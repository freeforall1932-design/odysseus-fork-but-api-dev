"""Council: fan-out / debate / verify with a fake model call (no network)."""
import asyncio
import time

import pytest

from src import council as cn

REFUSAL = "I'm sorry, but I can't help with that."
P = cn.DEFAULT_PERSONAS  # Researcher, Logician, Contrarian, Builder


class FakeLLM:
    """Records every call; replies are scripted per ref, per call number, or default to a tagged string."""

    def __init__(self, fail=(), refuse=(), fail_on=(), delays=None, chair_reply=None, worker_reply=None, worker_ref=None):
        self.calls = []                    # (ref, system, user)
        self.count = {}
        self.fail, self.refuse, self.fail_on = set(fail), set(refuse), set(fail_on)
        self.delays = delays or {}
        self.chair_reply, self.worker_reply, self.worker_ref = chair_reply, worker_reply, worker_ref

    async def __call__(self, ref, messages, temperature, max_tokens):
        n = self.count[ref] = self.count.get(ref, 0) + 1
        self.calls.append((ref, messages[0]["content"], messages[1]["content"]))
        if self.delays.get(ref):
            await asyncio.sleep(self.delays[ref])
        if ref in self.fail or (ref, n) in self.fail_on:
            raise RuntimeError("boom")
        if ref in self.refuse:
            return REFUSAL
        if ref == self.worker_ref and self.worker_reply is not None:
            return self.worker_reply
        if ref == "chair::c" and self.chair_reply is not None:
            return self.chair_reply
        return f"ANSWER[{ref}#{n}]"

    def for_ref(self, ref):
        return [c for c in self.calls if c[0] == ref]


def members(n=4, personas=True):
    return [cn.Member(ref=f"m{i}::model", persona=P[i] if personas else None) for i in range(n)]


def cfg(mode="debate", n=4, **kw):
    kw.setdefault("seed", 7)
    return cn.CouncilConfig(members=members(n, kw.pop("personas", True)), chair="chair::c", mode=mode, **kw)


async def run(config, fake, question="Q?"):
    return [ev async for ev in cn.run_council(question, config, fake)]


def kinds(events):
    return [e["type"] for e in events]


# --------------------------------------------------------------------------- cost model
def test_plan_numbers_match_the_hand_calculation():
    d = cn.plan("debate", 4, 2)
    assert (d["calls"], d["tokens"], d["x_single_call"]) == (9, 13270, 19.0)
    f = cn.plan("fanout", 4, 2)
    assert (f["calls"], f["tokens"], f["x_single_call"]) == (5, 5190, 7.4)
    v = cn.plan("verify", 4, 2)
    assert v["calls"] == 6                   # worker + 4 reviewers + chair
    assert cn.plan("debate", 4, 3)["calls"] == 13
    # the point of the model: debate costs far more tokens than calls suggest, because prompts carry everyone's answers
    assert d["tokens"] / f["tokens"] > d["calls"] / f["calls"]


# --------------------------------------------------------------------------- fanout / debate
async def test_fanout_runs_each_member_once_then_the_chair():
    fake = FakeLLM()
    ev = await run(cfg("fanout"), fake)
    assert kinds(ev) == ["start", "member", "member", "member", "member", "round_done", "chair", "done"]
    assert len(fake.calls) == 5 and ev[-1]["calls"] == 5
    chair_user = fake.for_ref("chair::c")[0][2]
    for i in range(4):
        assert f"ANSWER[m{i}::model#1]" in chair_user
    assert fake.for_ref("chair::c")[0][1].startswith(cn.CHAIR_SYSTEM)
    assert ev[0]["estimate"]["calls"] == 5


async def test_debate_makes_n_times_rounds_plus_one_calls():
    fake = FakeLLM()
    ev = await run(cfg("debate", rounds=2), fake)
    assert len(fake.calls) == 9 and ev[-1]["calls"] == 9
    assert [e["round"] for e in ev if e["type"] == "round_done"] == [1, 2]


async def test_rounds_are_clamped_to_the_maximum():
    fake = FakeLLM()
    await run(cfg("debate", rounds=99), fake)
    assert len(fake.calls) == 4 * cn.MAX_ROUNDS + 1


async def test_round_two_shows_others_anonymously_and_never_by_persona_name():
    fake = FakeLLM()
    await run(cfg("debate", rounds=2), fake)
    second = fake.for_ref("m0::model")[1]
    system, user = second[1], second[2]
    assert "ANSWER[m0::model#1]" in user                              # its own previous answer
    for i in (1, 2, 3):
        assert f"ANSWER[m{i}::model#1]" in user                       # everyone else's answer
    for other in ("Logician", "Contrarian", "Builder"):
        assert other not in user                                      # identities hidden from the reader
    assert "Member A" in user and "Member C" in user and "Member D" not in user
    assert "Researcher" in system                                     # its own persona stays in its system prompt
    assert "better argument, not to the majority" in user


