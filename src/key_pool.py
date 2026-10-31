"""Multi-key rotation ("key pool") for bring-your-own API keys.

One provider, several keys. When a key is rate-limited or its quota is spent,
the next healthy key of the same endpoint picks the request up, so a single
chat keeps going instead of stopping at a cutoff. There is no separate memory
to share: the conversation (messages, tool results, session row) is owned by
the session, and a rotation only swaps the *credential* underneath it — the
next key receives the exact same transcript, which is what makes the switch
invisible to the user.

Design notes
------------

* Credentials live in ``provider_keys`` (encrypted at rest). The endpoint's own
  ``ModelEndpoint.api_key`` is treated as the first member of its pool, so an
  existing single-key endpoint keeps working unchanged and pool rows are purely
  additive.
* Health lives in **process memory**, keyed by ``(endpoint_id, fingerprint)``.
  Rotating a credential must never require a database write on the chat path,
  and after a restart every key deserves a fresh try anyway. Cooldowns are
  therefore advisory: the worst case after a restart is one retried key.
* Only key-scoped failures rotate: 401/402/403 and 429. A 5xx, a timeout, or a
  network error is a *provider* problem, and switching keys would only burn
  the next credential's quota — those stay with the existing host-cooldown and
  fallback machinery in ``src/llm_core.py``.
* Selection is deterministic: enabled keys that are not cooling down are tried
  by ``priority`` then least-recently-used, so a pool of equal priorities
  round-robins under load and a pooled key that has never been used is tried
  before one that saw traffic.

Nothing here performs network I/O or logs a raw key.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Failures that belong to the credential, not to the provider.
KEY_SCOPED_STATUSES = frozenset({401, 402, 403, 429})

# Cooldowns in seconds. 429 honors Retry-After when the provider sends one.
_RATE_LIMIT_COOLDOWN = 60.0
_INVALID_KEY_COOLDOWN = 3600.0
_QUOTA_EXHAUSTED_COOLDOWN = 1800.0
_MAX_COOLDOWN = 6 * 3600.0
# A 5xx/timeout streak is not key-scoped, but a key that keeps hitting them is
# still suspect: cool it briefly after this many consecutive failures.
_SOFT_FAILURE_COOLDOWN_AFTER = 3
_SOFT_FAILURE_COOLDOWN = 30.0

_ENV_DISABLE = "ODYSSEUS_KEY_POOL_DISABLED"

_QUOTA_MARKERS = (
    "insufficient_quota",
    "insufficient quota",
    "quota exceeded",
    "exceeded your current quota",
    "out of credits",
    "credit balance is too low",
    "billing",
)


def pool_enabled() -> bool:
    """Master switch. Rotation is opt-in only in the sense that a pool needs
    at least two keys, but operators can disable it wholesale for debugging."""
    return str(os.environ.get(_ENV_DISABLE, "")).strip().lower() not in {"1", "true", "yes"}


# --------------------------------------------------------------------------- keys


def normalize_key(value: Optional[str]) -> str:
    return (value or "").strip()


def fingerprint(api_key: Optional[str]) -> str:
    """Stable, non-secret lookup id for a key."""
    return hashlib.sha256(normalize_key(api_key).encode("utf-8")).hexdigest()


def mask_key(api_key: Optional[str]) -> str:
    """``sk-live…1a2b`` — enough to tell two keys apart, never enough to use one."""
    key = normalize_key(api_key)
    if not key:
        return ""
    if len(key) <= 8:
        return key[0] + "…" if len(key) > 1 else "…"
    return f"{key[:6]}…{key[-4:]}"


def key_id(api_key: Optional[str]) -> str:
    return fingerprint(api_key)[:16]


def cooldown_for_status(
    status: Optional[int],
    retry_after: Optional[float] = None,
    body: Optional[str] = None,
) -> float:
    """How long to rest a key after this failure."""
    text = (body or "").lower()
    if status == 401:
        return _INVALID_KEY_COOLDOWN
    if status == 402:
        return _QUOTA_EXHAUSTED_COOLDOWN
    if status == 403 and any(marker in text for marker in _QUOTA_MARKERS):
        return _QUOTA_EXHAUSTED_COOLDOWN
    if status == 429:
        if retry_after and retry_after > 0:
            return min(float(retry_after), _MAX_COOLDOWN)
        return _RATE_LIMIT_COOLDOWN
    return 0.0


def parse_retry_after(value: Any) -> Optional[float]:
    """``Retry-After`` as seconds. HTTP-date form is ignored (rare for APIs)."""
    if value is None:
        return None
    try:
        seconds = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if seconds < 0 or seconds > _MAX_COOLDOWN:
        return None
    return seconds


def is_key_scoped_failure(status: Optional[int], body: Optional[str] = None) -> bool:
    if status in KEY_SCOPED_STATUSES:
        return True
    text = (body or "").lower()
    return bool(status and status >= 400 and any(marker in text for marker in _QUOTA_MARKERS))


# --------------------------------------------------------------------------- state


@dataclass
class KeyHealth:
    fingerprint: str
    cooldown_until: float = 0.0
    failures: int = 0
    successes: int = 0
    last_status: Optional[int] = None
    last_error: str = ""
    last_used: float = 0.0

    def cooling(self, now: Optional[float] = None) -> bool:
        return self.cooldown_until > (now if now is not None else time.monotonic())


_LOCK = threading.Lock()
# (endpoint_id, fingerprint) -> KeyHealth
_HEALTH: Dict[Tuple[str, str], KeyHealth] = {}


def _health(endpoint_id: str, key_fp: str) -> KeyHealth:
    entry = _HEALTH.get((endpoint_id, key_fp))
    if entry is None:
        entry = KeyHealth(fingerprint=key_fp)
        _HEALTH[(endpoint_id, key_fp)] = entry
    return entry


def reset(endpoint_id: Optional[str] = None) -> None:
    """Drop runtime health. ``None`` clears every endpoint (tests, admin reset)."""
    with _LOCK:
        if endpoint_id is None:
            _HEALTH.clear()
            _POOL_CACHE.clear()
            return
        _POOL_CACHE.pop(endpoint_id, None)
        for composite in [c for c in _HEALTH if c[0] == endpoint_id]:
            _HEALTH.pop(composite, None)


def record_success(endpoint_id: str, api_key: Optional[str], *, now: Optional[float] = None) -> None:
    key_fp = fingerprint(api_key)
    if not key_fp or not endpoint_id:
        return
    stamp = now if now is not None else time.monotonic()
    with _LOCK:
        entry = _health(endpoint_id, key_fp)
        entry.successes += 1
        entry.failures = 0
        entry.cooldown_until = 0.0
        entry.last_status = None
        entry.last_error = ""
        entry.last_used = stamp


def record_failure(
    endpoint_id: str,
    api_key: Optional[str],
    *,
    status: Optional[int] = None,
    body: Optional[str] = None,
    retry_after: Optional[float] = None,
    message: str = "",
    now: Optional[float] = None,
) -> float:
    """Record a failure and return the cooldown applied (seconds, 0 = none)."""
    key_fp = fingerprint(api_key)
    if not key_fp or not endpoint_id:
        return 0.0
    stamp = now if now is not None else time.monotonic()
    with _LOCK:
        entry = _health(endpoint_id, key_fp)
        entry.failures += 1
        entry.last_status = status
        entry.last_error = (message or body or "")[:200]
        entry.last_used = stamp
        cooldown = cooldown_for_status(status, retry_after, body)
        if not cooldown and entry.failures >= _SOFT_FAILURE_COOLDOWN_AFTER:
            cooldown = _SOFT_FAILURE_COOLDOWN
        if cooldown:
            entry.cooldown_until = stamp + cooldown
        logger.info(
            "key pool: endpoint=%s key=%s failed status=%s cooldown=%.0fs streak=%d",
            endpoint_id, key_fp[:8], status, cooldown, entry.failures,
        )
        return cooldown


def health_snapshot(endpoint_id: str) -> Dict[str, KeyHealth]:
    with _LOCK:
        return {
            key_fp: KeyHealth(**vars(entry))
            for (ep, key_fp), entry in _HEALTH.items()
            if ep == endpoint_id
        }


# --------------------------------------------------------------------------- credentials


@dataclass(frozen=True)
class PoolKey:
    """One candidate credential of an endpoint."""

    api_key: str
    label: str
    priority: int
    key_id: str
    persisted: bool  # False for the endpoint's own api_key (the implicit primary)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.api_key)

    @property
    def masked(self) -> str:
        return mask_key(self.api_key)


def _endpoint_primary(endpoint_id: str) -> Optional[str]:
    from core.database import ModelEndpoint, get_db_session

    with get_db_session() as db:
        endpoint = db.query(ModelEndpoint).filter(ModelEndpoint.id == endpoint_id).first()
        return normalize_key(getattr(endpoint, "api_key", None)) if endpoint else None


# Credentials change rarely; the chat path asks on every call. A short TTL
# keeps rotation cheap (no SQL per tool call) and add/remove invalidates it.
_POOL_CACHE: Dict[str, Tuple[float, List["PoolKey"]]] = {}
_POOL_CACHE_TTL = 15.0


def invalidate(endpoint_id: Optional[str] = None) -> None:
    with _LOCK:
        if endpoint_id is None:
            _POOL_CACHE.clear()
            return
        _POOL_CACHE.pop(endpoint_id, None)


def pool_keys(endpoint_id: str) -> List[PoolKey]:
    """Every usable credential for one endpoint, primary first.

    Returns ``[]`` when the endpoint has no key at all (local servers) so callers
    can leave anonymous endpoints exactly as they were.
    """
    if not endpoint_id:
        return []
    now = time.monotonic()
    with _LOCK:
        cached = _POOL_CACHE.get(endpoint_id)
        if cached and cached[0] > now:
            return list(cached[1])
    keys = _load_pool_keys(endpoint_id)
    with _LOCK:
        _POOL_CACHE[endpoint_id] = (now + _POOL_CACHE_TTL, list(keys))
    return keys


def _load_pool_keys(endpoint_id: str) -> List[PoolKey]:
    from core.database import ProviderKey, get_db_session

    keys: List[PoolKey] = []
    primary = _endpoint_primary(endpoint_id)
    if primary:
        # Priority 0 keeps the primary in the same rotation band as pooled
        # keys (list order, not priority, is what makes it "first").
        keys.append(PoolKey(primary, "primary", 0, key_id(primary), False))
    seen = {k.fingerprint for k in keys}
    with get_db_session() as db:
        rows = (
            db.query(ProviderKey)
            .filter(ProviderKey.endpoint_id == endpoint_id)
            .filter(ProviderKey.is_enabled.is_(True))
            .order_by(ProviderKey.priority.asc(), ProviderKey.created_at.asc())
            .all()
        )
        for row in rows:
            value = normalize_key(row.api_key)
            if not value or fingerprint(value) in seen:
                continue
            seen.add(fingerprint(value))
            keys.append(
                PoolKey(
                    value,
                    row.label or "",
                    int(row.priority or 0),
                    row.id,
                    True,
                )
            )
    return keys


def pick_key(
    endpoint_id: str,
    *,
    exclude: Iterable[str] = (),
    now: Optional[float] = None,
) -> Optional[str]:
    """Choose the next credential to use for this endpoint.

    Excluded keys (already tried in this request) are skipped. Cooling keys are
    skipped too; if every key is cooling, the one that recovers soonest is
    returned rather than failing the request outright — a stale cooldown must
    never be the reason a chat cannot start.
    """
    keys = pool_keys(endpoint_id)
    if not keys:
        return None
    stamp = now if now is not None else time.monotonic()
    excluded = {fingerprint(k) for k in exclude if k}
    with _LOCK:
        scored = []
        for key in keys:
            if key.fingerprint in excluded:
                continue
            entry = _health(endpoint_id, key.fingerprint)
            cooling = entry.cooldown_until > stamp
            # (cooling, priority, last-used) — a cooling key only wins when
            # everything is cooling, and then the earliest recovery goes first.
            scored.append((
                (1 if cooling else 0),
                entry.cooldown_until if cooling else 0.0,
                key.priority,
                entry.last_used,
                key,
            ))
        if not scored:
            return None
        scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        chosen = scored[0][4]
        _health(endpoint_id, chosen.fingerprint).last_used = stamp
        return chosen.api_key


def remember_key(endpoint_id: str, api_key: Optional[str]) -> None:
    """Mark a credential as used without judging the outcome."""
    key_fp = fingerprint(api_key)
    if not endpoint_id or not key_fp:
        return
    with _LOCK:
        _health(endpoint_id, key_fp).last_used = time.monotonic()


# --------------------------------------------------------------------------- rotation


def endpoint_for_key(api_key: Optional[str]) -> Optional[str]:
    """Find the endpoint a credential belongs to (pool row or primary key)."""
    key = normalize_key(api_key)
    if not key:
        return None
    key_fp = fingerprint(key)
    from core.database import ModelEndpoint, ProviderKey, get_db_session

    with get_db_session() as db:
        row = (
            db.query(ProviderKey)
            .filter(ProviderKey.key_fingerprint == key_fp)
            .first()
        )
        if row is not None:
            return row.endpoint_id
        # Primary keys: compare fingerprints so a rotated/`enc:` value can never
        # match by accident.
        for endpoint in db.query(ModelEndpoint).all():
            if fingerprint(getattr(endpoint, "api_key", None)) == key_fp:
                return endpoint.id
    return None


def rotate(
    endpoint_id: str,
    failed_key: Optional[str],
    *,
    status: Optional[int] = None,
    retry_after: Optional[float] = None,
    body: Optional[str] = None,
    tried: Sequence[str] = (),
    now: Optional[float] = None,
) -> Optional[str]:
    """Rest the failed key and return the next one, or ``None`` if there is none.

    ``tried`` holds every credential this request already used, so a chain of
    rate limits walks the pool instead of ping-ponging between two keys.
    """
    record_failure(
        endpoint_id, failed_key, status=status, retry_after=retry_after, body=body, now=now,
    )
    attempted = [k for k in list(tried) + [failed_key] if k]
    return pick_key(endpoint_id, exclude=attempted, now=now)


def rotate_headers(
    headers: Optional[Dict[str, str]],
    url: str,
    *,
    status: Optional[int],
    body: Optional[str] = None,
    retry_after: Optional[float] = None,
    tried: Sequence[str] = (),
) -> Optional[Dict[str, str]]:
    """Rotate the credential inside an outgoing header set.

    Returns fresh headers for the same URL/model when another key is available,
    otherwise ``None`` (caller keeps its normal error path). This is the hook
    ``src/llm_core.py`` uses inside its retry loop, so a 429 mid-conversation
    costs one extra request instead of a dead turn.
    """
    if not pool_enabled() or not headers or status is None:
        return None
    if not is_key_scoped_failure(status, body):
        return None
    current = current_key(headers)
    if not current:
        return None
    endpoint_id = endpoint_for_key(current)
    if not endpoint_id:
        return None
    successor = rotate(
        endpoint_id,
        current,
        status=status,
        retry_after=retry_after,
        body=body,
        tried=tried,
    )
    if not successor or successor == current:
        return None
    from src.endpoint_resolver import build_headers

    rotated = dict(headers)
    rotated.pop("Authorization", None)
    rotated.pop("authorization", None)
    rotated.pop("x-api-key", None)
    rotated.pop("api-key", None)
    rotated.update(build_headers(successor, url))
    remember_key(endpoint_id, successor)
    logger.info(
        "key pool: rotated endpoint=%s from=%s to=%s status=%s",
        endpoint_id, fingerprint(current)[:8], fingerprint(successor)[:8], status,
    )
    return rotated


def current_key(headers: Optional[Dict[str, str]]) -> Optional[str]:
    """The credential an outgoing request is actually using."""
    if not headers:
        return None
    lowered = {str(k).lower(): v for k, v in headers.items()}
    bearer = lowered.get("authorization") or ""
    if isinstance(bearer, str) and bearer.lower().startswith("bearer "):
        return normalize_key(bearer[7:])
    for name in ("x-api-key", "api-key"):
        value = lowered.get(name)
        if isinstance(value, str) and value.strip():
            return normalize_key(value)
    return None


# --------------------------------------------------------------------------- management


def add_key(
    endpoint_id: str,
    api_key: str,
    *,
    label: str = "",
    priority: int = 0,
    owner: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist one pooled credential. Idempotent per (endpoint, key)."""
    key = normalize_key(api_key)
    if not key:
        raise ValueError("api_key is required")
    from core.database import ProviderKey, get_db_session

    key_fp = fingerprint(key)
    with get_db_session() as db:
        existing = (
            db.query(ProviderKey)
            .filter(ProviderKey.endpoint_id == endpoint_id)
            .filter(ProviderKey.key_fingerprint == key_fp)
            .first()
        )
        if existing is not None:
            existing.is_enabled = True
            existing.label = label or existing.label
            existing.priority = int(priority)
            row = existing
        else:
            row = ProviderKey(
                id=key_id(key),
                endpoint_id=endpoint_id,
                owner=owner,
                label=label or mask_key(key),
                api_key=key,
                key_fingerprint=key_fp,
                is_enabled=True,
                priority=int(priority),
            )
            db.add(row)
        db.flush()
        invalidate(endpoint_id)
        return {"id": row.id, "label": row.label or "", "masked": mask_key(key)}


