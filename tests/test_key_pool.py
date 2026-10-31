"""Key pool: rotation policy, cooldowns, header swap and endpoint integration."""
import asyncio
import json

import pytest

from core.database import ModelEndpoint, ProviderKey, engine, get_db_session
from src import key_pool


ENDPOINT_ID = "ep-pool-test"
PRIMARY = "sk-primary-0001"
SECOND = "sk-second-0002"
THIRD = "sk-third-0003"


@pytest.fixture(autouse=True)
def _tables():
    ProviderKey.__table__.create(bind=engine, checkfirst=True)
    ModelEndpoint.__table__.create(bind=engine, checkfirst=True)
    key_pool.reset()
    _cleanup()
    with get_db_session() as db:
        db.add(ModelEndpoint(
            id=ENDPOINT_ID,
            name="Pooled provider",
            base_url="https://api.example.test/v1",
            api_key=PRIMARY,
            is_enabled=True,
        ))
    yield
    key_pool.reset()
    _cleanup()


def _cleanup():
    with get_db_session() as db:
        db.query(ProviderKey).filter(ProviderKey.endpoint_id == ENDPOINT_ID).delete()
        db.query(ModelEndpoint).filter(ModelEndpoint.id == ENDPOINT_ID).delete()


# --------------------------------------------------------------------------- policy


def test_cooldown_is_key_scoped_and_status_aware():
    assert key_pool.cooldown_for_status(401) == key_pool._INVALID_KEY_COOLDOWN
    assert key_pool.cooldown_for_status(402) == key_pool._QUOTA_EXHAUSTED_COOLDOWN
    assert key_pool.cooldown_for_status(429) == key_pool._RATE_LIMIT_COOLDOWN
    # Provider problems must not burn the next key's quota.
    assert key_pool.cooldown_for_status(500) == 0
    assert key_pool.cooldown_for_status(503) == 0
    assert not key_pool.is_key_scoped_failure(500)
    assert key_pool.is_key_scoped_failure(429)
    assert key_pool.is_key_scoped_failure(403, "insufficient_quota")


def test_retry_after_is_honored_and_clamped():
    assert key_pool.cooldown_for_status(429, retry_after=12) == 12
    assert key_pool.cooldown_for_status(429, retry_after=10 ** 9) == key_pool._MAX_COOLDOWN
    assert key_pool.parse_retry_after("30") == 30
    assert key_pool.parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") is None
    assert key_pool.parse_retry_after(None) is None


def test_masking_never_reveals_the_key():
    masked = key_pool.mask_key(SECOND)
    assert SECOND not in masked
    assert masked.startswith("sk-sec") and masked.endswith("0002")
    assert key_pool.mask_key("short") == "s…"
    assert key_pool.mask_key("") == ""


# --------------------------------------------------------------------------- pool membership


def test_primary_key_is_implicitly_first():
    keys = key_pool.pool_keys(ENDPOINT_ID)
    assert [k.api_key for k in keys] == [PRIMARY]
    assert keys[0].persisted is False


def test_added_keys_follow_the_primary_and_duplicates_collapse():
    key_pool.add_key(ENDPOINT_ID, SECOND, label="second")
    key_pool.add_key(ENDPOINT_ID, THIRD)
    key_pool.add_key(ENDPOINT_ID, SECOND, label="second again")  # idempotent
    keys = [k.api_key for k in key_pool.pool_keys(ENDPOINT_ID)]
    assert keys == [PRIMARY, SECOND, THIRD]


def test_pooled_keys_are_encrypted_at_rest():
    from sqlalchemy import text

    key_pool.add_key(ENDPOINT_ID, SECOND, label="second")
    with get_db_session() as db:
        raw = db.execute(text("SELECT api_key FROM provider_keys")).scalar()
    assert raw.startswith("enc:") and SECOND not in raw


# --------------------------------------------------------------------------- selection


def test_selection_round_robins_by_least_recent_use():
    key_pool.add_key(ENDPOINT_ID, SECOND)
    first = key_pool.pick_key(ENDPOINT_ID)
    second = key_pool.pick_key(ENDPOINT_ID)
    assert {first, second} == {PRIMARY, SECOND}
    assert first != second


def test_cooled_key_is_skipped_and_all_cooled_falls_back():
    key_pool.add_key(ENDPOINT_ID, SECOND)
    key_pool.record_failure(ENDPOINT_ID, PRIMARY, status=429)
    assert key_pool.pick_key(ENDPOINT_ID) == SECOND
    # Everything cooling: still return something instead of failing the turn.
    key_pool.record_failure(ENDPOINT_ID, SECOND, status=429)
    assert key_pool.pick_key(ENDPOINT_ID) in {PRIMARY, SECOND}


def test_rotation_walks_the_pool_without_repeating():
    key_pool.add_key(ENDPOINT_ID, SECOND)
    key_pool.add_key(ENDPOINT_ID, THIRD)
    tried = []
    current = PRIMARY
    for _ in range(3):
        nxt = key_pool.rotate(ENDPOINT_ID, current, status=429, tried=tried)
        if nxt is None:
            break
        tried.append(current)
        current = nxt
    assert len(set(tried)) == 2 and len(tried) == 2


def test_success_clears_a_cooldown():
    key_pool.record_failure(ENDPOINT_ID, PRIMARY, status=429)
    assert key_pool.health_snapshot(ENDPOINT_ID)[key_pool.fingerprint(PRIMARY)].cooling()
    key_pool.record_success(ENDPOINT_ID, PRIMARY)
    assert not key_pool.health_snapshot(ENDPOINT_ID)[key_pool.fingerprint(PRIMARY)].cooling()


