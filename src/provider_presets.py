"""Provider presets and key-based model discovery.

The point: pick a provider, paste a key, see its models - no base-URL copy/paste
(the Jan / AnythingLLM flow).

Self-contained on purpose (httpx + stdlib only) so it can be unit-tested without the
web app. It never touches the database and never logs keys. The HTTP layer lives in
routes/provider_routes.py; the chosen models are then saved through the *existing*
``POST /api/model-endpoints`` route, which already supports pinned models, so the
endpoint record, the key encryption and the model picker all behave as before.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx

_MAX_PAGES = 10


# --------------------------------------------------------------------------- presets
@dataclass(frozen=True)
class ProviderPreset:
    id: str
    label: str
    base_url: str
    flavor: str = "openai"  # openai | openrouter | google | anthropic
    needs_key: bool = True
    local: bool = False
    key_prefixes: tuple = ()
    key_url: str = ""
    note: str = ""


PRESETS: tuple = (
    ProviderPreset(
        "openrouter", "OpenRouter", "https://openrouter.ai/api/v1", flavor="openrouter",
        key_prefixes=("sk-or-",), key_url="https://openrouter.ai/keys",
        note="One key, hundreds of models. Free models are detected from the pricing data.",
    ),
    ProviderPreset(
        "google", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai",
        flavor="google", key_prefixes=("AIza",), key_url="https://aistudio.google.com/apikey",
        note="Use an AI Studio key. Whether a model is free depends on your quota, so it is not flagged.",
    ),
    ProviderPreset(
        "openai", "OpenAI", "https://api.openai.com/v1",
        key_prefixes=("sk-",), key_url="https://platform.openai.com/api-keys",
    ),
    ProviderPreset(
        "anthropic", "Anthropic", "https://api.anthropic.com/v1", flavor="anthropic",
        key_prefixes=("sk-ant-",), key_url="https://console.anthropic.com/settings/keys",
    ),
    ProviderPreset(
        "groq", "Groq", "https://api.groq.com/openai/v1",
        key_prefixes=("gsk_",), key_url="https://console.groq.com/keys",
    ),
    ProviderPreset(
        "mistral", "Mistral", "https://api.mistral.ai/v1",
        key_url="https://console.mistral.ai/api-keys",
    ),
    ProviderPreset(
        "deepseek", "DeepSeek", "https://api.deepseek.com/v1",
        key_prefixes=("sk-",), key_url="https://platform.deepseek.com/api_keys",
    ),
    ProviderPreset(
        "together", "Together AI", "https://api.together.xyz/v1",
        key_url="https://api.together.ai/settings/api-keys",
    ),
    ProviderPreset(
        "cerebras", "Cerebras", "https://api.cerebras.ai/v1",
        key_prefixes=("csk-",), key_url="https://cloud.cerebras.ai",
    ),
    ProviderPreset(
        "nvidia", "NVIDIA NIM", "https://integrate.api.nvidia.com/v1",
        key_prefixes=("nvapi-",), key_url="https://build.nvidia.com",
    ),
    ProviderPreset(
        "xai", "xAI", "https://api.x.ai/v1",
        key_prefixes=("xai-",), key_url="https://console.x.ai",
    ),
    ProviderPreset(
        "huggingface", "Hugging Face", "https://router.huggingface.co/v1",
        key_prefixes=("hf_",), key_url="https://huggingface.co/settings/tokens",
    ),
    ProviderPreset(
        "ollama", "Ollama (local)", "http://localhost:11434/v1",
        needs_key=False, local=True,
        note="Offline model on this machine. Inside Docker the host is rewritten automatically.",
    ),
    ProviderPreset(
        "lmstudio", "LM Studio (local)", "http://localhost:1234/v1",
        needs_key=False, local=True,
        note="Offline model on this machine. Start LM Studio's local server first.",
    ),
    ProviderPreset(
        "custom", "Other (OpenAI-compatible URL)", "", needs_key=False,
        note="Any OpenAI-compatible server. Paste its base URL; the key is optional.",
    ),
)

_BY_ID = {p.id: p for p in PRESETS}


def get_preset(preset_id: str) -> Optional[ProviderPreset]:
    return _BY_ID.get((preset_id or "").strip().lower())


def public_presets() -> List[Dict[str, Any]]:
    """JSON-ready preset list for the UI (no secrets live here)."""
    return [asdict(p) for p in PRESETS]


# Order matters: the longer / more specific prefixes first.
_PREFIX_RULES = (
    ("sk-or-", "openrouter"),
    ("sk-ant-", "anthropic"),
    ("AIza", "google"),
    ("gsk_", "groq"),
    ("xai-", "xai"),
    ("nvapi-", "nvidia"),
    ("hf_", "huggingface"),
    ("csk-", "cerebras"),
)


def guess_provider(api_key: str) -> List[str]:
    """Best-effort provider guess from a key's prefix.

    Returns one id when the prefix is distinctive, several when it is ambiguous (plain
    ``sk-`` is used by OpenAI and DeepSeek, among others), and ``[]`` when unknown.
    The UI only pre-selects a provider; the user always has the final say.
    """
    key = (api_key or "").strip()
    for prefix, preset_id in _PREFIX_RULES:
        if key.startswith(prefix):
            return [preset_id]
    if key.startswith("sk-"):
        return ["openai", "deepseek"]
    return []


# --------------------------------------------------------------------------- model cards
@dataclass
class ModelCard:
    id: str
    name: str = ""
    context_length: Optional[int] = None
    free: Optional[bool] = None  # only known where the provider publishes pricing (OpenRouter)
    vision: Optional[bool] = None
    tools: Optional[bool] = None
    reasoning: Optional[bool] = None
    local: bool = False


class DiscoveryError(Exception):
    """A user-presentable failure. Never contains the key or a response body."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class Discovery:
    cards: List[ModelCard]
    key_info: Optional[Dict[str, Any]] = None  # e.g. {"is_free_tier": True, "label": "sk-or-v1-abc...xyz"}


