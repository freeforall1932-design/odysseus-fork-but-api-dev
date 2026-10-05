"""Auto mode: pick the right model from a saved pool, per message.

Pieces (all pure / injectable so they can be tested without a network):

* ``PoolEntry``      - one saved model (endpoint id + model id + tags + local/cloud).
* ``prefilter``      - cheap rules before any LLM is asked (vision, tools, context, keep-local).
* ``route``          - asks a small *router model* (cloud or offline) to choose; falls back
                       to the user's order if the router is slow or answers badly.
* refusal helpers    - ``looks_like_refusal`` and ``answer_with_fallback`` for non-streaming
                       paths (council, verification). Every attempt is reported back so the
                       UI can show which model answered and which ones declined.

Design rules worth keeping:

* ``keep_local`` is a HARD constraint. If nothing local is in the pool the request fails; it
  never silently falls through to a cloud model.
* The router only ever chooses from the pool the user saved. It cannot add models.
* A refusal is reported, never hidden, and the prompt is never rewritten to get around it.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

AUTO_MODEL_ID = "auto"

# ``call(messages) -> text``. Supplied by the caller so this module knows nothing about HTTP.
RouterCall = Callable[[List[Dict[str, str]]], Awaitable[str]]
# ``call(entry, messages) -> text`` for answering with a specific pool entry.
EntryCall = Callable[["PoolEntry", List[Dict[str, str]]], Awaitable[str]]


class NoRouteError(Exception):
    """Raised when a hard constraint (keep_local) cannot be satisfied."""


@dataclass(frozen=True)
class PoolEntry:
    endpoint_id: str
    model: str
    label: str = ""
    tags: Tuple[str, ...] = ()
    local: bool = False
    free: Optional[bool] = None
    context_length: Optional[int] = None
    vision: Optional[bool] = None
    tools: Optional[bool] = None

    @property
    def ref(self) -> str:
        return f"{self.endpoint_id}::{self.model}"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PoolEntry":
        tags = d.get("tags") or ()
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        return cls(
            endpoint_id=str(d.get("endpoint_id") or ""),
            model=str(d.get("model") or ""),
            label=str(d.get("label") or ""),
            tags=tuple(t for t in (str(x).strip().lower() for x in tags) if t),
            local=bool(d.get("local")),
            free=d.get("free"),
            context_length=d.get("context_length"),
            vision=d.get("vision"),
            tools=d.get("tools"),
        )

    def describe(self) -> str:
        bits = ["offline" if self.local else "cloud"]
        if self.free:
            bits.append("free")
        if self.context_length:
            bits.append(f"{self.context_length // 1000}k ctx" if self.context_length >= 1000 else f"{self.context_length} ctx")
        if self.vision:
            bits.append("vision")
        if self.tags:
            bits.append("tags: " + ", ".join(self.tags))
        return f"{self.label or self.model} [{'; '.join(bits)}]"


def split_ref(ref: str) -> Tuple[str, str]:
    """'endpoint_id::model' -> (endpoint_id, model). Model ids may themselves contain colons."""
    ep, _, model = (ref or "").partition("::")
    return ep, model


@dataclass
class TaskInfo:
    text: str
    has_image: bool = False
    needs_tools: bool = False
    keep_local: bool = False
    est_tokens: int = 0

    def __post_init__(self):
        if not self.est_tokens:
            self.est_tokens = max(1, len(self.text or "") // 4)


@dataclass
class RouteDecision:
    entry: PoolEntry
    reason: str
    source: str  # router | only-candidate | fallback
    notes: List[str] = field(default_factory=list)
    candidates: List[PoolEntry] = field(default_factory=list)


# --------------------------------------------------------------------------- prefilter
def prefilter(
    task: TaskInfo, pool: Sequence[PoolEntry], exclude: Sequence[str] = ()
) -> Tuple[List[PoolEntry], List[str]]:
    """Narrow the pool with cheap rules. keep_local and exclude are hard; the rest are best-effort."""
    notes: List[str] = []
    cands = [e for e in pool if e.endpoint_id and e.model]
    if exclude:
        skip = set(exclude)
        left = [e for e in cands if e.ref not in skip]
        if len(left) != len(cands):
            notes.append(f"skipped {len(cands) - len(left)} already tried")
        if not left:
            raise NoRouteError("No other model left to try in the pool.")
        cands = left
    if task.keep_local:
        cands = [e for e in cands if e.local]
        if not cands:
            raise NoRouteError("Keep-local is on, but the pool has no offline model. Add one or turn keep-local off.")
        notes.append("keep-local")

    def soft(pred: Callable[[PoolEntry], bool], why: str) -> None:
        nonlocal cands
        kept = [e for e in cands if pred(e)]
        if kept and len(kept) != len(cands):
            cands = kept
            notes.append(why)
        elif not kept:
            notes.append(f"{why} (no model matched, ignored)")

    if task.has_image:
        soft(lambda e: e.vision is not False, "vision")
    if task.needs_tools:
        soft(lambda e: e.tools is not False, "tools")
    need = int(task.est_tokens * 1.5) + 1000
    soft(lambda e: not e.context_length or e.context_length >= need, "context-length")
    return cands, notes


# --------------------------------------------------------------------------- router prompt
ROUTER_SYSTEM = (
    "You are a model router. Pick the single best model for the user's task from the numbered list. "
    "Prefer the cheapest or fastest model that can do the task well; choose a stronger model only for "
    "hard reasoning, long context, careful writing or code. "
    'Reply with ONLY JSON like {"pick": 2, "reason": "short code task"} - reason at most 12 words.'
)


def build_router_messages(task: TaskInfo, cands: Sequence[PoolEntry], max_chars: int = 1200) -> List[Dict[str, str]]:
    lines = [f"{i}. {e.describe()}" for i, e in enumerate(cands, 1)]
    text = (task.text or "").strip()
    if len(text) > max_chars:
        text = text[: max_chars // 2] + "\n...\n" + text[-max_chars // 2:]
    flags = []
    if task.has_image:
        flags.append("has an image")
    if task.needs_tools:
        flags.append("needs tools")
    user = "Models:\n" + "\n".join(lines) + ("\n\nTask flags: " + ", ".join(flags) if flags else "") + "\n\nTask:\n" + text
    return [{"role": "system", "content": ROUTER_SYSTEM}, {"role": "user", "content": user}]


_JSON_OBJ = re.compile(r"\{.*?\}", re.S)


def parse_pick(text: str, n: int) -> Tuple[Optional[int], str]:
    """Return (1-based index or None, reason). Tolerant of fences, prose and bare numbers."""
    body = (text or "").strip()
    for m in _JSON_OBJ.finditer(body):
        try:
            obj = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(obj, dict) and "pick" in obj:
            raw_idx = obj["pick"]
            if isinstance(raw_idx, bool):
                continue
            if isinstance(raw_idx, int):
                idx = raw_idx
            elif isinstance(raw_idx, str) and re.fullmatch(r"\d+", raw_idx.strip()):
                idx = int(raw_idx.strip())
            else:
                continue
            if 1 <= idx <= n:
                return idx, str(obj.get("reason") or "")[:120]
    m = re.search(r'"?pick"?\s*[:=]\s*(\d+)(?![\d.])', body)
    if m and 1 <= int(m.group(1)) <= n:
        return int(m.group(1)), ""
    if re.fullmatch(r"\s*\d+\s*", body) and 1 <= int(body) <= n:
        return int(body), ""
    return None, ""


async def route(
    task: TaskInfo,
    pool: Sequence[PoolEntry],
    router_call: Optional[RouterCall],
    *,
    default_ref: str = "",
    exclude: Sequence[str] = (),
    max_candidates: int = 12,
    timeout: float = 15.0,
) -> RouteDecision:
    """Choose a pool entry. Raises NoRouteError only for a hard constraint (keep-local, nothing left to try, empty pool)."""
    cands, notes = prefilter(task, pool, exclude)
    if not cands:
        raise NoRouteError("The auto pool is empty. Add models to the pool first.")
    limit = max(1, int(max_candidates))
    preferred_default = next((e for e in cands if e.ref == default_ref), None)
    if len(cands) > limit:
        cands = cands[:limit]
        # Keep the configured fallback eligible even when it is later in the saved pool.
        if preferred_default and all(e.ref != preferred_default.ref for e in cands):
            cands[-1] = preferred_default
    default = next((e for e in cands if e.ref == default_ref), cands[0])
    if len(cands) == 1:
        return RouteDecision(cands[0], "only one eligible model", "only-candidate", notes, cands)
    if router_call is None:
        return RouteDecision(default, "no router model configured; using pool order", "fallback", notes, cands)
    try:
        reply = await asyncio.wait_for(router_call(build_router_messages(task, cands)), timeout=timeout)
    except Exception as exc:  # router down / slow / rate-limited: degrade, do not fail the chat
        notes.append(f"router unavailable ({type(exc).__name__})")
        return RouteDecision(default, "router unavailable; using pool order", "fallback", notes, cands)
    idx, why = parse_pick(reply, len(cands))
    if idx is None:
        notes.append("router reply unreadable")
        return RouteDecision(default, "router reply unreadable; using pool order", "fallback", notes, cands)
    return RouteDecision(cands[idx - 1], why or "router pick", "router", notes, cands)


# --------------------------------------------------------------------------- refusals
# Text heuristics only fire on SHORT replies that OPEN with a refusal; long answers that merely
# contain "I can't" somewhere are left alone. They will still miss some refusals and flag some
# non-refusals, which is why callers surface every attempt instead of acting silently.
_REFUSAL_OPENERS = [
    r"i\s*(?:'m|am)\s+sorry,?\s+(?:but\s+)?i\s+(?:can(?:no|')t|won'?t|am\s+(?:unable|not\s+able))",
    r"i\s+(?:can(?:no|')t|cannot|won'?t|will\s+not)\s+(?:help|assist|provide|comply|fulfil+|support|continue|do\s+that)",
    r"i(?:'m|\s+am)\s+(?:unable|not\s+able)\s+to\s+(?:help|assist|provide|comply|fulfil+)",
    r"(?:sorry,?\s+)?i\s+must\s+(?:decline|refuse)",
    r"as\s+an\s+ai(?:\s+language\s+model)?,?\s+i\s+(?:can(?:no|')t|cannot|am\s+unable)",
]
_REFUSAL_RE = re.compile(r"^\s*(?:" + "|".join(_REFUSAL_OPENERS) + r")", re.I)
_REFUSAL_MAX_CHARS = 700


def looks_like_refusal(text: str, *, finish_reason: str = "", stop_reason: str = "") -> bool:
    if (finish_reason or "").lower() == "content_filter" or (stop_reason or "").lower() == "refusal":
        return True
    body = (text or "").strip()
    return bool(body) and len(body) <= _REFUSAL_MAX_CHARS and bool(_REFUSAL_RE.match(body))


@dataclass
class Attempt:
    entry: PoolEntry
    outcome: str  # ok | error | refused
    detail: str = ""


@dataclass
class FallbackResult:
    text: str
    entry: Optional[PoolEntry]
    attempts: List[Attempt]
    all_declined: bool = False


async def answer_with_fallback(
    entries: Sequence[PoolEntry],
    call: EntryCall,
    messages: List[Dict[str, str]],
    *,
    on_refusal: bool = False,
    on_error: bool = True,
) -> FallbackResult:
    """Try entries in order. Moves on after an error and, if enabled, after a refusal.

    The same ``messages`` go to every model unchanged. If every model declined, the first
    refusal text is returned with ``all_declined=True`` so the user sees what happened.
    """
    attempts: List[Attempt] = []
    first_refusal: Optional[Tuple[PoolEntry, str]] = None
    for entry in entries:
        try:
            text = await call(entry, messages)
        except Exception as exc:
            attempts.append(Attempt(entry, "error", type(exc).__name__))
            if on_error:
                continue
            raise
        if on_refusal and looks_like_refusal(text):
            attempts.append(Attempt(entry, "refused", "declined"))
            if first_refusal is None:
                first_refusal = (entry, text)
            continue
        attempts.append(Attempt(entry, "ok"))
        return FallbackResult(text, entry, attempts)
    if first_refusal is not None:
        return FallbackResult(first_refusal[1], first_refusal[0], attempts, all_declined=True)
    return FallbackResult("", None, attempts, all_declined=False)