async def test_shuffle_is_seeded_and_changes_with_the_seed():
    outs = []
    for seed in (1, 1, 2, 3, 4, 5):
        fake = FakeLLM()
        await run(cfg("debate", rounds=2, seed=seed), fake)
        outs.append(fake.for_ref("chair::c")[0][2])
    assert outs[0] == outs[1]                  # same seed -> same chair prompt
    assert len(set(outs)) > 1                  # different seeds -> different panel order


async def test_members_run_concurrently_and_events_stream_in_completion_order():
    fake = FakeLLM(delays={"m0::model": 0.15, "m1::model": 0.01, "m2::model": 0.08})
    start = time.perf_counter()
    ev = await run(cfg("fanout", n=3), fake)
    elapsed = time.perf_counter() - start
    assert [e["ref"] for e in ev if e["type"] == "member"] == ["m1::model", "m2::model", "m0::model"]
    assert elapsed < 0.30                       # sequential would be >= 0.24 + chair; parallel is ~0.15


async def test_members_without_personas_are_anonymous_to_the_chair():
    fake = FakeLLM()
    await run(cfg("fanout", personas=False), fake)
    user = fake.for_ref("chair::c")[0][2]
    assert "[Member A]" in user and "Researcher" not in user


# --------------------------------------------------------------------------- failures and refusals
async def test_a_failing_member_does_not_sink_the_council():
    fake = FakeLLM(fail={"m1::model"})
    ev = await run(cfg("fanout"), fake)
    done = ev[-1]
    assert done["type"] == "done" and (done["answered"], done["failed"], done["declined"]) == (3, 1, 0)
    failed = [e for e in ev if e["type"] == "member" and e["ref"] == "m1::model"][0]
    assert failed["ok"] is False and failed["error"] == "RuntimeError"
    assert "1 member(s) could not answer or declined" in fake.for_ref("chair::c")[0][2]


async def test_a_refusing_member_is_reported_and_kept_out_of_the_panel():
    fake = FakeLLM(refuse={"m2::model"})
    ev = await run(cfg("fanout"), fake)
    assert ev[-1]["declined"] == 1 and ev[-1]["answered"] == 3
    refused = [e for e in ev if e["type"] == "member" and e["refused"]]
    assert len(refused) == 1 and refused[0]["ref"] == "m2::model"
    assert REFUSAL not in fake.for_ref("chair::c")[0][2]


async def test_all_members_failing_is_an_error_and_the_chair_is_never_called():
    fake = FakeLLM(fail={f"m{i}::model" for i in range(4)})
    ev = await run(cfg("fanout"), fake)
    assert ev[-1]["type"] == "error" and "No member produced a usable answer" in ev[-1]["message"]
    assert not fake.for_ref("chair::c")


async def test_debate_skips_round_two_when_fewer_than_two_members_survive():
    fake = FakeLLM(fail={"m1::model", "m2::model", "m3::model"})
    ev = await run(cfg("debate", rounds=2), fake)
    assert len(fake.calls) == 4 + 1             # 4 first-round calls (3 failed) + chair, no revision round
    assert ev[-1]["type"] == "done" and ev[-1]["answered"] == 1


async def test_a_failed_revision_keeps_the_members_earlier_answer():
    fake = FakeLLM(fail_on={("m1::model", 2)})  # m1 answers round 1, fails round 2
    ev = await run(cfg("debate", rounds=2), fake)
    assert ev[-1]["type"] == "done" and ev[-1]["answered"] == 4
    assert "ANSWER[m1::model#1]" in fake.for_ref("chair::c")[0][2]


async def test_a_refusing_chair_is_flagged_and_an_empty_chair_is_an_error():
    ev = await run(cfg("fanout"), FakeLLM(chair_reply=REFUSAL))
    chair = [e for e in ev if e["type"] == "chair"][0]
    assert chair["refused"] is True
    ev = await run(cfg("fanout"), FakeLLM(chair_reply="   "))
    assert ev[-1]["type"] == "error" and "chair produced no answer" in ev[-1]["message"]


# --------------------------------------------------------------------------- verify
async def test_verify_with_an_existing_draft_reviews_it_blind_and_the_chair_issues_a_verdict():
    fake = FakeLLM()
    ev = await run(cfg("verify", draft="THE DRAFT TEXT"), fake)
    assert len(fake.calls) == 4 + 1
    review_user = fake.for_ref("m0::model")[0][2]
    assert "THE DRAFT TEXT" in review_user and "Question:" in review_user
    assert "SCORE: n/5" in fake.for_ref("m0::model")[0][1]
    chair_sys, chair_user = fake.for_ref("chair::c")[0][1], fake.for_ref("chair::c")[0][2]
    assert "Verdict: accepted as-is" in chair_sys and "THE DRAFT TEXT" in chair_user
    assert ev[-1]["type"] == "done"