# --------------------------------------------------------------------------- headers


def test_headers_rotate_from_bearer_to_bearer(monkeypatch):
    key_pool.add_key(ENDPOINT_ID, SECOND)
    headers = {"Authorization": f"Bearer {PRIMARY}", "X-Trace": "1"}
    rotated = key_pool.rotate_headers(
        headers, "https://api.example.test/v1/chat/completions", status=429,
    )
    assert rotated is not None
    assert rotated["Authorization"] == f"Bearer {SECOND}"
    assert rotated["X-Trace"] == "1"  # unrelated headers survive
    assert headers["Authorization"] == f"Bearer {PRIMARY}"  # input untouched


def test_rotate_headers_ignores_provider_wide_failures():
    key_pool.add_key(ENDPOINT_ID, SECOND)
    headers = {"Authorization": f"Bearer {PRIMARY}"}
    assert key_pool.rotate_headers(headers, "https://api.example.test/v1", status=503) is None
    assert key_pool.rotate_headers(headers, "https://api.example.test/v1", status=429) is not None


def test_current_key_reads_both_auth_styles():
    assert key_pool.current_key({"Authorization": "Bearer abc"}) == "abc"
    assert key_pool.current_key({"x-api-key": "def"}) == "def"
    assert key_pool.current_key({}) is None


# --------------------------------------------------------------------------- endpoint integration


def test_resolve_endpoint_runtime_uses_the_pool():
    from src.endpoint_resolver import resolve_endpoint_runtime

    key_pool.add_key(ENDPOINT_ID, SECOND)
    with get_db_session() as db:
        ep = db.query(ModelEndpoint).filter(ModelEndpoint.id == ENDPOINT_ID).first()
        seen = {resolve_endpoint_runtime(ep)[1] for _ in range(4)}
    assert seen == {PRIMARY, SECOND}


def test_resolve_endpoint_runtime_survives_a_broken_pool(monkeypatch):
    from src.endpoint_resolver import resolve_endpoint_runtime

    def boom(endpoint_id):
        raise RuntimeError("no db")

    monkeypatch.setattr(key_pool, "pick_key", boom)
    with get_db_session() as db:
        ep = db.query(ModelEndpoint).filter(ModelEndpoint.id == ENDPOINT_ID).first()
        base, key = resolve_endpoint_runtime(ep)
    assert key == PRIMARY and base.startswith("https://api.example.test")


def test_describe_pool_is_browser_safe():
    key_pool.add_key(ENDPOINT_ID, SECOND, label="backup")
    key_pool.record_failure(ENDPOINT_ID, PRIMARY, status=429)
    described = key_pool.describe_pool(ENDPOINT_ID)
    blob = json.dumps(described)
    assert SECOND not in blob and PRIMARY not in blob
    assert described["key_count"] == 2 and described["rotation_ready"] is True
    assert described["healthy_count"] == 1
    assert [k["masked"] for k in described["keys"]][1] == key_pool.mask_key(SECOND)


# --------------------------------------------------------------------------- streaming hook


def test_stream_error_payload_parses_status():
    from src.llm_core import _stream_error_payload

    chunk = 'event: error\ndata: {"error": "rate limited", "status": 429}\n\n'
    assert _stream_error_payload(chunk) == (429, "rate limited")
    assert _stream_error_payload('data: {"delta": "hi"}\n\n') == (None, "")


def test_stream_retries_on_a_fresh_key_before_any_output(monkeypatch):
    """429 before the first token must be invisible to the user."""
    from src import llm_core

    key_pool.add_key(ENDPOINT_ID, SECOND)
    calls = []

    async def fake_inner(url, model, messages, **kwargs):
        calls.append(kwargs.get("headers", {}).get("Authorization"))
        if len(calls) == 1:
            yield 'event: error\ndata: {"error": "quota", "status": 429}\n\n'
            return
        yield 'data: {"delta": "hello"}\n\n'
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(llm_core, "_stream_llm_inner", fake_inner)
    monkeypatch.setattr(llm_core, "_stream_target_url", lambda url: url)

    async def run():
        chunks = []
        async for chunk in llm_core.stream_llm(
            "https://api.example.test/v1",
            "model-x",
            [{"role": "user", "content": "hi"}],
            headers={"Authorization": f"Bearer {PRIMARY}"},
        ):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(run())
    assert calls == [f"Bearer {PRIMARY}", f"Bearer {SECOND}"]
    assert any('"delta": "hello"' in c for c in chunks)
    assert not any(c.startswith("event: error") for c in chunks)


def test_stream_does_not_hide_an_error_after_output(monkeypatch):
    """A mid-stream failure is reported, never silently re-tried."""
    from src import llm_core

    key_pool.add_key(ENDPOINT_ID, SECOND)
    calls = []

    async def fake_inner(url, model, messages, **kwargs):
        calls.append(1)
        yield 'data: {"delta": "partial"}\n\n'
        yield 'event: error\ndata: {"error": "rate limited", "status": 429}\n\n'

    monkeypatch.setattr(llm_core, "_stream_llm_inner", fake_inner)
    monkeypatch.setattr(llm_core, "_stream_target_url", lambda url: url)

    async def run():
        return [c async for c in llm_core.stream_llm(
            "https://api.example.test/v1", "model-x",
            [{"role": "user", "content": "hi"}],
            headers={"Authorization": f"Bearer {PRIMARY}"},
        )]

    chunks = asyncio.run(run())
    assert len(calls) == 1
    assert any(c.startswith("event: error") for c in chunks)
