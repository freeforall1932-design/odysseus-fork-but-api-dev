"""Chatbox AI license + catalog client (HTTP mocked, no network, no real key)."""
import json

import httpx
import pytest

from src import chatbox_ai as cb

LICENSE = "cbx-test-license-key-0123456789"
DETAIL = {
    "name": "Chatbox AI Pro",
    "plan": "pro",
    "status": "active",
    "expires_at": "2027-01-31T00:00:00Z",
    "unified_token_usage": 12_300,
    "unified_token_limit": 50_000,
    "remaining_quota_unified": 37_700,
    "remaining_quota_35": 10,
    "remaining_quota_4": 20,
    "remaining_quota_image": 34,
    "image_used_count": 6,
    "image_total_quota": 40,
    "expansion_pack_limit": 5_000,
    "expansion_pack_usage": 1_000,
    "key": LICENSE,
}


def _catalog():
    return {
        "success": True,
        "data": {
            "provider": {"id": "chatboxai", "name": "Chatbox AI"},
            "license": {"plan": "pro"},
            "groups": [
                {"id": "flagship", "modelIds": ["gpt-5.2", "claude-sonnet-4.5"], "featuredModelIds": ["claude-sonnet-4.5"]},
                {"id": "fast", "modelIds": ["gemini-2.5-flash", "o4-mini"]},
            ],
            "models": {
                "gpt-5.2": {"modelName": "GPT-5.2", "apiStyle": "openai", "contextWindow": 200000,
                            "capabilities": ["tool_use", "vision"]},
                "claude-sonnet-4.5": {"modelName": "Claude Sonnet 4.5", "apiStyle": "anthropic",
                                       "contextWindow": 200000, "capabilities": ["tool_use", "reasoning"]},
                "gemini-2.5-flash": {"modelName": "Gemini 2.5 Flash", "apiStyle": "google", "contextWindow": 1000000},
                "o4-mini": {"modelName": "o4-mini"},  # no apiStyle: prefix fallback -> openai
                "text-embedding-3": {"modelName": "Embedding", "type": "embedding"},
                "dall-e-image": {"modelName": "Image", "type": "image"},
                "gpt-5-codex": {"modelName": "Codex", "apiStyle": "openai-responses"},
            },
            "imageModels": [],
        },
    }


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5)


def _detail(payload=None, status=200):
    return httpx.Response(status, json=payload if payload is not None else {"data": DETAIL})


# --------------------------------------------------------------------------- origins / styles
def test_origin_override_and_validation(monkeypatch):
    monkeypatch.delenv(cb._ORIGIN_ENV, raising=False)
    assert cb.api_origin() == cb.DEFAULT_API_ORIGIN
    monkeypatch.setenv(cb._ORIGIN_ENV, "https://chatbox.example.com/")
    assert cb.api_origin() == "https://chatbox.example.com"
    monkeypatch.setenv(cb._ORIGIN_ENV, "https://user:pass@evil.example")
    assert cb.api_origin() == cb.DEFAULT_API_ORIGIN
    monkeypatch.setenv(cb._ORIGIN_ENV, "file:///etc/passwd")
    assert cb.api_origin() == cb.DEFAULT_API_ORIGIN


def test_is_chatbox_url_is_host_exact():
    assert cb.is_chatbox_url("https://api.chatboxai.app/gateway/openai/v1")
    assert cb.is_chatbox_url("https://chatboxai.app/api/license/detail")
    assert cb.is_chatbox_url("https://api.ai-chatbox.com/gateway/anthropic/v1")
    assert not cb.is_chatbox_url("https://api.chatboxai.app.evil.example/gateway/openai/v1")
    assert not cb.is_chatbox_url("https://evil.example/https://api.chatboxai.app")
    assert not cb.is_chatbox_url("ftp://api.chatboxai.app/gateway")
    assert not cb.is_chatbox_url("")