_NON_CHAT = re.compile(
    r"(embed|whisper|tts|dall-e|moderation|rerank|imagen|veo-|stable-diffusion|sdxl|flux|transcribe|speech)",
    re.I,
)
_NON_CHAT_TYPES = {"embedding", "image", "moderation", "rerank", "audio", "transcribe", "video", "tts"}
_CTX_KEYS = ("context_length", "context_window", "max_context_length", "max_model_len", "n_ctx")


def _int_or_none(value: Any) -> Optional[int]:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _is_zero_price(value: Any) -> Optional[bool]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- parsers
def parse_openrouter(data: Any) -> List[ModelCard]:
    items = data.get("data") if isinstance(data, dict) else data
    cards: List[ModelCard] = []
    for m in items or []:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not mid:
            continue
        arch = m.get("architecture") if isinstance(m.get("architecture"), dict) else {}
        outs = arch.get("output_modalities")
        if isinstance(outs, list) and "text" not in outs:
            continue  # image/audio-only generators are not chat models
        ins = arch.get("input_modalities") if isinstance(arch.get("input_modalities"), list) else []
        params = m.get("supported_parameters") if isinstance(m.get("supported_parameters"), list) else []
        pricing = m.get("pricing") if isinstance(m.get("pricing"), dict) else None
        if mid.endswith(":free"):
            free: Optional[bool] = True
        elif pricing is None:
            free = None
        else:
            prompt_free = _is_zero_price(pricing.get("prompt"))
            completion_free = _is_zero_price(pricing.get("completion"))
            free = False if prompt_free is False or completion_free is False else (
                True if prompt_free is True and completion_free is True else None
            )
        cards.append(ModelCard(
            id=mid,
            name=str(m.get("name") or mid),
            context_length=_int_or_none(m.get("context_length")),
            free=free,
            vision="image" in ins,
            tools="tools" in params,
            reasoning=("reasoning" in params) or ("include_reasoning" in params),
        ))
    return cards


def parse_google(data: Any) -> List[ModelCard]:
    cards: List[ModelCard] = []
    for item in (data.get("models") if isinstance(data, dict) else None) or []:
        if not isinstance(item, dict):
            continue
        methods = item.get("supportedGenerationMethods")
        if not isinstance(methods, list) or "generateContent" not in methods:
            continue
        raw = str(item.get("baseModelId") or item.get("name") or "").strip()
        mid = raw[len("models/"):] if raw.startswith("models/") else raw
        if not mid or _NON_CHAT.search(mid):
            continue
        cards.append(ModelCard(
            id=mid,
            name=str(item.get("displayName") or mid),
            context_length=_int_or_none(item.get("inputTokenLimit")),
        ))
    return cards


def parse_anthropic(data: Any) -> List[ModelCard]:
    cards: List[ModelCard] = []
    for m in (data.get("data") if isinstance(data, dict) else None) or []:
        if isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"]:
            cards.append(ModelCard(id=m["id"], name=str(m.get("display_name") or m["id"])))
    return cards


