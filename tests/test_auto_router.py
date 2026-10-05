"""Auto mode: pool prefilter, router pick, degradation, refusal detection, fallback chain."""
import asyncio

import pytest

from src import auto_router as ar


def E(ep, model, **kw):
    return ar.PoolEntry(endpoint_id=ep, model=model, **kw)


def pool():
    return [
        E("or", "meta/llama:free", label="Llama Free", free=True, context_length=131072, vision=False, tools=True),
        E("or", "qwen/coder:free", label="Qwen Coder Free", free=True, context_length=32768, vision=False, tags=("code",)),
        E("gem", "gemini-flash", label="Gemini Flash", context_length=1_000_000, vision=True),
        E("loc", "qwen3:4b", label="Qwen3 4B", local=True, context_length=8192),
    ]


def refs(entries):
    return [e.model for e in entries]


# --------------------------------------------------------------------------- refs / entries
def test_split_ref_keeps_colons_in_model_ids():
    assert ar.split_ref("loc::qwen3:4b") == ("loc", "qwen3:4b")
    assert ar.split_ref("nothing") == ("nothing", "")
    assert E("loc", "qwen3:4b").ref == "loc::qwen3:4b"


def test_pool_entry_from_dict_normalises_tags():
    e = ar.PoolEntry.from_dict({"endpoint_id": "x", "model": "m", "tags": " Code , Fast ,", "local": 1})
    assert e.tags == ("code", "fast") and e.local is True


# --------------------------------------------------------------------------- prefilter
def test_keep_local_is_a_hard_filter():
    cands, notes = ar.prefilter(ar.TaskInfo("hello", keep_local=True), pool())
    assert refs(cands) == ["qwen3:4b"] and "keep-local" in notes


def test_keep_local_with_no_local_model_raises_instead_of_falling_back_to_cloud():
    cloud_only = [e for e in pool() if not e.local]
    with pytest.raises(ar.NoRouteError, match="no offline model"):
        ar.prefilter(ar.TaskInfo("hello", keep_local=True), cloud_only)


def test_vision_prefers_models_that_are_not_known_text_only():
    cands, notes = ar.prefilter(ar.TaskInfo("what is in this picture", has_image=True), pool())
    assert refs(cands) == ["gemini-flash", "qwen3:4b"]  # unknown (None) is kept, known-False is dropped
    assert "vision" in notes


def test_soft_filters_are_ignored_when_nothing_would_match():
    only_text = [e for e in pool() if e.vision is False]
    cands, notes = ar.prefilter(ar.TaskInfo("img", has_image=True), only_text)
    assert refs(cands) == refs(only_text)
    assert any("no model matched" in n for n in notes)


def test_long_prompts_drop_models_with_too_small_a_context_window():
    task = ar.TaskInfo("x" * 40_000)  # ~10k tokens, needs ~16k
    cands, notes = ar.prefilter(task, pool())
    assert "qwen3:4b" not in refs(cands) and "context-length" in notes


def test_exclude_skips_models_already_tried_and_errors_when_none_are_left():
    cands, notes = ar.prefilter(ar.TaskInfo("hi"), pool(), exclude=["or::meta/llama:free"])
    assert "meta/llama:free" not in refs(cands) and any("already tried" in n for n in notes)
    with pytest.raises(ar.NoRouteError, match="No other model"):
        ar.prefilter(ar.TaskInfo("hi"), pool(), exclude=[e.ref for e in pool()])


def test_empty_pool_and_incomplete_entries_are_not_candidates():
    with pytest.raises(ar.NoRouteError):
        asyncio.run(ar.route(ar.TaskInfo("hi"), [E("", "m"), E("ep", "")], None))