def test_gateway_paths_and_style_inference():
    assert cb.gateway_base("openai") == "https://api.chatboxai.app/gateway/openai/v1"
    assert cb.gateway_base("anthropic") == "https://api.chatboxai.app/gateway/anthropic/v1"
    assert cb.gateway_base("nope") == ""
    assert cb.infer_api_style("claude-sonnet-4.5") == "anthropic"
    assert cb.infer_api_style("gemini-2.5-flash") == "google"
    assert cb.infer_api_style("gpt-5.2") == "openai"
    assert cb.infer_api_style("claude-sonnet-4.5", "openai") == "openai"  # declared wins
    assert cb.model_supported("openai") and cb.model_supported("anthropic")
    assert not cb.model_supported("google") and not cb.model_supported("openai-responses")


def test_key_helpers_never_reveal_the_key():
    masked = cb.mask_key(LICENSE)
    assert masked.startswith("cbx-") and masked.endswith("6789")
    assert LICENSE not in masked
    short = cb.mask_key("abcd")
    assert len(short) == 4 and short.startswith("ab") and "cd" not in short


# --------------------------------------------------------------------------- discovery
@pytest.mark.asyncio
async def test_discover_activates_lists_and_groups(monkeypatch):
    monkeypatch.delenv(cb._ORIGIN_ENV, raising=False)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.headers.get("authorization")))
        if request.url.path == "/api/license/activate":
            body = json.loads(request.content)
            assert body["licenseKey"] == LICENSE
            assert body["instanceName"] == "Odysseus"
            return httpx.Response(200, json={"data": {"valid": True, "instanceId": "inst-1"}})
        if request.url.path == "/api/license/detail/realtime":
            assert request.headers["authorization"] == LICENSE
            return _detail()
        if request.url.path == "/api/chatbox_ai/model_list":
            body = json.loads(request.content)
            assert body["licenseKey"] == LICENSE
            return httpx.Response(200, json=_catalog())
        raise AssertionError(f"unexpected {request.url}")

    async with _client(handler) as client:
        found = await cb.discover(LICENSE, client=client)

    assert found["instance_id"] == "inst-1"
    assert found["license_detail"]["plan"] == "pro"
    assert found["catalog_source"] == "model_list"
    assert found["masked_key"] == cb.mask_key(LICENSE)
    assert LICENSE not in json.dumps(found)

    models = {m["id"]: m for m in found["models"]}
    assert list(models) == ["claude-sonnet-4.5", "gpt-5.2", "gemini-2.5-flash", "o4-mini", "gpt-5-codex"]
    assert models["claude-sonnet-4.5"]["api_style"] == "anthropic"
    assert models["claude-sonnet-4.5"]["supported"] is True
    assert models["gemini-2.5-flash"]["supported"] is False
    assert models["o4-mini"]["api_style"] == "openai"
    assert models["gpt-5-codex"]["supported"] is False
    assert models["gpt-5.2"]["context_length"] == 200000
    assert models["gpt-5.2"]["tools"] is True and models["gpt-5.2"]["vision"] is True

    variants = {v["api_style"]: v for v in found["variants"]}
    assert variants["openai"]["base_url"] == "https://api.chatboxai.app/gateway/openai/v1"
    assert variants["anthropic"]["base_url"] == "https://api.chatboxai.app/gateway/anthropic/v1"
    assert variants["anthropic"]["model_ids"] == ["claude-sonnet-4.5"]
    assert variants["openai"]["model_ids"] == ["gpt-5.2", "o4-mini"]
    unsupported = {u["api_style"]: u["model_ids"] for u in found["unsupported"]}
    assert unsupported == {"google": ["gemini-2.5-flash"], "openai-responses": ["gpt-5-codex"]}
    assert seen[0] == ("POST", "/api/license/activate", None)
    assert seen[1][2] == LICENSE  # detail uses Authorization: <licenseKey>