def parse_openai_style(data: Any, *, local: bool = False) -> List[ModelCard]:
    items = data if isinstance(data, list) else ((data or {}).get("data") if isinstance(data, dict) else None)
    cards: List[ModelCard] = []
    seen = set()
    for m in items or []:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not mid or mid in seen or _NON_CHAT.search(mid):
            continue
        if str(m.get("type") or "").lower() in _NON_CHAT_TYPES:
            continue
        seen.add(mid)
        ctx = next((_int_or_none(m.get(k)) for k in _CTX_KEYS if _int_or_none(m.get(k))), None)
        cards.append(ModelCard(id=mid, name=str(m.get("name") or m.get("display_name") or mid),
                               context_length=ctx, local=local))
    return cards


# --------------------------------------------------------------------------- fetching
def _friendly_status(label: str, status: int) -> DiscoveryError:
    if status == 401:
        return DiscoveryError(f"{label} rejected this key (HTTP 401). Check that it is a valid key for {label}.", status)
    if status == 403:
        return DiscoveryError(
            f"{label} refused the request (HTTP 403). The key may be invalid or lack access, or a firewall/proxy may be blocking the connection.",
            status,
        )
    if status == 404:
        return DiscoveryError(f"{label} has no model list at that address (HTTP 404). Check the base URL.", status)
    if status == 429:
        return DiscoveryError(f"{label} is rate-limiting requests (HTTP 429). Wait a moment and try again.", status)
    return DiscoveryError(f"{label} answered with HTTP {status}.", status)


async def _get_json(client: httpx.AsyncClient, url: str, headers: Dict[str, str], params: Optional[dict], label: str) -> Any:
    try:
        r = await client.get(url, headers=headers, params=params)
    except httpx.TimeoutException:
        raise DiscoveryError(f"Timed out reaching {urlparse(url).hostname}.")
    except httpx.HTTPError as e:
        raise DiscoveryError(f"Could not reach {urlparse(url).hostname}: {type(e).__name__}.")
    if r.status_code >= 400:
        raise _friendly_status(label, r.status_code)
    try:
        return r.json()
    except ValueError:
        raise DiscoveryError(f"{label} did not return a model list (response was not JSON).")


def _same_origin(a: str, b: str) -> bool:
    """Compare scheme, host and effective port before forwarding credential headers."""
    try:
        left, right = urlparse(a), urlparse(b)
        if any((left.username, left.password, left.fragment, right.username, right.password, right.fragment)):
            return False
        def origin(parsed):
            scheme = parsed.scheme.lower()
            host = (parsed.hostname or "").lower()
            if not host or scheme not in ("http", "https"):
                return None
            port = parsed.port if parsed.port is not None else (443 if scheme == "https" else 80)
            return scheme, host, port
        return origin(left) is not None and origin(left) == origin(right)
    except ValueError:
        return False


