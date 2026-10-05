"""Council: several models (or several personas of one model) work a question, a chair merges.

How a single model can "talk to itself": it can't. Each member is a separate call, and the
orchestrator (this file) pastes one member's answer into another member's next prompt. A
persona is just the system prompt, so diversity comes from (a) different prompts, (b) different
models when you have API keys for several, and (c) sampling temperature.

Modes
-----
fanout  members answer independently, in parallel; the chair merges.
debate  fanout, then every member reads the others (anonymised, shuffled) and revises; chair merges.
verify  a *worker* (typically a small offline model) drafts; members review the draft blind to
        who wrote it; the chair corrects it and says whether it was accepted as-is.

Guard-rails against the failure PewDiePie's council hit (members voting to protect each other):
members never score each other, the chair is a separate seat that does not vote, others' answers
are anonymised and shuffled per reader, and the chair is told to weigh arguments, not counts.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional

from src.auto_router import looks_like_refusal

# call(ref, messages, temperature, max_tokens) -> text.  ``ref`` is "endpoint_id::model".
CallFn = Callable[[str, List[Dict[str, str]], float, int], Awaitable[str]]

MODES = ("fanout", "debate", "verify")
MAX_MEMBERS = 8
MAX_ROUNDS = 3


@dataclass(frozen=True)
class Persona:
    name: str
    prompt: str


DEFAULT_PERSONAS = (
    Persona("Researcher", "You are the Researcher. Ground every claim in facts and say what you would need to verify."),
    Persona("Logician", "You are the Logician. Check numbers, steps and logic. Flag anything that does not follow."),
    Persona("Contrarian", "You are the Contrarian. Challenge the obvious answer and name what everyone is missing."),
    Persona("Builder", "You are the Builder. Turn the problem into concrete steps someone can do today."),
)

NEUTRAL = "You are one member of a council. Answer carefully and concisely. State your confidence and what you could not verify."
CHAIR_SYSTEM = (
    "You are the chair of a council. You receive the question and each member's answer. Judge by the quality of "
    "the reasoning, not by how many members agree. Keep what holds up, flag what stays uncertain or disputed, and "
    "write ONE final answer for the user. If some members could not answer, add one short line saying so."
)
REVIEW_SYSTEM = (
    "You are reviewing a draft answer written by another model. Do not rewrite it. List (1) factual errors or "
    "claims you cannot support, (2) missing steps or caveats, (3) anything risky. If it is fine, say so. "
    "End with a line 'SCORE: n/5'."
)
VERIFY_CHAIR_SYSTEM = (
    "You are the chair. You receive the question, a draft answer and reviews of it. Produce the final answer: fix "
    "what the reviews establish, keep what is fine, and do not add claims nobody verified. Start with one line, "
    "either 'Verdict: accepted as-is' or 'Verdict: corrected', then give the final answer."
)


@dataclass
class Member:
    ref: str
    persona: Optional[Persona] = None
    label: str = ""
    temperature: float = 0.8

    @property
    def display(self) -> str:
        return self.label or (self.persona.name if self.persona else self.ref.partition("::")[2] or self.ref)


@dataclass
class CouncilConfig:
    members: List[Member]
    chair: str
    mode: str = "debate"
    rounds: int = 2
    skill_text: str = ""
    skill_scope: str = "chair"  # chair | all
    worker: str = ""            # verify: who drafts (ignored when ``draft`` is given)
    draft: str = ""             # verify: an existing answer to review
    member_max_tokens: int = 600
    chair_max_tokens: int = 900
    seed: Optional[int] = None  # makes the shuffle deterministic (tests)


@dataclass
class _Result:
    text: str = ""
    ok: bool = False
    refused: bool = False
    error: str = ""


def plan(mode: str, n: int = 4, rounds: int = 2, q: int = 400, a: int = 300, persona: int = 60, chair_out: int = 400) -> Dict[str, Any]:
    """Rough budget. q/a/persona/chair_out are token GUESSES, so treat the result as an order of magnitude."""
    first = n * (persona + q + a)
    later = (rounds - 1) * n * (persona + q + a + (n - 1) * a + 60 + a) if mode == "debate" else 0
    chair = 150 + q + n * a + chair_out
    if mode == "verify":
        first = (q + a) + n * (persona + q + a + a)  # worker draft + n reviews of it
    calls = (1 if mode == "verify" else 0) + n * (rounds if mode == "debate" else 1) + 1
    total = first + later + chair
    return {"mode": mode, "calls": calls, "tokens": total, "x_single_call": round(total / (q + a), 1)}


# --------------------------------------------------------------------------- prompts
def _system_for(cfg: CouncilConfig, m: Member, base: Optional[str] = None) -> str:
    parts = [m.persona.prompt if m.persona else (base or NEUTRAL)]
    if cfg.skill_text and cfg.skill_scope == "all":
        parts.append(cfg.skill_text)
    parts.append("Keep your answer under about 250 words.")
    return "\n\n".join(parts)


def _chair_system(cfg: CouncilConfig, base: str) -> str:
    return base + ("\n\n" + cfg.skill_text if cfg.skill_text else "")


def _msgs(system: str, user: str) -> List[Dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _label(i: int) -> str:
    return f"Member {chr(ord('A') + i)}"


def _panel(items: List[tuple]) -> str:
    return "\n\n".join(f"[{name}]\n{text}" for name, text in items)


# --------------------------------------------------------------------------- engine
async def _safe_call(call: CallFn, ref: str, messages, temperature: float, max_tokens: int) -> _Result:
    try:
        text = await call(ref, messages, temperature, max_tokens)
    except Exception as exc:  # one member failing must not sink the council
        code = getattr(exc, "status_code", None)
        return _Result(error=f"HTTP {code}" if isinstance(code, int) else type(exc).__name__)
    text = (text or "").strip()
    if not text:
        return _Result(error="empty reply")
    if looks_like_refusal(text):
        return _Result(text=text, refused=True)
    return _Result(text=text, ok=True)


async def _round(members, build, call: CallFn, cfg: CouncilConfig, round_no: int, out: Dict[int, _Result]):
    """Run members concurrently and yield an event as each one finishes."""
    async def one(i: int):
        m = members[i]
        return i, await _safe_call(call, m.ref, build(i), m.temperature, cfg.member_max_tokens)

    tasks = [asyncio.ensure_future(one(i)) for i in range(len(members))]
    try:
        for fut in asyncio.as_completed(tasks):
            i, res = await fut
            out[i] = res
            m = members[i]
            yield {"type": "member", "round": round_no, "name": m.display, "ref": m.ref, "text": res.text,
                   "ok": res.ok, "refused": res.refused, "error": res.error}
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def run_council(question: str, cfg: CouncilConfig, call: CallFn) -> AsyncIterator[Dict[str, Any]]:
    """Yield events: start, [draft], member*, round_done*, chair, done (or error)."""
    if cfg.mode not in MODES:
        yield {"type": "error", "message": f"Unknown council mode '{cfg.mode}'."}
        return
    if not cfg.members or len(cfg.members) > MAX_MEMBERS:
        yield {"type": "error", "message": f"A council needs 1-{MAX_MEMBERS} members."}
        return
    if not cfg.chair:
        yield {"type": "error", "message": "Pick a chair model."}
        return

    rng = random.Random(cfg.seed)
    members = list(cfg.members)
    n, rounds = len(members), max(1, min(cfg.rounds, MAX_ROUNDS))
    calls = 0
    yield {"type": "start", "mode": cfg.mode, "chair": cfg.chair, "rounds": rounds if cfg.mode == "debate" else 1,
           "members": [{"name": m.display, "ref": m.ref} for m in members],
           "estimate": plan(cfg.mode, n, rounds)}

    draft = (cfg.draft or "").strip()
    if cfg.mode == "verify" and not draft:
        if not cfg.worker:
            yield {"type": "error", "message": "Verify mode needs a worker model or an existing draft."}
            return
        res = await _safe_call(call, cfg.worker, _msgs(NEUTRAL, question), 0.4, cfg.chair_max_tokens)
        calls += 1
        yield {"type": "draft", "ref": cfg.worker, "text": res.text, "ok": res.ok, "refused": res.refused, "error": res.error}
        if res.refused:
            yield {"type": "error", "message": "The worker model declined the task, so there is no draft to verify."}
            return
        if not res.ok:
            yield {"type": "error", "message": "The worker model produced no draft."}
            return
        draft = res.text

    results: Dict[int, _Result] = {}
    if cfg.mode == "verify":
        def build_review(i: int):
            m = members[i]
            sys_prompt = (m.persona.prompt + "\n\n" if m.persona else "") + REVIEW_SYSTEM
            if cfg.skill_text and cfg.skill_scope == "all":
                sys_prompt += "\n\n" + cfg.skill_text
            return _msgs(sys_prompt, f"Question:\n{question}\n\nDraft answer:\n{draft}")
        build_first = build_review
    else:
        def build_first(i: int):
            return _msgs(_system_for(cfg, members[i]), question)

    async for ev in _round(members, build_first, call, cfg, 1, results):
        calls += 1
        yield ev
    yield {"type": "round_done", "round": 1}

    if cfg.mode == "debate":
        for r in range(2, rounds + 1):
            alive = [i for i in range(n) if results.get(i) and results[i].ok]
            if len(alive) < 2:
                break
            snapshot = {i: results[i].text for i in alive}
            new_results: Dict[int, _Result] = {}

            def build_revise(k: int, _alive=alive, _snap=snapshot):
                i = _alive[k]
                others = [j for j in _alive if j != i]
                rng.shuffle(others)
                seen = _panel([(_label(x), _snap[j]) for x, j in enumerate(others)])
                user = (f"Question:\n{question}\n\nYour answer so far:\n{_snap[i]}\n\nOther members said (anonymous):\n{seen}\n\n"
                        "Revise your answer. Concede what is wrong, defend what is right, and name any disagreement that "
                        "remains. Defer to the better argument, not to the majority.")
                return _msgs(_system_for(cfg, members[i]), user)

            sub = [members[i] for i in alive]
            sub_out: Dict[int, _Result] = {}
            async for ev in _round(sub, build_revise, call, cfg, r, sub_out):
                calls += 1
                yield ev
            for k, i in enumerate(alive):
                res = sub_out.get(k)
                # keep the earlier answer if the revision failed or was declined
                new_results[i] = res if (res and res.ok) else results[i]
            results.update(new_results)
            yield {"type": "round_done", "round": r}

    answered = [i for i in range(n) if results.get(i) and results[i].ok]
    declined = [i for i in range(n) if results.get(i) and results[i].refused]
    if not answered:
        yield {"type": "error", "message": "No member produced a usable answer."
               + (f" {len(declined)} declined." if declined else "")}
        return

    order = answered[:]
    rng.shuffle(order)
    panel = _panel([(members[i].display if members[i].persona or members[i].label else _label(x), results[i].text)
                    for x, i in enumerate(order)])
    missing = n - len(answered)
    note = f"\n\n({missing} member(s) could not answer or declined.)" if missing else ""
    if cfg.mode == "verify":
        user = f"Question:\n{question}\n\nDraft answer:\n{draft}\n\nReviews:\n{panel}{note}"
        system = _chair_system(cfg, VERIFY_CHAIR_SYSTEM)
    else:
        user = f"Question:\n{question}\n\nMember answers:\n{panel}{note}"
        system = _chair_system(cfg, CHAIR_SYSTEM)
    final = await _safe_call(call, cfg.chair, _msgs(system, user), 0.3, cfg.chair_max_tokens)
    calls += 1
    if not final.text:
        yield {"type": "error", "message": f"The chair produced no answer ({final.error or 'declined'})."}
        return
    yield {"type": "chair", "ref": cfg.chair, "text": final.text, "refused": final.refused}
    yield {"type": "done", "calls": calls, "answered": len(answered), "declined": len(declined), "failed": n - len(answered) - len(declined)}


# --------------------------------------------------------------------------- config parsing
def config_from_dict(d: Dict[str, Any], skill_text: str = "") -> CouncilConfig:
    """Validate a JSON body from the API. Raises ValueError with a presentable message."""
    raw_members = d.get("members")
    if not isinstance(raw_members, list) or not raw_members:
        raise ValueError("members must be a non-empty list")
    if len(raw_members) > MAX_MEMBERS:
        raise ValueError(f"at most {MAX_MEMBERS} members")
    by_name = {p.name.lower(): p for p in DEFAULT_PERSONAS}
    members: List[Member] = []
    for item in raw_members:
        if not isinstance(item, dict):
            raise ValueError("each member must be an object")
        ref = str(item.get("ref") or f"{item.get('endpoint_id', '')}::{item.get('model', '')}")
        if "::" not in ref or ref.startswith("::") or ref.endswith("::"):
            raise ValueError("each member needs an endpoint_id and a model")
        p = item.get("persona")
        persona: Optional[Persona] = None
        if isinstance(p, str) and p.strip():
            persona = by_name.get(p.strip().lower())
            if persona is None:
                raise ValueError(f"unknown persona '{p}'")
        elif isinstance(p, dict) and str(p.get("prompt") or "").strip():
            persona = Persona(str(p.get("name") or "Member")[:40], str(p["prompt"])[:1500])
        try:
            temp = float(item.get("temperature", 0.8))
        except (TypeError, ValueError):
            temp = 0.8
        members.append(Member(ref=ref, persona=persona, label=str(item.get("label") or "")[:40], temperature=min(max(temp, 0.0), 1.5)))
    seen: Dict[str, int] = {}
    for m in members:  # keep display names unique so the UI can tell members apart
        base = m.display
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            m.label = f"{base} {seen[base]}"
    chair = str(d.get("chair") or "")
    if "::" not in chair:
        raise ValueError("chair must be 'endpoint_id::model'")
    mode = str(d.get("mode") or "debate")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    try:
        rounds = int(d.get("rounds", 2))
    except (TypeError, ValueError):
        rounds = 2
    scope = "all" if str(d.get("skill_scope") or "chair") == "all" else "chair"
    return CouncilConfig(
        members=members, chair=chair, mode=mode, rounds=max(1, min(rounds, MAX_ROUNDS)),
        skill_text=skill_text, skill_scope=scope, worker=str(d.get("worker") or ""),
        draft=str(d.get("draft") or "")[:20000],
    )