@pytest.mark.asyncio
async def test_discover_falls_back_to_manifest():
    def handler(request):
        if request.url.path.endswith("/activate"):
            return httpx.Response(200, json={"data": {"valid": True, "instanceId": "i"}})
        if request.url.path.endswith("/detail/realtime"):
            return _detail()
        if request.url.path == "/api/chatbox_ai/model_list":
            return httpx.Response(404, json={"error": {"code": "gone"}})
        if request.url.path == "/api/model_manifest":
            body = json.loads(request.content)
            assert body["aiProvider"] == "ChatboxAI"
            return httpx.Response(200, json={"data": {"groupName": "Chatbox AI", "models": [
                {"modelId": "gpt-4.1", "modelName": "GPT-4.1", "apiStyle": "openai"},
            ]}})
        raise AssertionError(request.url)

    async with _client(handler) as client:
        found = await cb.discover(LICENSE, client=client)
    assert found["catalog_source"] == "model_manifest"
    assert [m["id"] for m in found["models"]] == ["gpt-4.1"]


@pytest.mark.asyncio
async def test_discover_rejects_an_invalid_license_without_echoing_it():
    def handler(request):
        if request.url.path.endswith("/activate"):
            return httpx.Response(200, json={"data": {"valid": False, "error": "not found"}})
        raise AssertionError("must not continue after a rejected license")

    async with _client(handler) as client:
        with pytest.raises(cb.ChatboxError) as err:
            await cb.discover(LICENSE, client=client)
    assert "rejected" in str(err.value).lower()
    assert LICENSE not in str(err.value)


@pytest.mark.asyncio
async def test_detail_auth_error_is_returned_not_raised():
    def handler(request):
        return httpx.Response(401, json={"error": {"code": "invalid_license", "message": "License not found"}})

    async with _client(handler) as client:
        detail, error = await cb.license_detail(client, LICENSE)
    assert detail is None
    assert error == {"code": "invalid_license", "message": "License not found"}


@pytest.mark.asyncio
async def test_detail_server_error_raises_so_cached_summary_survives():
    async with _client(lambda request: httpx.Response(503, text="down")) as client:
        with pytest.raises(cb.ChatboxError):
            await cb.license_detail(client, LICENSE)


@pytest.mark.asyncio
async def test_empty_catalog_raises_instead_of_connecting_nothing():
    def handler(request):
        if request.url.path.endswith("/activate"):
            return httpx.Response(200, json={"data": {"valid": True, "instanceId": "i"}})
        if request.url.path.endswith("/detail/realtime"):
            return _detail()
        if request.url.path == "/api/chatbox_ai/model_list":
            return httpx.Response(200, json={"data": {"models": {}, "groups": []}})
        if request.url.path == "/api/model_manifest":
            return httpx.Response(200, json={"data": {"models": []}})
        raise AssertionError(request.url)

    async with _client(handler) as client:
        with pytest.raises(cb.ChatboxError) as err:
            await cb.discover(LICENSE, client=client)
    assert "no chat models" in str(err.value).lower()


# --------------------------------------------------------------------------- summary / headers
def test_summarize_detail_hides_key_and_computes_quota():
    summary = cb.summarize_detail(DETAIL)
    assert summary["plan"] == "pro"
    assert summary["expires_at"].startswith("2027-01-31")
    assert summary["quotas"]["unified_used"] == 12_300
    assert summary["quotas"]["unified_limit"] == 50_000
    assert summary["quotas"]["remaining_images"] == 34
    assert summary["quotas"]["expansion_pack_remaining"] == 4_000
    assert "key" not in summary
    assert LICENSE not in json.dumps(summary)
    assert cb.summarize_detail(None) == {}


def test_auth_headers_only_for_chatbox(monkeypatch):
    monkeypatch.setattr(cb, "instance_id_for_key", lambda key: "inst-9" if key == LICENSE else "")
    assert cb.auth_headers(LICENSE, "https://api.chatboxai.app/gateway/openai/v1") == {"Instance-Id": "inst-9"}
    assert cb.auth_headers(LICENSE, "https://api.chatboxai.app/gateway/anthropic/v1") == {"Instance-Id": "inst-9"}
    assert cb.auth_headers(LICENSE, "https://api.openai.com/v1") == {}
    assert cb.auth_headers("", "https://api.chatboxai.app/gateway/openai/v1") == {}
    assert cb.auth_headers("other-key", "https://api.chatboxai.app/gateway/openai/v1") == {}
