# routes/provider_routes.py
"""Provider onboarding: pick a provider, paste a key, see its models.

These routes only *discover*. Saving is done by the existing ``POST /api/model-endpoints`` (which
encrypts the key and supports pinned models), so nothing about key storage changes.

Admin-only, like adding an endpoint. A cloud preset always talks to its own fixed address: a caller
can override the base URL only for local/custom providers, so a pasted key is never sent to a URL
someone typed for a cloud provider.
"""
import logging
from dataclasses import asdict

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.middleware import require_admin
from src import chatbox_ai, provider_presets as pp
from src.auth_helpers import get_current_user

logger = logging.getLogger(__name__)


class GuessBody(BaseModel):
    api_key: str = Field("", max_length=512)


class ModelsBody(BaseModel):
    provider: str = Field(..., max_length=40)
    api_key: str = Field("", max_length=512)
    base_url: str = Field("", max_length=300)


class ChatboxActivateBody(BaseModel):
    license_key: str = Field(..., max_length=2048)
    instance_name: str = Field("", max_length=64)


class KeyPoolAddBody(BaseModel):
    endpoint_id: str = Field(..., max_length=64)
    api_key: str = Field(..., max_length=2048)
    label: str = Field("", max_length=80)
    priority: int = Field(0, ge=-1000, le=1000)


class KeyPoolToggleBody(BaseModel):
    is_enabled: bool


def _endpoint_exists(endpoint_id: str) -> bool:
    from core.database import ModelEndpoint, get_db_session

    try:
        with get_db_session() as db:
            return (
                db.query(ModelEndpoint.id)
                .filter(ModelEndpoint.id == endpoint_id)
                .first()
                is not None
            )
    except Exception:  # pragma: no cover - storage failure answers 404 upstream
        logger.warning("Could not look up model endpoint %s", endpoint_id, exc_info=True)
        return False


def _chatbox_client(timeout: float = 20.0) -> httpx.AsyncClient:
    from src.tls_overrides import llm_verify

    # Never follow a redirect with a license key in the headers.
    return httpx.AsyncClient(timeout=timeout, verify=llm_verify(), follow_redirects=False)


def _chatbox_http_error(exc: "chatbox_ai.ChatboxError") -> HTTPException:
    """Keep upstream 401/403 out of the browser's session-expired path."""
    if exc.status in (401, 403, 404):
        return HTTPException(400, exc.message)
    if exc.status == 429:
        return HTTPException(429, exc.message)
    if exc.status is None:
        return HTTPException(502, exc.message)
    return HTTPException(400, exc.message)


def _http_status(err: "pp.DiscoveryError") -> int:
    # Never relay an upstream 401/403: the browser would read it as "your Odysseus session expired".
    if err.status in (401, 403, 404):
        return 400
    if err.status == 429:
        return 429
    if err.status is None and not err.message.startswith(("Paste", "Unknown", "A base URL", "The base URL")):
        return 502
    return 400


