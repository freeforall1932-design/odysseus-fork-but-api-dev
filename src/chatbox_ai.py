"""Chatbox AI (chatboxai.app) license and gateway client.

Odysseus can use a Chatbox AI subscription as a model provider: the user pastes
a license key from chatboxai.app, this module activates it, lists the models the
plan allows, and exposes the gateway base URLs the Chatbox desktop client uses.
The license key and its activated instance id are stored encrypted (Fernet, via
``EncryptedText``) and are never returned to the browser.

Wire contract mirrored from the Chatbox community client
(``src/shared/services/native-license.ts`` and
``src/renderer/packages/remote.ts`` upstream):

* ``POST /api/license/activate``      {licenseKey, instanceName} -> {valid, instanceId, error}
* ``POST /api/license/validate``      {licenseKey, instanceId}   -> {valid}
* ``POST /api/license/deactivate``    {licenseKey, instanceId}
* ``GET  /api/license/detail/realtime`` (Authorization: <licenseKey>) -> {data}
* ``POST /api/chatbox_ai/model_list`` {licenseKey, language} -> {data:{models, groups, ...}}
* ``POST /api/model_manifest``        {aiProvider:"ChatboxAI", licenseKey, language} -> {data}

Chat calls go to one of these gateways (same origin):

* ``/gateway/openai/v1``            OpenAI-compatible chat completions
* ``/gateway/anthropic/v1``         Anthropic-compatible messages
* ``/gateway/google-ai-studio/v1beta`` Gemini native (not implemented in Odysseus yet)
* ``/gateway/openai-responses/v1``  OpenAI Responses (not implemented in Odysseus yet)

The module is deliberately stdlib + httpx only. Database helpers import
``core.database`` lazily so the pure HTTP/parsing layer stays unit-testable
without a running app.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

DEFAULT_API_ORIGIN = "https://api.chatboxai.app"
# Origins the official client probes (chatboxai_pool.ts). A key is only ever
# sent to the origin the operator selected, never to an arbitrary redirect.
KNOWN_API_ORIGINS: Tuple[str, ...] = (
    "https://api.chatboxai.app",
    "https://chatboxai.app",
    "https://api.ai-chatbox.com",
    "https://api.chatboxapp.xyz",
)
GATEWAY_PATHS: Dict[str, str] = {
    "openai": "/gateway/openai/v1",
    "anthropic": "/gateway/anthropic/v1",
    "google": "/gateway/google-ai-studio/v1beta",
    "openai-responses": "/gateway/openai-responses/v1",
}
SUPPORTED_API_STYLES: Tuple[str, ...] = ("openai", "anthropic")
API_STYLE_LABELS: Dict[str, str] = {
    "openai": "OpenAI-compatible",
    "anthropic": "Claude (Anthropic gateway)",
    "google": "Gemini (native Google gateway)",
    "openai-responses": "OpenAI Responses",
}
DEFAULT_INSTANCE_NAME = "Odysseus"
INSTANCE_CACHE_TTL = 300.0
_MAX_ERROR_TEXT = 300
_MANIFEST_PROVIDER = "ChatboxAI"

_ORIGIN_ENV = "CHATBOX_API_ORIGIN"
_INSTANCE_ENV = "CHATBOX_INSTANCE_NAME"

# fingerprint -> (expires_at_monotonic, instance_id)
_INSTANCE_CACHE: Dict[str, Tuple[float, str]] = {}


class ChatboxError(Exception):
    """A user-presentable Chatbox failure. Never contains the license key."""

    def __init__(self, message: str, status: Optional[int] = None, code: str = ""):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code or ""


# --------------------------------------------------------------------------- origins
def _clean_origin(value: str) -> str:
    """Return a canonical http(s) origin or "" when the value is unusable."""
    raw = (value or "").strip().rstrip("/")
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        if parsed.scheme.lower() not in ("http", "https"):
            return ""
        if not parsed.hostname or parsed.username or parsed.password:
            return ""
        if parsed.query or parsed.fragment or (parsed.path or "").strip("/"):
            return ""
    except ValueError:
        return ""
    return raw


def api_origin() -> str:
    """Configured Chatbox API origin (operator env override, else the default)."""
    override = _clean_origin(os.environ.get(_ORIGIN_ENV, ""))
    if override:
        return override
    return DEFAULT_API_ORIGIN


def _known_hosts() -> set:
    hosts = set()
    for origin in (*KNOWN_API_ORIGINS, api_origin()):
        try:
            host = (urlparse(origin).hostname or "").lower()
        except ValueError:
            host = ""
        if host:
            hosts.add(host)
    return hosts


def is_chatbox_url(url: str) -> bool:
    """True when ``url`` belongs to a Chatbox API origin (host-exact match)."""
    try:
        parsed = urlparse((url or "").strip())
        host = (parsed.hostname or "").lower()
    except ValueError:
        return False
    if parsed.scheme.lower() not in ("http", "https") or not host:
        return False
    return host in _known_hosts()


def is_chatbox_anthropic_url(url: str) -> bool:
    """True for Chatbox's Anthropic-compatible gateway (Claude models)."""
    if not is_chatbox_url(url):
        return False
    try:
        path = urlparse((url or "").strip()).path or ""
    except ValueError:
        return False
    return "/gateway/anthropic/" in path


