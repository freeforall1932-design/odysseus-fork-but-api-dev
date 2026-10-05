# routes/auto_routes.py
"""Auto mode (a saved model pool + a router model) and the council runner.

Storage: the pool and its settings live in the per-user preferences store the UI already uses, under
``auto_pool`` and ``auto_settings``. These routes never create endpoints or keys; every model is
resolved through the existing endpoint resolver, which enforces ownership and ``is_enabled``.

Server-side truths the client cannot override:
  * ``local`` is recomputed from the endpoint's address, never taken from the request.
  * keep-local is HARD: it limits the router's candidates, skips a cloud router (so the message text is
    never sent to a cloud model), and rejects a council that includes any cloud model.
  * a refusal is surfaced, never hidden, and the prompt is never rewritten to get around it.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.database import ModelEndpoint, SessionLocal
from src import auto_router as ar
from src import council as cn
from src.auth_helpers import owner_filter, require_api_token_scope
from src.endpoint_resolver import resolve_endpoint_by_id
from src.llm_core import llm_call_async

logger = logging.getLogger(__name__)

POOL_KEY = "auto_pool"
SETTINGS_KEY = "auto_settings"
MAX_POOL = 60
MAX_SKILL_CHARS = 6000
DEFAULT_SETTINGS: Dict[str, Any] = {
    "router_ref": "",          # "endpoint_id::model" that picks the model (cloud or offline); "" = no router
    "default_ref": "",         # used when the router is unavailable or unreadable
    "keep_local_default": False,
    "refusal_fallback": False,  # reserved for the UI's "offer another model" button; never automatic
}


# --------------------------------------------------------------------------- request bodies
class PoolBody(BaseModel):
    pool: List[Dict[str, Any]] = Field(default_factory=list, max_length=MAX_POOL)
    settings: Dict[str, Any] = Field(default_factory=dict)


class RouteBody(BaseModel):
    message: str = Field("", max_length=20000)
    has_image: bool = False
    needs_tools: bool = False
    keep_local: Optional[bool] = None  # None -> the saved default
    exclude: List[str] = Field(default_factory=list, max_length=MAX_POOL)  # refs already tried


class PlanBody(BaseModel):
    mode: str = "debate"
    members: int = Field(4, ge=1, le=cn.MAX_MEMBERS)
    rounds: int = Field(2, ge=1, le=cn.MAX_ROUNDS)


class CouncilBody(BaseModel):
    question: str = Field(..., min_length=1, max_length=20000)
    mode: str = "debate"
    members: List[Dict[str, Any]] = Field(..., min_length=1, max_length=cn.MAX_MEMBERS)
    chair: str = Field(..., max_length=300)
    rounds: int = Field(2, ge=1, le=cn.MAX_ROUNDS)
    worker: str = Field("", max_length=300)
    draft: str = Field("", max_length=20000)
    skill: str = Field("", max_length=120)         # a skill NAME from the user's skill library
    skill_scope: str = "chair"                      # chair | all
    keep_local: Optional[bool] = None


# --------------------------------------------------------------------------- helpers
def _prefs():
    from routes import prefs_routes  # lazy: keeps this module cheap to import in tests
    return prefs_routes


def _endpoint_index(owner: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """{endpoint_id: {name, local}} for the endpoints this user may use. ``local`` is server-truth."""
    from routes.model_routes import _classify_endpoint  # lazy: heavy module
    db = SessionLocal()
    try:
        q = db.query(ModelEndpoint).filter(ModelEndpoint.is_enabled == True)  # noqa: E712
        if owner:
            q = owner_filter(q, ModelEndpoint, owner)
        out: Dict[str, Dict[str, Any]] = {}
        for r in q.all():
            kind = getattr(r, "endpoint_kind", None) or "auto"
            out[r.id] = {"name": r.name or r.id, "local": _classify_endpoint(r.base_url or "", kind) == "local"}
        return out
    finally:
        db.close()


def _clean_entry(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    ep = str(raw.get("endpoint_id") or "").strip()[:64]
    model = str(raw.get("model") or "").strip()[:200]
    if not ep or not model or "::" in ep:
        return None
    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = tags.split(",")
    elif not isinstance(tags, (list, tuple)):
        tags = []
    clean_tags: List[str] = []
    for t in tags[:8]:
        t = re.sub(r"[^a-z0-9 _+.\-]", "", str(t).strip().lower())[:24].strip()
        if t and t not in clean_tags:
            clean_tags.append(t)

    def _b(v: Any) -> Optional[bool]:
        return v if isinstance(v, bool) else None

    ctx = raw.get("context_length")
    ctx = int(ctx) if isinstance(ctx, (int, float)) and not isinstance(ctx, bool) and 0 < ctx <= 1_000_000_000 else None
    return {"endpoint_id": ep, "model": model, "label": str(raw.get("label") or "")[:80], "tags": clean_tags,
            "free": _b(raw.get("free")), "context_length": ctx, "vision": _b(raw.get("vision")), "tools": _b(raw.get("tools"))}


def _clean_ref(value: Any) -> str:
    ref = str(value or "").strip()[:300]
    ep, _, model = ref.partition("::")
    return ref if ep and model else ""


def _clean_settings(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}

    def flag(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value == 1
        return isinstance(value, str) and value.strip().lower() in {"true", "1", "yes", "on"}

    return {
        "router_ref": _clean_ref(raw.get("router_ref")),
        "default_ref": _clean_ref(raw.get("default_ref")),
        "keep_local_default": flag(raw.get("keep_local_default", False)),
        "refusal_fallback": flag(raw.get("refusal_fallback", False)),
    }


def _stored(owner: Optional[str]) -> tuple:
    prefs = _prefs()._load_for_user(owner)
    pool = [e for e in (_clean_entry(x) for x in (prefs.get(POOL_KEY) or [])[:MAX_POOL]) if e]
    settings = {**DEFAULT_SETTINGS, **_clean_settings(prefs.get(SETTINGS_KEY))}
    return pool, settings


def _pool_entries(pool: List[Dict[str, Any]], index: Dict[str, Dict[str, Any]]) -> List[ar.PoolEntry]:
    out: List[ar.PoolEntry] = []
    for e in pool:
        info = index.get(e["endpoint_id"])
        if info is None:  # endpoint deleted or disabled
            continue
        out.append(ar.PoolEntry.from_dict({**e, "local": info["local"], "label": e.get("label") or e["model"]}))
    return out


def _make_call(owner: Optional[str], *, timeout: int = 90, retries: int = 2) -> cn.CallFn:
    async def call(ref: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        ep_id, model = ar.split_ref(ref)
        resolved = resolve_endpoint_by_id(ep_id, model, owner=owner, require_exact_model=True)
        if not resolved:
            raise RuntimeError("model unavailable")
        url, m, headers = resolved
        return await llm_call_async(
            url, m, messages, temperature=temperature, max_tokens=max_tokens, headers=headers,
            timeout=timeout, max_retries=retries, workload="foreground",
        )
    return call


def _sse(obj: Any) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def setup_auto_routes(skills_manager=None) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["auto", "council"])

    # ---- pool ------------------------------------------------------------------------------
    @router.get("/auto/pool")
    def get_pool(request: Request):
        owner = require_api_token_scope(request, "chat")
        pool, settings = _stored(owner)
        index = _endpoint_index(owner)
        shown = []
        for e in pool:
            info = index.get(e["endpoint_id"])
            shown.append({**e, "available": info is not None, "local": bool(info and info["local"]),
                          "endpoint_name": (info or {}).get("name", "")})
        return {"pool": shown, "settings": settings, "max_pool": MAX_POOL,
                "endpoints": [{"id": k, **v} for k, v in index.items()]}

    @router.put("/auto/pool")
    def put_pool(request: Request, body: PoolBody):
        owner = require_api_token_scope(request, "chat")
        index = _endpoint_index(owner)
        seen, clean, dropped = set(), [], 0
        for raw in body.pool:
            e = _clean_entry(raw)
            key = (e["endpoint_id"], e["model"]) if e else None
            if not e or e["endpoint_id"] not in index or key in seen:
                dropped += 1
                continue
            seen.add(key)
            clean.append(e)
        settings = {**DEFAULT_SETTINGS, **_clean_settings(body.settings)}
        for k in ("router_ref", "default_ref"):  # refs must point at an endpoint this user can use
            ep, _, _m = settings[k].partition("::")
            if settings[k] and ep not in index:
                settings[k] = ""
        prefs = _prefs()
        stored = prefs._load_for_user(owner)
        stored[POOL_KEY] = clean
        stored[SETTINGS_KEY] = settings
        prefs._save_for_user(owner, stored)
        return {"saved": len(clean), "dropped": dropped, "settings": settings}

    # ---- routing ---------------------------------------------------------------------------
    @router.post("/auto/route")
    async def route_message(request: Request, body: RouteBody):
        owner = require_api_token_scope(request, "chat")
        pool, settings = _stored(owner)
        index = _endpoint_index(owner)
        entries = _pool_entries(pool, index)
        keep_local = settings["keep_local_default"] if body.keep_local is None else body.keep_local
        task = ar.TaskInfo(body.message, has_image=body.has_image, needs_tools=body.needs_tools, keep_local=keep_local)

        router_call = None
        notes: List[str] = []
        rref = settings["router_ref"]
        if rref:
            r_ep, _, _r_model = rref.partition("::")
            r_info = index.get(r_ep)
            if r_info is None:
                notes.append("router model unavailable")
            elif keep_local and not r_info["local"]:
                # The router would see the message text. Under keep-local that must stay on this machine.
                notes.append("router skipped (it is a cloud model and keep-local is on)")
            else:
                _call = _make_call(owner, timeout=15, retries=1)

                async def router_call(messages, _c=_call, _ref=rref):
                    return await _c(_ref, messages, 0.0, 120)
        try:
            d = await ar.route(task, entries, router_call, default_ref=settings["default_ref"], exclude=body.exclude)
        except ar.NoRouteError as e:
            raise HTTPException(409, str(e))
        return {
            "endpoint_id": d.entry.endpoint_id, "model": d.entry.model, "label": d.entry.label or d.entry.model,
            "local": d.entry.local, "reason": d.reason, "source": d.source, "notes": notes + d.notes,
            "candidates": [c.ref for c in d.candidates],
        }

    # ---- council ---------------------------------------------------------------------------
    @router.post("/council/plan")
    def council_plan(request: Request, body: PlanBody):
        require_api_token_scope(request, "chat")
        if body.mode not in cn.MODES:
            raise HTTPException(400, f"mode must be one of {', '.join(cn.MODES)}")
        return cn.plan(body.mode, body.members, body.rounds)

    @router.post("/council/run")
    async def council_run(request: Request, body: CouncilBody):
        owner = require_api_token_scope(request, "chat")
        skill_text = ""
        if body.skill:
            raw = skills_manager.read_skill_md(body.skill, owner=owner) if skills_manager else None
            if raw is None:
                raise HTTPException(404, f"Skill '{body.skill}' was not found.")
            from services.memory.skill_format import parse_frontmatter
            _meta, skill_text = parse_frontmatter(raw)
            skill_text = skill_text.strip()[:MAX_SKILL_CHARS]
        try:
            cfg = cn.config_from_dict(body.model_dump(exclude={"question", "skill", "keep_local"}), skill_text)
        except ValueError as e:
            raise HTTPException(400, str(e))

        index = _endpoint_index(owner)
        _pool, settings = _stored(owner)
        keep_local = settings["keep_local_default"] if body.keep_local is None else body.keep_local
        uses_worker = cfg.mode == "verify" and not cfg.draft.strip()
        refs = [m.ref for m in cfg.members] + [cfg.chair] + ([cfg.worker] if uses_worker and cfg.worker else [])
        for ref in refs:
            ep_id, model = ar.split_ref(ref)
            if ep_id not in index or not model:
                raise HTTPException(400, f"Model not available: {model or ref}")
            if keep_local and not index[ep_id]["local"]:
                raise HTTPException(409, f"Keep-local is on, but {model} is a cloud model. Use offline models only, or turn keep-local off.")

        call = _make_call(owner)

        async def stream():
            try:
                async for ev in cn.run_council(body.question, cfg, call):
                    yield _sse(ev)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("council run failed")
                yield _sse({"type": "error", "message": "The council failed unexpectedly."})
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return router