async def test_verify_with_a_worker_drafts_first_then_reviews_it():
    fake = FakeLLM(worker_ref="local::w", worker_reply="WORKER DRAFT")
    ev = await run(cfg("verify", worker="local::w"), fake)
    assert fake.calls[0][0] == "local::w"
    draft = [e for e in ev if e["type"] == "draft"][0]
    assert draft["text"] == "WORKER DRAFT" and draft["ok"]
    assert "WORKER DRAFT" in fake.for_ref("m3::model")[0][2]
    assert len(fake.calls) == 1 + 4 + 1 and ev[-1]["calls"] == 6


async def test_verify_stops_when_the_worker_declines_or_there_is_no_draft_source():
    fake = FakeLLM(worker_ref="local::w", worker_reply=REFUSAL)
    ev = await run(cfg("verify", worker="local::w"), fake)
    assert ev[-1]["type"] == "error" and "declined" in ev[-1]["message"]
    assert len(fake.calls) == 1
    ev = await run(cfg("verify"), FakeLLM())
    assert ev[-1]["type"] == "error" and "worker model or an existing draft" in ev[-1]["message"]
    ev = await run(cfg("verify", worker="local::w"), FakeLLM(fail={"local::w"}))
    assert ev[-1]["type"] == "error" and "no draft" in ev[-1]["message"]


# --------------------------------------------------------------------------- skills
async def test_skill_text_goes_to_the_chair_by_default_and_to_everyone_when_asked():
    fake = FakeLLM()
    await run(cfg("fanout", skill_text="BE-BRIEF-RULES"), fake)
    assert "BE-BRIEF-RULES" in fake.for_ref("chair::c")[0][1]
    assert all("BE-BRIEF-RULES" not in c[1] for c in fake.calls if c[0] != "chair::c")
    fake = FakeLLM()
    await run(cfg("fanout", skill_text="BE-BRIEF-RULES", skill_scope="all"), fake)
    assert all("BE-BRIEF-RULES" in c[1] for c in fake.calls)


# --------------------------------------------------------------------------- guard rails
@pytest.mark.parametrize("make,needle", [
    (lambda: cn.CouncilConfig(members=members(2), chair="chair::c", mode="nope"), "Unknown council mode"),
    (lambda: cn.CouncilConfig(members=[], chair="chair::c"), "1-8 members"),
    (lambda: cn.CouncilConfig(members=members(2) * 5, chair="chair::c"), "1-8 members"),
    (lambda: cn.CouncilConfig(members=members(2), chair=""), "Pick a chair"),
])
async def test_bad_configs_yield_an_error_event_and_make_no_calls(make, needle):
    fake = FakeLLM()
    ev = await run(make(), fake)
    assert kinds(ev) == ["error"] and needle in ev[0]["message"] and not fake.calls


# --------------------------------------------------------------------------- config_from_dict
def _body(**over):
    body = {"members": [{"ref": "a::m1", "persona": "researcher"}, {"endpoint_id": "b", "model": "m2:7b"}],
            "chair": "c::big", "mode": "debate", "rounds": 2}
    body.update(over)
    return body


def test_config_from_dict_happy_path():
    c = cn.config_from_dict(_body(skill_scope="all", draft="d" * 30000), skill_text="SK")
    assert [m.ref for m in c.members] == ["a::m1", "b::m2:7b"]
    assert c.members[0].persona.name == "Researcher" and c.members[1].persona is None
    assert c.chair == "c::big" and c.skill_scope == "all" and c.skill_text == "SK"
    assert len(c.draft) == 20000                   # capped


def test_config_from_dict_accepts_custom_personas_and_clamps_values():
    body = _body(members=[{"ref": "a::m", "persona": {"name": "Pirate", "prompt": "Talk like a pirate."}, "temperature": 9},
                          {"ref": "b::m", "temperature": "nope"}], rounds=50)
    c = cn.config_from_dict(body)
    assert c.members[0].persona.name == "Pirate" and c.members[0].temperature == 1.5
    assert c.members[1].temperature == 0.8 and c.rounds == cn.MAX_ROUNDS


def test_duplicate_members_get_distinct_display_names():
    c = cn.config_from_dict(_body(members=[{"ref": "a::m"}, {"ref": "b::m"}, {"ref": "c::m"}]))
    assert len({m.display for m in c.members}) == 3


@pytest.mark.parametrize("override,needle", [
    ({"members": []}, "non-empty list"),
    ({"members": [{"ref": "a::m"}] * 9}, "at most 8"),
    ({"members": ["str"]}, "must be an object"),
    ({"members": [{"ref": "nocolons"}]}, "endpoint_id and a model"),
    ({"members": [{"ref": "::m"}]}, "endpoint_id and a model"),
    ({"members": [{"ref": "a::m", "persona": "wizard"}]}, "unknown persona"),
    ({"chair": "nochair"}, "chair must be"),
    ({"mode": "vote"}, "mode must be one of"),
])
def test_config_from_dict_rejects_bad_input(override, needle):
    with pytest.raises(ValueError, match=needle):
        cn.config_from_dict(_body(**override))