def gateway_base(api_style: str, origin: Optional[str] = None) -> str:
    """Gateway base URL for a Chatbox API style, or "" for an unknown style."""
    path = GATEWAY_PATHS.get((api_style or "").strip().lower())
    if not path:
        return ""
    return (origin or api_origin()).rstrip("/") + path


def origin_for_base(base: str) -> str:
    """Origin implied by a configured base URL, else the configured origin."""
    try:
        parsed = urlparse((base or "").strip())
        if parsed.scheme.lower() in ("http", "https") and parsed.hostname:
            candidate = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            if is_chatbox_url(candidate):
                return candidate
    except ValueError:
        pass
    return api_origin()


def infer_api_style(model_id: str, declared: Any = None) -> str:
    """Resolve a model's API style, preferring the server's declaration.

    Older catalogs omit ``apiStyle``; Chatbox's own client then falls back to
    the model id prefix (``claude-*`` -> Anthropic, ``gemini-*`` -> Google).
    """
    value = str(declared or "").strip().lower()
    if value in GATEWAY_PATHS:
        return value
    mid = str(model_id or "").strip().lower()
    if mid.startswith("gemini-"):
        return "google"
    if mid.startswith("claude-"):
        return "anthropic"
    return "openai"


def model_supported(api_style: str) -> bool:
    """Whether Odysseus can route this Chatbox API style today."""
    return (api_style or "").strip().lower() in SUPPORTED_API_STYLES


def default_instance_name() -> str:
    name = (os.environ.get(_INSTANCE_ENV, "") or "").strip()
    return name[:64] or DEFAULT_INSTANCE_NAME


# --------------------------------------------------------------------------- keys
def normalize_key(license_key: str) -> str:
    """Strip copy/paste whitespace without mangling an otherwise opaque key."""
    return re.sub(r"\s+", "", (license_key or "")).strip()


def fingerprint(license_key: str) -> str:
    """Non-secret lookup id for a license key."""
    return hashlib.sha256(normalize_key(license_key).encode("utf-8")).hexdigest()


def mask_key(license_key: str) -> str:
    """Show enough to recognise a key, never enough to reuse it."""
    key = normalize_key(license_key)
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "*" * max(0, len(key) - 2)
    return f"{key[:4]}…{key[-4:]}"


# --------------------------------------------------------------------------- HTTP
def _truncate(text: Any, limit: int = _MAX_ERROR_TEXT) -> str:
    value = str(text or "").strip().replace("\n", " ")
    return value[:limit]


def _error_message(payload: Any) -> Tuple[str, str]:
    """Extract (message, code) from Chatbox's ``{"error": ...}`` envelope."""
    if not isinstance(payload, dict):
        return "", ""
    error = payload.get("error")
    if isinstance(error, str):
        return _truncate(error), ""
    if isinstance(error, dict):
        message = error.get("message") or error.get("detail") or error.get("title") or ""
        code = error.get("code") or str(error.get("status") or "")
        return _truncate(message), _truncate(code, 64)
    return "", ""