# --------------------------------------------------------------------------- parse_pick
@pytest.mark.parametrize("text,n,expected", [
    ('{"pick": 2, "reason": "code task"}', 4, (2, "code task")),
    ('```json\n{"pick": 3}\n```', 4, (3, "")),
    ('Sure! {"pick": 1, "reason": "small"} hope that helps', 4, (1, "small")),
    ('pick: 4', 4, (4, "")),
    ('"pick" = 2', 4, (2, "")),
    ("3", 4, (3, "")),
    ('{"pick": "2"}', 4, (2, "")),
    ('{"pick": 9}', 4, (None, "")),     # out of range
    ('{"pick": 0}', 4, (None, "")),
    ('{"pick": "two"}', 4, (None, "")),
    ('{"pick": true}', 4, (None, "")),
    ('{"pick": 2.5}', 4, (None, "")),
    ('pick: 2.5', 4, (None, "")),
    ("I would choose the second one", 4, (None, "")),
    ("", 4, (None, "")),
])
def test_parse_pick(text, n, expected):
    assert ar.parse_pick(text, n) == expected


# --------------------------------------------------------------------------- route
async def test_single_candidate_never_calls_the_router():
    called = []

    async def router(msgs):
        called.append(msgs)
        return '{"pick": 1}'

    d = await ar.route(ar.TaskInfo("hi", keep_local=True), pool(), router)
    assert d.source == "only-candidate" and d.entry.model == "qwen3:4b" and not called


async def test_router_pick_is_used_with_its_reason():
    async def router(msgs):
        return '{"pick": 2, "reason": "code task"}'

    d = await ar.route(ar.TaskInfo("write a python function"), pool(), router)
    assert d.source == "router" and d.entry.model == "qwen/coder:free" and d.reason == "code task"
    assert len(d.candidates) == 4


@pytest.mark.parametrize("behaviour", ["raise", "garbage", "out_of_range", "slow"])
async def test_router_problems_degrade_to_the_default_instead_of_failing(behaviour):
    async def router(msgs):
        if behaviour == "raise":
            raise RuntimeError("429")
        if behaviour == "slow":
            await asyncio.sleep(1)
        return {"garbage": "no idea", "out_of_range": '{"pick": 99}', "slow": '{"pick": 1}'}.get(behaviour, "")

    d = await ar.route(ar.TaskInfo("hi"), pool(), router, default_ref="gem::gemini-flash", timeout=0.05)
    assert d.source == "fallback" and d.entry.model == "gemini-flash"


async def test_no_router_uses_pool_order_when_there_is_no_default():
    d = await ar.route(ar.TaskInfo("hi"), pool(), None)
    assert d.source == "fallback" and d.entry.model == "meta/llama:free"


async def test_candidate_limit_preserves_a_late_configured_default():
    entries = [E("ep", f"model-{i}") for i in range(14)]
    preferred = entries[-1]
    d = await ar.route(ar.TaskInfo("hi"), entries, None, default_ref=preferred.ref)
    assert d.entry.ref == preferred.ref and preferred in d.candidates
    assert len(d.candidates) == 12


async def test_keep_local_router_prompt_never_mentions_cloud_models():
    seen = []

    async def router(msgs):
        seen.append(msgs)
        return '{"pick": 1}'

    local_pool = pool() + [E("loc", "phi4-mini", label="Phi4 Mini", local=True)]
    d = await ar.route(ar.TaskInfo("private notes", keep_local=True), local_pool, router)
    text = " ".join(m["content"] for m in seen[0])
    assert "Qwen3 4B" in text and "Phi4 Mini" in text
    for cloud in ("Llama Free", "Gemini Flash", "Qwen Coder Free"):
        assert cloud not in text
    assert d.entry.local is True


def test_router_prompt_truncates_long_messages_but_keeps_both_ends():
    msg = "START" + "m" * 5000 + "END"
    out = ar.build_router_messages(ar.TaskInfo(msg), pool())[1]["content"]
    assert "START" in out and "END" in out and len(out) < 2500
    assert ar.build_router_messages(ar.TaskInfo("x"), pool())[0]["role"] == "system"