async def _openrouter_key_info(client: httpx.AsyncClient, base: str, key: str) -> Optional[Dict[str, Any]]:
    """Validate the key with OpenRouter's GET /key (the model list itself is public, so a typo'd key
    would otherwise look fine until the first chat). Only an explicit 401/403 is treated as a bad key;
    anything else (network blip, endpoint change) just means "no extra info"."""
    try:
        r = await client.get(base.rstrip("/") + "/key", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    except httpx.HTTPError:
        return None
    if r.status_code in (401, 403):
        raise _friendly_status("OpenRouter", r.status_code)
    if r.status_code >= 400:
        return None
    try:
        payload = r.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return None
    label = str(data.get("label") or "")
    free_tier = data.get("is_free_tier")
    return {
        "is_free_tier": free_tier if isinstance(free_tier, bool) else None,
        "label": label[:48] if label and key not in label else None,
    }


async def _fetch_openrouter(client, preset: ProviderPreset, base: str, key: str) -> List[ModelCard]:
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    url, cards, seen = base.rstrip("/") + "/models", [], set()
    for _ in range(_MAX_PAGES):
        data = await _get_json(client, url, headers, None, preset.label)
        for c in parse_openrouter(data):
            if c.id not in seen:
                seen.add(c.id)
                cards.append(c)
        nxt = ((data.get("links") or {}).get("next")) if isinstance(data, dict) else None
        if not nxt:
            break
        nxt_url = urljoin(base.rstrip("/") + "/", str(nxt))
        if not _same_origin(nxt_url, base):  # never forward credentials off the provider's origin
            break
        url = nxt_url
    return cards


async def _fetch_google(client, preset: ProviderPreset, base: str, key: str) -> List[ModelCard]:
    root = base.rstrip("/")
    if root.endswith("/openai"):
        root = root[: -len("/openai")]
    headers = {"Accept": "application/json", "x-goog-api-key": key}
    cards, seen, token = [], set(), ""
    for _ in range(_MAX_PAGES):
        params: Dict[str, Any] = {"pageSize": 1000}
        if token:
            params["pageToken"] = token
        data = await _get_json(client, root + "/models", headers, params, preset.label)
        for c in parse_google(data):
            if c.id not in seen:
                seen.add(c.id)
                cards.append(c)
        token = str((data or {}).get("nextPageToken") or "") if isinstance(data, dict) else ""
        if not token:
            break
    return cards


async def _fetch_anthropic(client, preset: ProviderPreset, base: str, key: str) -> List[ModelCard]:
    root = base.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    headers = {"Accept": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}
    cards, seen, after = [], set(), ""
    for _ in range(_MAX_PAGES):
        params: Dict[str, Any] = {"limit": 1000}
        if after:
            params["after_id"] = after
        data = await _get_json(client, root + "/v1/models", headers, params, preset.label)
        for c in parse_anthropic(data):
            if c.id not in seen:
                seen.add(c.id)
                cards.append(c)
        after = str((data or {}).get("last_id") or "") if isinstance(data, dict) else ""
        if not (isinstance(data, dict) and data.get("has_more") and after):
            break
    return cards


async def _fetch_openai_style(client, preset: ProviderPreset, base: str, key: str) -> List[ModelCard]:
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = await _get_json(client, base.rstrip("/") + "/models", headers, None, preset.label)
    return parse_openai_style(data, local=preset.local)


_FETCHERS = {
    "openrouter": _fetch_openrouter,
    "google": _fetch_google,
    "anthropic": _fetch_anthropic,
    "openai": _fetch_openai_style,
}


async def discover(
    preset_id: str,
    api_key: str = "",
    base_url: str = "",
    *,
    client: Optional[httpx.AsyncClient] = None,
    timeout: float = 20.0,
    verify: Any = True,
) -> Discovery:
    """List the chat models a key can use, plus key info where the provider offers it.

    ``base_url`` overrides the preset's address (needed for ``custom``, and useful for
    self-hosted proxies). Raises :class:`DiscoveryError` with a message safe to show.
    """
    preset = get_preset(preset_id)
    if preset is None:
        raise DiscoveryError(f"Unknown provider '{preset_id}'.")
    key = (api_key or "").strip()
    if preset.needs_key and not key:
        raise DiscoveryError(f"Paste your {preset.label} API key first.")
    base = (base_url or preset.base_url or "").strip()
    if not base:
        raise DiscoveryError("A base URL is required for this provider.")
    try:
        parsed_base = urlparse(base)
        hostname = parsed_base.hostname
        port = parsed_base.port
    except ValueError:
        raise DiscoveryError("The base URL must be a valid http:// or https:// URL.")
    if parsed_base.scheme.lower() not in ("http", "https") or not hostname or any(c.isspace() for c in base):
        raise DiscoveryError("The base URL must be a valid http:// or https:// URL.")
    if parsed_base.username is not None or parsed_base.password is not None:
        raise DiscoveryError("The base URL must not contain embedded credentials.")
    if parsed_base.fragment:
        raise DiscoveryError("The base URL must not include a fragment.")
    if port == 0:
        raise DiscoveryError("The base URL port must be between 1 and 65535.")

    fetch = _FETCHERS.get(preset.flavor, _fetch_openai_style)
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=timeout, verify=verify, follow_redirects=False)
    key_info: Optional[Dict[str, Any]] = None
    try:
        if preset.flavor == "openrouter" and key:
            key_info = await _openrouter_key_info(client, base, key)  # fail fast on a bad key
        cards = await fetch(client, preset, base, key)
    finally:
        if owns_client:
            await client.aclose()
    if not cards:
        raise DiscoveryError(f"{preset.label} returned no chat models for this key.")
    return Discovery(cards=cards, key_info=key_info)


async def discover_models(preset_id: str, api_key: str = "", base_url: str = "", **kw: Any) -> List[ModelCard]:
    """Convenience wrapper around :func:`discover` that returns only the model cards."""
    return (await discover(preset_id, api_key, base_url, **kw)).cards