def _status_message(status: int, label: str = "Chatbox AI") -> str:
    if status in (401, 403):
        return f"{label} rejected this license key (HTTP {status})."
    if status == 404:
        return f"{label} has no such API endpoint (HTTP 404). It may be temporarily unavailable."
    if status == 429:
        return f"{label} is rate-limiting requests (HTTP 429). Wait a moment and try again."
    if status >= 500:
        return f"{label} is having trouble right now (HTTP {status}). Try again later."
    return f"{label} answered with HTTP {status}."


async def _request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    json_body: Any = None,
    timeout: float = 20.0,
    label: str = "Chatbox AI",
) -> Any:
    """One request, no redirects, bounded error text, key never logged."""
    try:
        response = await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=timeout,
        )
    except httpx.TimeoutException:
        raise ChatboxError(f"{label} timed out. Check your connection and try again.")
    except httpx.HTTPError as exc:
        raise ChatboxError(f"Could not reach {label}: {type(exc).__name__}.")

    payload: Any = None
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = None

    if response.status_code >= 400:
        message, code = _error_message(payload)
        raise ChatboxError(message or _status_message(response.status_code, label),
                           status=response.status_code, code=code)
    if payload is None:
        raise ChatboxError(f"{label} returned an unreadable response.")
    return payload


def _json_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if extra:
        headers.update({str(k): str(v) for k, v in extra.items() if v})
    return headers