def remove_key(key_row_id: str) -> bool:
    from core.database import ProviderKey, get_db_session

    with get_db_session() as db:
        row = db.query(ProviderKey).filter(ProviderKey.id == key_row_id).first()
        if row is None:
            return False
        endpoint_id = row.endpoint_id
        key_fp = row.key_fingerprint
        db.delete(row)
    with _LOCK:
        _HEALTH.pop((endpoint_id, key_fp), None)
    invalidate(endpoint_id)
    return True


def set_enabled(key_row_id: str, enabled: bool) -> bool:
    from core.database import ProviderKey, get_db_session

    with get_db_session() as db:
        row = db.query(ProviderKey).filter(ProviderKey.id == key_row_id).first()
        if row is None:
            return False
        row.is_enabled = bool(enabled)
        if not enabled:
            with _LOCK:
                _HEALTH.pop((row.endpoint_id, row.key_fingerprint), None)
        invalidate(row.endpoint_id)
        return True


def describe_pool(endpoint_id: str) -> Dict[str, Any]:
    """Browser-safe view of a pool: masked keys, health, no ciphertext."""
    keys = pool_keys(endpoint_id)
    snapshot = health_snapshot(endpoint_id)
    now = time.monotonic()
    items = []
    for key in keys:
        entry = snapshot.get(key.fingerprint)
        items.append({
            "id": key.key_id,
            "label": key.label or ("primary" if not key.persisted else ""),
            "masked": key.masked,
            "persisted": key.persisted,
            "priority": None if not key.persisted else key.priority,
            "cooling_down": bool(entry and entry.cooling(now)),
            "cooldown_seconds": (
                max(0, int(entry.cooldown_until - now)) if entry and entry.cooling(now) else 0
            ),
            "failures": entry.failures if entry else 0,
            "successes": entry.successes if entry else 0,
            "last_status": entry.last_status if entry else None,
            "last_error": entry.last_error if entry else "",
        })
    healthy = [i for i in items if not i["cooling_down"]]
    return {
        "endpoint_id": endpoint_id,
        "key_count": len(items),
        "healthy_count": len(healthy),
        "rotation_ready": len(items) > 1,
        "enabled": pool_enabled(),
        "keys": items,
    }