# --------------------------------------------------------------------------- refusals
@pytest.mark.parametrize("text", [
    "I'm sorry, but I can't help with that request.",
    "I cannot assist with this.",
    "I can't help with that.",
    "Sorry, I must decline.",
    "I am unable to provide that information.",
    "As an AI language model, I cannot do that.",
    "  I won't help with this.  ",
])
def test_refusal_openers_are_detected(text):
    assert ar.looks_like_refusal(text)


@pytest.mark.parametrize("text", [
    "",
    "OK",
    "Sure! Here is the plan. I can't stress enough how important backups are.",
    "The patient said she cannot sleep, so here is what the literature suggests...",
    "I cannot help with the exact request, but here is a detailed alternative: " + "x" * 800,  # long answers are left alone
])
def test_normal_answers_are_not_flagged(text):
    assert not ar.looks_like_refusal(text)


def test_provider_signals_count_even_when_the_text_is_unremarkable():
    assert ar.looks_like_refusal("whatever", finish_reason="content_filter")
    assert ar.looks_like_refusal("whatever", stop_reason="refusal")
    assert not ar.looks_like_refusal("whatever", finish_reason="stop")


# --------------------------------------------------------------------------- fallback chain
def _caller(script, seen=None):
    async def call(entry, messages):
        if seen is not None:
            seen.append((entry.model, messages))
        outcome = script[entry.model]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    return call


MSGS = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
REFUSAL = "I'm sorry, but I can't help with that."


async def test_error_moves_on_to_the_next_model():
    entries = pool()[:2]
    r = await ar.answer_with_fallback(entries, _caller({"meta/llama:free": RuntimeError("503"), "qwen/coder:free": "fine"}), MSGS)
    assert r.text == "fine" and r.entry.model == "qwen/coder:free"
    assert [(a.entry.model, a.outcome) for a in r.attempts] == [("meta/llama:free", "error"), ("qwen/coder:free", "ok")]


async def test_a_refusal_is_accepted_as_the_answer_unless_fallback_on_refusal_is_enabled():
    entries = pool()[:2]
    r = await ar.answer_with_fallback(entries, _caller({"meta/llama:free": REFUSAL, "qwen/coder:free": "fine"}), MSGS)
    assert r.text == REFUSAL and r.entry.model == "meta/llama:free" and len(r.attempts) == 1


async def test_on_refusal_moves_on_and_reports_every_attempt():
    entries = pool()[:3]
    r = await ar.answer_with_fallback(
        entries, _caller({"meta/llama:free": REFUSAL, "qwen/coder:free": REFUSAL, "gemini-flash": "ok"}), MSGS, on_refusal=True)
    assert r.text == "ok" and not r.all_declined
    assert [a.outcome for a in r.attempts] == ["refused", "refused", "ok"]


async def test_if_everyone_declines_the_first_refusal_is_returned_not_hidden():
    entries = pool()[:2]
    r = await ar.answer_with_fallback(
        entries, _caller({"meta/llama:free": REFUSAL, "qwen/coder:free": "I cannot assist with this."}), MSGS, on_refusal=True)
    assert r.all_declined and r.text == REFUSAL and r.entry.model == "meta/llama:free"


async def test_everything_failing_returns_an_empty_result_and_on_error_false_raises():
    entries = pool()[:2]
    boom = {"meta/llama:free": RuntimeError("a"), "qwen/coder:free": RuntimeError("b")}
    r = await ar.answer_with_fallback(entries, _caller(boom), MSGS)
    assert r.text == "" and r.entry is None and not r.all_declined
    with pytest.raises(RuntimeError):
        await ar.answer_with_fallback(entries, _caller(boom), MSGS, on_error=False)


async def test_every_model_receives_the_same_unmodified_messages():
    seen = []
    entries = pool()[:3]
    snapshot = [dict(m) for m in MSGS]
    await ar.answer_with_fallback(
        entries, _caller({"meta/llama:free": REFUSAL, "qwen/coder:free": REFUSAL, "gemini-flash": "ok"}, seen), MSGS, on_refusal=True)
    assert len(seen) == 3
    assert all(m == snapshot for _model, m in seen)   # no rewording to get past a refusal
    assert MSGS == snapshot
