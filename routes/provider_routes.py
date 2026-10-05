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

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.middleware import require_admin
from src import provider_presets as pp

logger = logging.getLogger(__name__)


class GuessBody(BaseModel):
    api_key: str = Field("", max_length=512)


class ModelsBody(BaseModel):
    provider: str = Field(..., max_length=40)
    api_key: str = Field("", max_length=512)
    base_url: str = Field("", max_length=300)


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
        return {
            "provider": preset.id,
            "label": preset.label,
            "base_url": base,
            "local": local,
            "key_info": found.key_info,
            "count": len(cards),
            "free_count": sum(1 for c in cards if c.get("free")),
            "models": cards,
        }

    return router