def setup_provider_routes() -> APIRouter:
    router = APIRouter(prefix="/api/providers", tags=["providers"])

    @router.get("/presets")
    def list_presets(request: Request):
        require_admin(request)
        return {"presets": pp.public_presets()}

    @router.post("/guess")
    def guess_provider(request: Request, body: GuessBody):
        require_admin(request)
        return {"candidates": pp.guess_provider(body.api_key)}

    @router.post("/models")
    async def provider_models(request: Request, body: ModelsBody):
        require_admin(request)
        preset = pp.get_preset(body.provider)
        if preset is None:
            raise HTTPException(400, "Unknown provider.")
        override = body.base_url.strip()
        if override and not (preset.local or preset.id == "custom"):
            raise HTTPException(400, "The address of a cloud provider is fixed; pick 'Other (OpenAI-compatible URL)' for a custom one.")
        base = override or preset.base_url
        local = False
        if (preset.local or preset.id == "custom") and base:
            # Inside Docker, "localhost" is the container; reuse the app's own rewrite so Ollama / LM Studio
            # and custom OpenAI-compatible services on the host are reachable as they are when added manually.
            # Classify the actual entered address; a local preset can be overridden with a remote URL.
            try:
                from routes.model_routes import _classify_endpoint, _rewrite_loopback_for_docker
                local = local or _classify_endpoint(base, "auto") == "local"
                base = _rewrite_loopback_for_docker(base)
            except Exception:  # pragma: no cover - best effort only
                logger.debug("loopback rewrite unavailable", exc_info=True)
        try:
            from src.tls_overrides import llm_verify
            found = await pp.discover(preset.id, body.api_key, base, verify=llm_verify())
        except pp.DiscoveryError as e:
            raise HTTPException(_http_status(e), e.message)
        cards = [{**asdict(c), "local": local} for c in found.cards]
        key_info = found.key_info or {}
        variants = []
        unsupported = []
        if preset.id == "chatboxai":
            # Persist the activated license (encrypted) so chat calls can send
            # Instance-Id. The raw detail and instance id stay server-side.
            owner = get_current_user(request) or None
            try:
                chatbox_ai.save_license(
                    owner,
                    body.api_key,
                    key_info.get("instance_id"),
                    key_info.get("license_detail"),
                    instance_name=key_info.get("instance_name") or None,
                )
            except Exception:
                # A storage failure must not hide a valid catalog: chat still
                # works with the key on the endpoint; only the seat header is lost.
                logger.warning("Could not persist the Chatbox AI license", exc_info=True)
            variants = key_info.get("variants") or []
            unsupported = key_info.get("unsupported") or []
            key_info = {
                k: v for k, v in key_info.items()
                if k not in {"instance_id", "license_detail"}
            }
        return {
            "provider": preset.id,
            "label": preset.label,
            "base_url": base,
            "local": local,
            "key_info": key_info,
            "variants": variants,
            "unsupported": unsupported,
            "count": len(cards),
            "free_count": sum(1 for c in cards if c.get("free")),
            "models": cards,
        }

    # ------------------------------------------------------------------ Chatbox AI
    @router.post("/chatbox/activate")
    async def chatbox_activate(request: Request, body: ChatboxActivateBody):
        """Activate a license without fetching models (status panel / re-activation)."""
        require_admin(request)
        owner = get_current_user(request) or None
        key = chatbox_ai.normalize_key(body.license_key)
        if not key:
            raise HTTPException(400, "Paste a Chatbox AI license key first.")
        try:
            async with _chatbox_client() as client:
                activation = await chatbox_ai.activate_license(
                    client, key, body.instance_name or None,
                )
                if not activation.get("valid"):
                    message = "Chatbox AI rejected this license key."
                    if activation.get("error"):
                        message += f" {activation['error']}"
                    raise HTTPException(400, message)
                detail, detail_error = await chatbox_ai.license_detail(client, key)
        except chatbox_ai.ChatboxError as exc:
            raise _chatbox_http_error(exc)
        try:
            chatbox_ai.save_license(
                owner, key, activation.get("instance_id"), detail,
                instance_name=body.instance_name or chatbox_ai.default_instance_name(),
            )
        except Exception:
            logger.warning("Could not persist the Chatbox AI license", exc_info=True)
            raise HTTPException(500, "The license was accepted but could not be stored.")
        return {
            "ok": True,
            "configured": True,
            "masked_key": chatbox_ai.mask_key(key),
            "summary": chatbox_ai.summarize_detail(detail),
            "detail_error": detail_error,
            "instance_name": body.instance_name or chatbox_ai.default_instance_name(),
        }

    @router.get("/chatbox/status")
    async def chatbox_status(request: Request, refresh: bool = False):
        """Plan, quota and expiry for the stored license. Never returns the key."""
        require_admin(request)
        owner = get_current_user(request) or None
        stored = chatbox_ai.load_license(owner)
        if not stored:
            return {"configured": False, "provider": "chatboxai"}
        detail = stored.get("detail")
        detail_error = None
        if refresh:
            try:
                async with _chatbox_client() as client:
                    detail, detail_error = await chatbox_ai.license_detail(
                        client, stored["license_key"],
                    )
            except chatbox_ai.ChatboxError as exc:
                # Keep the cached summary rather than blanking the panel on a blip.
                detail, detail_error = stored.get("detail"), {"code": "refresh_failed", "message": exc.message}
            if detail:
                try:
                    chatbox_ai.save_license(
                        owner, stored["license_key"], stored.get("instance_id"), detail,
                        instance_name=stored.get("instance_name") or None,
                    )
                except Exception:
                    logger.warning("Could not refresh the Chatbox AI license", exc_info=True)
        summary = chatbox_ai.summarize_detail(detail) or stored.get("summary") or {}
        return {
            "configured": True,
            "provider": "chatboxai",
            "masked_key": stored.get("masked_key") or "",
            "plan": summary.get("plan") or stored.get("plan") or "",
            "status": summary.get("status") or stored.get("status") or "",
            "summary": summary,
            "detail_error": detail_error,
            "instance_name": stored.get("instance_name") or "",
            "has_instance": bool(stored.get("instance_id")),
            "api_origin": chatbox_ai.api_origin(),
            "last_checked": (
                stored["last_checked"].isoformat()
                if getattr(stored.get("last_checked"), "isoformat", None) else None
            ),
        }

    @router.post("/chatbox/deactivate")
    async def chatbox_deactivate(request: Request):
        """Release the seat upstream, then remove the encrypted local row."""
        require_admin(request)
        owner = get_current_user(request) or None
        stored = chatbox_ai.load_license(owner)
        if not stored:
            return {"ok": True, "configured": False}
        warning = ""
        if stored.get("instance_id"):
            try:
                async with _chatbox_client() as client:
                    await chatbox_ai.deactivate_license(
                        client, stored["license_key"], stored["instance_id"],
                    )
            except chatbox_ai.ChatboxError as exc:
                # Local removal still matters (the key stops being used here);
                # the upstream seat may need to be freed from chatboxai.app.
                warning = exc.message
        disabled = 0
        try:
            disabled = chatbox_ai.disable_endpoints_for_key(stored["license_key"])
        except Exception:
            logger.warning("Could not disable Chatbox AI endpoints on unlink", exc_info=True)
        chatbox_ai.remove_license(owner)
        return {"ok": True, "configured": False, "warning": warning or None,
                "disabled_endpoints": disabled}

    # ------------------------------------------------------------------ key pool
    @router.get("/keys")
    async def key_pool_status(request: Request, endpoint_id: str = ""):
        """Masked credentials + live health for one endpoint's pool."""
        require_admin(request)
        from src import key_pool

        if not endpoint_id.strip():
            raise HTTPException(400, "endpoint_id is required.")
        if not _endpoint_exists(endpoint_id):
            raise HTTPException(404, "Unknown model endpoint.")
        return key_pool.describe_pool(endpoint_id)

    @router.post("/keys")
    async def key_pool_add(request: Request, body: KeyPoolAddBody):
        """Add one credential to an endpoint. The endpoint's own key stays first."""
        require_admin(request)
        from src import key_pool

        if not _endpoint_exists(body.endpoint_id):
            raise HTTPException(404, "Unknown model endpoint.")
        try:
            added = key_pool.add_key(
                body.endpoint_id,
                body.api_key,
                label=body.label.strip(),
                priority=body.priority,
                owner=get_current_user(request) or None,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return {"ok": True, **added, "pool": key_pool.describe_pool(body.endpoint_id)}

    @router.delete("/keys/{key_row_id}")
    async def key_pool_remove(request: Request, key_row_id: str):
        require_admin(request)
        from src import key_pool

        if not key_pool.remove_key(key_row_id):
            raise HTTPException(404, "Unknown pooled key.")
        return {"ok": True}

    @router.patch("/keys/{key_row_id}")
    async def key_pool_toggle(request: Request, key_row_id: str, body: KeyPoolToggleBody):
        require_admin(request)
        from src import key_pool

        if not key_pool.set_enabled(key_row_id, body.is_enabled):
            raise HTTPException(404, "Unknown pooled key.")
        return {"ok": True}

    @router.post("/keys/reset")
    async def key_pool_reset(request: Request, endpoint_id: str = ""):
        """Forget cooldowns/failure streaks (after topping up a provider quota)."""
        require_admin(request)
        from src import key_pool

        key_pool.reset(endpoint_id.strip() or None)
        return {"ok": True}

    return router