# --------------------------------------------------------------------------- license
async def activate_license(
    client: httpx.AsyncClient,
    license_key: str,
    instance_name: Optional[str] = None,
    *,
    origin: Optional[str] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    """Bind the key to one instance. Returns {valid, instance_id, error}."""
    key = normalize_key(license_key)
    if not key:
        return {"valid": False, "instance_id": "", "error": "Paste a Chatbox AI license key first."}
    payload = await _request_json(
        client,
        "POST",
        f"{(origin or api_origin()).rstrip('/')}/api/license/activate",
        headers=_json_headers(),
        json_body={"licenseKey": key, "instanceName": (instance_name or default_instance_name())[:64]},
        timeout=timeout,
    )
    data = payload.get("data") if isinstance(payload, dict) else None
    data = data if isinstance(data, dict) else {}
    return {
        "valid": bool(data.get("valid")),
        "instance_id": str(data.get("instanceId") or ""),
        "error": _truncate(data.get("error") or ""),
    }


async def validate_license(
    client: httpx.AsyncClient,
    license_key: str,
    instance_id: str,
    *,
    origin: Optional[str] = None,
    timeout: float = 20.0,
) -> bool:
    """Only an explicit boolean is authoritative (mirrors the upstream client)."""
    payload = await _request_json(
        client,
        "POST",
        f"{(origin or api_origin()).rstrip('/')}/api/license/validate",
        headers=_json_headers(),
        json_body={"licenseKey": normalize_key(license_key), "instanceId": instance_id or ""},
        timeout=timeout,
    )
    data = payload.get("data") if isinstance(payload, dict) else None
    valid = data.get("valid") if isinstance(data, dict) else None
    if not isinstance(valid, bool):
        raise ChatboxError("Chatbox AI did not understand the license validation response.")
    return valid


async def deactivate_license(
    client: httpx.AsyncClient,
    license_key: str,
    instance_id: str,
    *,
    origin: Optional[str] = None,
    timeout: float = 20.0,
) -> None:
    await _request_json(
        client,
        "POST",
        f"{(origin or api_origin()).rstrip('/')}/api/license/deactivate",
        headers=_json_headers(),
        json_body={"licenseKey": normalize_key(license_key), "instanceId": instance_id or ""},
        timeout=timeout,
    )


async def license_detail(
    client: httpx.AsyncClient,
    license_key: str,
    *,
    realtime: bool = True,
    origin: Optional[str] = None,
    timeout: float = 20.0,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
    """Plan, quotas and expiry. Returns (detail, error) instead of raising on auth errors.

    A transient 5xx/network failure raises so the caller can keep cached data; a
    401/403/4xx is a real "this key cannot be read" answer and is returned.
    """
    endpoint = "detail/realtime" if realtime else "detail/all_status"
    try:
        payload = await _request_json(
            client,
            "GET",
            f"{(origin or api_origin()).rstrip('/')}/api/license/{endpoint}",
            headers=_json_headers({"Authorization": normalize_key(license_key)}),
            timeout=timeout,
        )
    except ChatboxError as exc:
        if exc.status and 400 <= exc.status < 500:
            return None, {"code": exc.code or str(exc.status), "message": exc.message}
        raise
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None, {"code": "empty_detail", "message": "Chatbox AI returned no license detail."}
    # The upstream detail repeats the license in ``key``. It is never needed
    # here (the key is already stored separately) and must not ride along into
    # logs, JSON columns or a browser response.
    data = {k: v for k, v in data.items() if k not in {"key", "licenseKey", "license_key"}}
    return data, None


def summarize_detail(detail: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Browser-safe license summary: plan, quota, expiry. Never the key."""
    if not isinstance(detail, dict) or not detail:
        return {}

    def num(value: Any) -> Optional[float]:
        try:
            if value is None or isinstance(value, bool):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    expires_at = str(detail.get("expires_at") or detail.get("token_expire_time") or "")
    days_left = None
    if expires_at:
        try:
            parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            days_left = max(0, (parsed - datetime.now(timezone.utc)).days)
        except ValueError:
            days_left = None

    quotas = {
        "unified_used": num(detail.get("unified_token_usage")),
        "unified_limit": num(detail.get("unified_token_limit")),
        "remaining_unified": num(detail.get("remaining_quota_unified")),
        "remaining_quota_35": num(detail.get("remaining_quota_35")),
        "remaining_quota_4": num(detail.get("remaining_quota_4")),
        "remaining_images": num(detail.get("remaining_quota_image")),
        "images_used": num(detail.get("image_used_count")),
        "images_limit": num(detail.get("image_total_quota")),
        "expansion_pack_remaining": None,
    }
    pack_limit = num(detail.get("expansion_pack_limit"))
    pack_used = num(detail.get("expansion_pack_usage"))
    if pack_limit is not None:
        quotas["expansion_pack_remaining"] = max(0.0, pack_limit - (pack_used or 0.0))

    usage_details = detail.get("unified_token_usage_details")
    if isinstance(usage_details, list):
        quotas["usage_details"] = [
            {
                "type": _truncate(item.get("type"), 32),
                "used": num(item.get("token_usage")),
                "limit": num(item.get("token_limit")),
                "expires_at": _truncate(item.get("expires_at"), 64) or None,
            }
            for item in usage_details
            if isinstance(item, dict)
        ]

    return {
        "name": _truncate(detail.get("name"), 120),
        "plan": _truncate(detail.get("plan"), 64),
        "status": _truncate(detail.get("status"), 64),
        "expires_at": expires_at or None,
        "days_left": days_left,
        "recurring_canceled": bool(detail.get("recurring_canceled")),
        "payment_type": _truncate(detail.get("payment_type"), 32) or None,
        "quotas": {k: v for k, v in quotas.items() if v is not None},
    }


# --------------------------------------------------------------------------- catalog
def _unwrap(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else {}


def _int_or_none(value: Any) -> Optional[int]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _model_record(model_id: str, info: Dict[str, Any]) -> Dict[str, Any]:
    capabilities = info.get("capabilities") if isinstance(info.get("capabilities"), list) else []
    api_style = infer_api_style(model_id, info.get("apiStyle"))
    return {
        "id": model_id,
        "name": str(info.get("modelName") or info.get("nickname") or model_id),
        "description": _truncate(info.get("description"), 200),
        "api_style": api_style,
        "context_length": _int_or_none(info.get("contextWindow") or info.get("context_length")),
        "vision": "vision" in capabilities,
        "tools": "tool_use" in capabilities,
        "reasoning": "reasoning" in capabilities,
        "supported": model_supported(api_style),
    }


def parse_model_list(payload: Any) -> List[Dict[str, Any]]:
    """Parse ``/api/chatbox_ai/model_list`` (or a model manifest) into cards."""
    data = _unwrap(payload)
    models_by_id: Dict[str, Any] = {}
    raw_models = data.get("models")
    if isinstance(raw_models, dict):
        models_by_id.update({str(k): v for k, v in raw_models.items() if isinstance(v, dict)})
    elif isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, dict):
                mid = str(item.get("modelId") or item.get("id") or "").strip()
                if mid:
                    models_by_id[mid] = item

    order: List[str] = []
    groups = data.get("groups")
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            for key in ("featuredModelIds", "modelIds"):
                ids = group.get(key)
                if isinstance(ids, list):
                    for mid in ids:
                        mid = str(mid or "").strip()
                        if mid and mid in models_by_id and mid not in order:
                            order.append(mid)
    for mid in models_by_id:
        if mid not in order:
            order.append(mid)

    cards: List[Dict[str, Any]] = []
    seen = set()
    for mid in order:
        info = models_by_id.get(mid)
        if not isinstance(info, dict):
            continue
        model_type = str(info.get("type") or "").strip().lower()
        if model_type in {"embedding", "rerank", "image"}:
            continue
        if mid in seen:
            continue
        seen.add(mid)
        cards.append(_model_record(mid, info))
    return cards


async def fetch_model_list(
    client: httpx.AsyncClient,
    license_key: str,
    language: str = "en",
    *,
    origin: Optional[str] = None,
    timeout: float = 20.0,
) -> List[Dict[str, Any]]:
    payload = await _request_json(
        client,
        "POST",
        f"{(origin or api_origin()).rstrip('/')}/api/chatbox_ai/model_list",
        headers=_json_headers(),
        json_body={"licenseKey": normalize_key(license_key), "language": language},
        timeout=timeout,
    )
    return parse_model_list(payload)


async def fetch_model_manifest(
    client: httpx.AsyncClient,
    license_key: str,
    language: str = "en",
    *,
    origin: Optional[str] = None,
    timeout: float = 20.0,
) -> List[Dict[str, Any]]:
    """Fallback catalog. Public for old plans; still carries no secrets."""
    payload = await _request_json(
        client,
        "POST",
        f"{(origin or api_origin()).rstrip('/')}/api/model_manifest",
        headers=_json_headers(),
        json_body={"aiProvider": _MANIFEST_PROVIDER, "licenseKey": normalize_key(license_key), "language": language},
        timeout=timeout,
    )
    return parse_model_list(payload)


def group_variants(models: List[Dict[str, Any]], origin: Optional[str] = None) -> Dict[str, Any]:
    """Split cards into per-gateway endpoint variants the app can register.

    Odysseus speaks OpenAI chat-completions and Anthropic messages. Gemini's
    native gateway and the Responses gateway are catalogued but marked
    unsupported so the UI never offers a model the runtime cannot call.
    """
    variants: List[Dict[str, Any]] = []
    unsupported: Dict[str, List[str]] = {}
    for style, label in API_STYLE_LABELS.items():
        if not model_supported(style):
            continue
        ids = [m["id"] for m in models if m.get("api_style") == style]
        if not ids:
            continue
        variants.append({
            "api_style": style,
            "label": label,
            "base_url": gateway_base(style, origin),
            "model_ids": ids,
        })
    for model in models:
        style = str(model.get("api_style") or "openai")
        if model_supported(style):
            continue
        unsupported.setdefault(style, []).append(model["id"])
    return {
        "variants": variants,
        "unsupported": [
            {"api_style": style, "label": API_STYLE_LABELS.get(style, style), "model_ids": ids}
            for style, ids in unsupported.items()
        ],
    }


# --------------------------------------------------------------------------- storage
def _utcnow():
    from core.database import utcnow_naive

    return utcnow_naive()


def _clear_instance_cache(fingerprint_value: Optional[str] = None) -> None:
    if fingerprint_value:
        _INSTANCE_CACHE.pop(fingerprint_value, None)
    else:
        _INSTANCE_CACHE.clear()


def save_license(
    owner: Optional[str],
    license_key: str,
    instance_id: Optional[str],
    detail: Optional[Dict[str, Any]],
    *,
    instance_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Upsert the active license row for one owner. Returns a browser-safe summary."""
    from core.database import ChatboxAILicense, get_db_session

    key = normalize_key(license_key)
    if not key:
        raise ValueError("license_key is required")
    fp = fingerprint(key)
    owner_value = owner or None
    summary = summarize_detail(detail)
    with get_db_session() as db:
        row = (
            db.query(ChatboxAILicense)
            .filter(ChatboxAILicense.owner == owner_value)
            .filter(ChatboxAILicense.key_fingerprint == fp)
            .order_by(ChatboxAILicense.created_at.desc())
            .first()
        )
        if row is None:
            row = ChatboxAILicense(
                id=fp[:12],
                owner=owner_value,
                license_key=key,
                key_fingerprint=fp,
            )
            db.add(row)
        # Deactivate any older keys this owner still has marked active: only one
        # license can back the shared Chatbox endpoints at a time.
        db.query(ChatboxAILicense).filter(
            ChatboxAILicense.owner == owner_value,
            ChatboxAILicense.key_fingerprint != fp,
            ChatboxAILicense.is_active.is_(True),
        ).update({ChatboxAILicense.is_active: False}, synchronize_session=False)
        row.license_key = key
        row.is_active = True
        if instance_id:
            row.instance_id = instance_id
        if instance_name:
            row.instance_name = instance_name
        row.plan = (summary.get("plan") or None)
        row.status = (summary.get("status") or None)
        row.label = (summary.get("name") or summary.get("plan") or "Chatbox AI")
        if detail:
            row.detail = json.dumps(detail, ensure_ascii=False)
        row.last_checked = _utcnow()
        db.flush()
        result = {
            "id": row.id,
            "plan": row.plan,
            "status": row.status,
            "label": row.label,
            "instance_id": "yes" if row.instance_id else "",
        }
    _clear_instance_cache(fp)
    return result


def load_license(owner: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Server-side view of the active license (includes the raw key)."""
    from core.database import ChatboxAILicense, get_db_session

    owner_value = owner or None
    with get_db_session() as db:
        query = db.query(ChatboxAILicense).filter(ChatboxAILicense.is_active.is_(True))
        if owner_value is None:
            query = query.filter(ChatboxAILicense.owner.is_(None))
        else:
            query = query.filter(ChatboxAILicense.owner == owner_value)
        row = query.order_by(ChatboxAILicense.created_at.desc()).first()
        if row is None:
            return None
        detail = None
        if row.detail:
            try:
                detail = json.loads(row.detail)
            except (TypeError, ValueError):
                detail = None
        return {
            "id": row.id,
            "owner": row.owner,
            "license_key": row.license_key or "",
            "masked_key": mask_key(row.license_key or ""),
            "instance_id": row.instance_id or "",
            "instance_name": row.instance_name or "",
            "plan": row.plan or "",
            "status": row.status or "",
            "label": row.label or "",
            "detail": detail,
            "summary": summarize_detail(detail),
            "last_checked": row.last_checked,
        }


def disable_endpoints_for_key(license_key: str) -> int:
    """Disable model endpoints that hold this Chatbox license key.

    Unlinking must actually stop use: the endpoint rows keep working until the
    key is gone, so clear it and disable the row. The row itself is kept so the
    user can see what was connected and re-enable it after re-activation.
    """
    key = normalize_key(license_key)
    if not key:
        return 0
    from core.database import ModelEndpoint, get_db_session

    disabled = 0
    with get_db_session() as db:
        for endpoint in db.query(ModelEndpoint).all():
            if (getattr(endpoint, "api_key", None) or "").strip() != key:
                continue
            endpoint.api_key = None
            endpoint.is_enabled = False
            disabled += 1
    return disabled


def remove_license(owner: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Delete the owner's active row and return what was removed (server-side)."""
    from core.database import ChatboxAILicense, get_db_session

    removed = load_license(owner)
    if not removed:
        return None
    owner_value = owner or None
    with get_db_session() as db:
        query = db.query(ChatboxAILicense).filter(ChatboxAILicense.key_fingerprint == fingerprint(removed["license_key"]))
        if owner_value is None:
            query = query.filter(ChatboxAILicense.owner.is_(None))
        else:
            query = query.filter(ChatboxAILicense.owner == owner_value)
        query.delete(synchronize_session=False)
    _clear_instance_cache(fingerprint(removed["license_key"]))
    return removed


def instance_id_for_key(license_key: str) -> str:
    """Instance id bound to this key, from a short-lived process cache.

    Called from request-header building, so it must never raise or touch the
    network. A missing row simply means the key was not activated here.
    """
    key = normalize_key(license_key)
    if not key:
        return ""
    fp = fingerprint(key)
    now = time.monotonic()
    cached = _INSTANCE_CACHE.get(fp)
    if cached and cached[0] > now:
        return cached[1]
    try:
        from core.database import ChatboxAILicense, get_db_session

        with get_db_session() as db:
            row = (
                db.query(ChatboxAILicense)
                .filter(ChatboxAILicense.key_fingerprint == fp)
                .filter(ChatboxAILicense.is_active.is_(True))
                .order_by(ChatboxAILicense.created_at.desc())
                .first()
            )
            instance_id = (row.instance_id or "") if row is not None else ""
    except Exception:
        logger.debug("Chatbox instance lookup failed", exc_info=True)
        instance_id = ""
    _INSTANCE_CACHE[fp] = (now + INSTANCE_CACHE_TTL, instance_id)
    return instance_id


def auth_headers(license_key: Optional[str], url: str) -> Dict[str, str]:
    """Extra gateway headers for a Chatbox base URL (empty for other hosts).

    Chatbox bills/limits by activated instance, so the instance id rides along
    with the license key. It is not a secret; the key stays in Authorization
    (or x-api-key for the Anthropic gateway).
    """
    if not license_key or not is_chatbox_url(url):
        return {}
    instance_id = instance_id_for_key(license_key)
    return {"Instance-Id": instance_id} if instance_id else {}


# --------------------------------------------------------------------------- discovery
async def discover(
    api_key: str,
    *,
    client: httpx.AsyncClient,
    base_url: str = "",
    language: str = "en",
    instance_name: Optional[str] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    """Activate the key (if needed), read plan/quota and list usable models.

    Returns a dict shaped for ``provider_presets.Discovery.key_info`` plus a
    ``models`` list and gateway ``variants``. Raises :class:`ChatboxError` with
    a message safe to show in the provider dialog.

    Every failure path is scrubbed of the key: upstream text is not trusted to
    avoid echoing the credential it just rejected.
    """
    key = normalize_key(api_key)
    if not key:
        raise ChatboxError("Paste a Chatbox AI license key first.")
    try:
        return await _discover_with_key(
            key,
            client=client,
            base_url=base_url,
            language=language,
            instance_name=instance_name,
            timeout=timeout,
        )
    except ChatboxError as exc:
        if key and key in exc.message:
            exc.message = exc.message.replace(key, mask_key(key))
            exc.args = (exc.message,)
        raise


async def _discover_with_key(
    key: str,
    *,
    client: httpx.AsyncClient,
    base_url: str = "",
    language: str = "en",
    instance_name: Optional[str] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    origin = origin_for_base(base_url)
    name = (instance_name or default_instance_name())[:64]

    activation = await activate_license(client, key, name, origin=origin, timeout=timeout)
    if not activation.get("valid"):
        raise ChatboxError(
            "Chatbox AI rejected this license key."
            + (f" {activation['error']}" if activation.get("error") else "")
            + " Check the key at chatboxai.app, or paste it again."
        )
    instance_id = activation.get("instance_id") or ""

    detail, detail_error = await license_detail(client, key, realtime=True, origin=origin, timeout=timeout)
    summary = summarize_detail(detail)

    models: List[Dict[str, Any]] = []
    catalog_source = "model_list"
    try:
        models = await fetch_model_list(client, key, language, origin=origin, timeout=timeout)
    except ChatboxError:
        models = []
    if not models:
        models = await fetch_model_manifest(client, key, language, origin=origin, timeout=timeout)
        catalog_source = "model_manifest"
    if not models:
        raise ChatboxError("Chatbox AI returned no chat models for this license.")

    variants = group_variants(models, origin)
    return {
        "provider": "chatboxai",
        "api_origin": origin,
        "instance_id": instance_id,
        "instance_name": name,
        "masked_key": mask_key(key),
        "license_detail": detail,
        "license_detail_error": detail_error,
        "summary": summary,
        "catalog_source": catalog_source,
        "models": models,
        "variants": variants["variants"],
        "unsupported": variants["unsupported"],
    }
