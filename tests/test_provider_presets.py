"""Provider onboarding: key-prefix guess, model-list parsing and discovery against mocked APIs."""
import httpx
import pytest

from src import provider_presets as pp

KEY = "openrouter-test-token"


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _chat(mid, **kw):
    return {"id": mid, "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}, **kw}


# --------------------------------------------------------------------------- guess
@pytest.mark.parametrize("key,expected", [
    ("sk-or-v1-abc", ["openrouter"]),
    ("sk-ant-api03-abc", ["anthropic"]),
    ("AIzaSyAbc", ["google"]),
    ("gsk_abc", ["groq"]),
    ("xai-abc", ["xai"]),
    ("nvapi-abc", ["nvidia"]),
    ("hf_abc", ["huggingface"]),
    ("csk-abc", ["cerebras"]),
    ("sk-abc", ["openai", "deepseek"]),     # ambiguous on purpose
    ("  sk-or-v1-abc  ", ["openrouter"]),   # whitespace from copy/paste
    ("", []),
    ("abcdef0123456789", []),               # e.g. Mistral/Together have no distinctive prefix
])
def test_guess_provider(key, expected):
    assert pp.guess_provider(key) == expected


def test_presets_are_well_formed():
    ids = [p.id for p in pp.PRESETS]
    assert len(ids) == len(set(ids))
    for p in pp.PRESETS:
        if p.id != "custom":
            assert p.base_url.startswith(("https://", "http://localhost")), p.id
        if p.local:
            assert not p.needs_key
    assert pp.get_preset("OpenRouter").id == "openrouter"
    assert pp.get_preset("nope") is None
    for item in pp.public_presets():  # presets are public data: prefixes only, never a stored key
        assert "api_key" not in item
        assert all(len(prefix) <= 8 for prefix in item["key_prefixes"])


# --------------------------------------------------------------------------- parsers
def test_parse_openrouter_flags_free_vision_tools_reasoning():
    data = {"data": [
        _chat("meta/llama:free", name="Llama", context_length=131072,
              pricing={"prompt": "0", "completion": "0"}, supported_parameters=["tools"]),
        {**_chat("openai/gpt-x", name="GPT X", context_length=400000, pricing={"prompt": "0.000001", "completion": "0.00001"},
                 supported_parameters=["tools", "include_reasoning"]),
         "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]}},
        _chat("vendor/zero", pricing={"prompt": "0", "completion": "0"}),
        _chat("vendor/half-free", pricing={"prompt": "0", "completion": "0.000002"}),
        _chat("vendor/partial-price", pricing={"prompt": "0"}),
        {"id": "vendor/no-pricing"},
        {"id": "img/only", "architecture": {"output_modalities": ["image"]}},
        "junk", {"name": "no id"},
    ]}
    cards = {c.id: c for c in pp.parse_openrouter(data)}
    assert set(cards) == {"meta/llama:free", "openai/gpt-x", "vendor/zero", "vendor/half-free", "vendor/partial-price", "vendor/no-pricing"}
    assert cards["meta/llama:free"].free is True and cards["meta/llama:free"].tools is True
    assert cards["meta/llama:free"].context_length == 131072
    assert cards["openai/gpt-x"].free is False and cards["openai/gpt-x"].vision is True
    assert cards["openai/gpt-x"].reasoning is True
    assert cards["vendor/zero"].free is True          # zero price without the :free suffix
    assert cards["vendor/half-free"].free is False     # only one side is free
    assert cards["vendor/partial-price"].free is None  # incomplete pricing stays unknown
    assert cards["vendor/no-pricing"].free is None     # unknown, not guessed


def test_parse_google_keeps_only_generate_content_models():
    data = {"models": [
        {"name": "models/gemini-2.5-flash", "displayName": "Gemini 2.5 Flash", "inputTokenLimit": 1048576,
         "supportedGenerationMethods": ["generateContent", "countTokens"]},
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/imagen-3", "supportedGenerationMethods": ["generateContent"]},   # name filter
        {"baseModelId": "gemini-2.5-pro", "name": "models/gemini-2.5-pro-001", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/no-methods"},
    ]}
    ids = [c.id for c in pp.parse_google(data)]
    assert ids == ["gemini-2.5-flash", "gemini-2.5-pro"]


def test_parse_openai_style_bare_list_dedupes_and_drops_non_chat():
    data = [{"id": "llama-3"}, {"id": "llama-3"}, {"id": "text-embedding-3-small"}, {"id": "whisper-1"},
            {"id": "rerank-x", "type": "rerank"}, {"id": "qwen", "context_length": 32768}, {"nope": 1}, 5]
    cards = pp.parse_openai_style(data)
    assert [c.id for c in cards] == ["llama-3", "qwen"]
    assert cards[1].context_length == 32768


def test_parse_openai_style_marks_local_cards():
    assert pp.parse_openai_style({"data": [{"id": "qwen3:4b"}]}, local=True)[0].local is True


# --------------------------------------------------------------------------- discovery
async def test_openrouter_checks_key_then_lists_with_pagination():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.path)
        assert req.headers["authorization"] == f"Bearer {KEY}"
        if req.url.path.endswith("/key"):
            return httpx.Response(200, json={"data": {"is_free_tier": True, "label": "sk-or-v1-abc...xyz"}})
        if req.url.params.get("offset") == "1":
            return httpx.Response(200, json={"data": [_chat("b/two:free", pricing={"prompt": "0", "completion": "0"})]})
        return httpx.Response(200, json={"data": [_chat("a/one")], "links": {"next": "/api/v1/models?offset=1"}})

    async with _client(handler) as c:
        found = await pp.discover("openrouter", KEY, client=c)
    assert [m.id for m in found.cards] == ["a/one", "b/two:free"]
    assert found.key_info == {"is_free_tier": True, "label": "sk-or-v1-abc...xyz"}
    assert seen[0].endswith("/key")  # key is validated before the big list is fetched


async def test_openrouter_never_follows_pagination_to_another_host():
    hosts = []

    def handler(req):
        hosts.append(req.url.host)
        if req.url.path.endswith("/key"):
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(200, json={"data": [_chat("a/one")], "links": {"next": "https://evil.example/steal"}})

    async with _client(handler) as c:
        found = await pp.discover("openrouter", KEY, client=c)
    assert [m.id for m in found.cards] == ["a/one"]
    assert set(hosts) == {"openrouter.ai"}


async def test_openrouter_does_not_forward_key_to_same_host_on_another_port():
    assert not pp._same_origin("https://openrouter.ai:0/steal", "https://openrouter.ai/api/v1")
    origins = []

    def handler(req):
        origins.append((req.url.host, req.url.port or 443))
        if req.url.path.endswith("/key"):
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(200, json={"data": [_chat("a/one")], "links": {"next": "https://openrouter.ai:444/steal"}})

    async with _client(handler) as c:
        found = await pp.discover("openrouter", KEY, client=c)
    assert [m.id for m in found.cards] == ["a/one"]
    assert origins == [("openrouter.ai", 443), ("openrouter.ai", 443)]


async def test_openrouter_key_check_ignores_non_object_json():
    def handler(req):
        if req.url.path.endswith("/key"):
            return httpx.Response(200, json=["unexpected"])
        return httpx.Response(200, json={"data": [_chat("a/one")]})

    async with _client(handler) as c:
        found = await pp.discover("openrouter", KEY, client=c)
    assert found.key_info is None and [m.id for m in found.cards] == ["a/one"]


async def test_openrouter_bad_key_fails_fast_and_never_echoes_the_key():
    calls = []

    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(401, json={"error": {"message": f"bad {KEY}"}})

    async with _client(handler) as c:
        with pytest.raises(pp.DiscoveryError) as ei:
            await pp.discover("openrouter", KEY, client=c)
    assert ei.value.status == 401 and KEY not in ei.value.message and "rejected this key" in ei.value.message
    assert len(calls) == 1  # did not go on to download the model list


async def test_openrouter_key_check_outage_is_not_fatal():
    def handler(req):
        if req.url.path.endswith("/key"):
            return httpx.Response(500)
        return httpx.Response(200, json={"data": [_chat("a/one")]})

    async with _client(handler) as c:
        found = await pp.discover("openrouter", KEY, client=c)
    assert found.key_info is None and len(found.cards) == 1


async def test_google_uses_native_list_header_key_and_pages():
    def handler(req):
        assert req.headers["x-goog-api-key"] == "AIzaKEY"
        assert req.url.path == "/v1beta/models"            # /openai suffix stripped for the catalog
        if req.url.params.get("pageToken") == "t2":
            return httpx.Response(200, json={"models": [
                {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]}]})
        return httpx.Response(200, json={"models": [
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]}], "nextPageToken": "t2"})

    async with _client(handler) as c:
        found = await pp.discover("google", "AIzaKEY", client=c)
    assert [m.id for m in found.cards] == ["gemini-2.5-flash", "gemini-2.5-pro"]


async def test_anthropic_headers_and_pagination():
    def handler(req):
        assert req.headers["x-api-key"] == "sk-ant-KEY" and req.headers["anthropic-version"] == "2023-06-01"
        assert req.url.path == "/v1/models"
        if req.url.params.get("after_id") == "m1":
            return httpx.Response(200, json={"data": [{"id": "m2", "display_name": "Two"}], "has_more": False})
        return httpx.Response(200, json={"data": [{"id": "m1", "display_name": "One"}], "has_more": True, "last_id": "m1"})

    async with _client(handler) as c:
        found = await pp.discover("anthropic", "sk-ant-KEY", client=c)
    assert [(m.id, m.name) for m in found.cards] == [("m1", "One"), ("m2", "Two")]


async def test_openai_style_provider_uses_bearer_and_base_path():
    def handler(req):
        assert req.url.host == "api.groq.com" and req.url.path == "/openai/v1/models"
        assert req.headers["authorization"] == "Bearer gsk_KEY"
        return httpx.Response(200, json={"data": [{"id": "llama-3.3-70b-versatile"}, {"id": "whisper-large-v3"}]})

    async with _client(handler) as c:
        cards = await pp.discover_models("groq", "gsk_KEY", client=c)
    assert [m.id for m in cards] == ["llama-3.3-70b-versatile"]


async def test_local_provider_needs_no_key_and_sends_no_auth_header():
    def handler(req):
        assert "authorization" not in req.headers
        assert req.url.port == 11434
        return httpx.Response(200, json={"data": [{"id": "qwen3:4b"}]})

    async with _client(handler) as c:
        found = await pp.discover("ollama", "", client=c)
    assert found.cards[0].local is True


async def test_custom_provider_requires_a_valid_base_url():
    async with _client(lambda r: httpx.Response(200, json={"data": [{"id": "m"}]})) as c:
        with pytest.raises(pp.DiscoveryError, match="base URL is required"):
            await pp.discover("custom", "", "", client=c)
        with pytest.raises(pp.DiscoveryError, match="http"):
            await pp.discover("custom", "", "ftp://x", client=c)
        ok = await pp.discover("custom", "", "http://my-box:8000/v1", client=c)
    assert ok.cards[0].id == "m"


@pytest.mark.parametrize("base", [
    "http://", "http://bad host/v1", "https://[::1", "http://user:secret@host/v1",
    "http://localhost:0/v1", "http://host/v1#fragment",
])
async def test_custom_provider_rejects_malformed_or_credentialed_urls(base):
    with pytest.raises(pp.DiscoveryError):
        await pp.discover("custom", "", base)


@pytest.mark.parametrize("provider,key,msg", [
    ("nope", "k", "Unknown provider"),
    ("openai", "", "Paste your OpenAI API key"),
])
async def test_input_errors(provider, key, msg):
    with pytest.raises(pp.DiscoveryError, match=msg):
        await pp.discover(provider, key)


@pytest.mark.parametrize("status,needle", [(401, "rejected this key"), (403, "firewall/proxy"),
                                           (404, "no model list"), (429, "rate-limiting"), (500, "HTTP 500")])
async def test_http_errors_are_friendly_and_never_leak_the_key(status, needle):
    key = "sk-LEAKTEST-123456"
    async with _client(lambda r: httpx.Response(status, text=f"oops {key}")) as c:
        with pytest.raises(pp.DiscoveryError) as ei:
            await pp.discover("openai", key, client=c)
    assert needle in ei.value.message and key not in ei.value.message and ei.value.status == status


async def test_network_failures_and_garbage_bodies():
    def boom(req):
        raise httpx.ConnectError("refused", request=req)

    def slow(req):
        raise httpx.ReadTimeout("slow", request=req)

    async with _client(boom) as c:
        with pytest.raises(pp.DiscoveryError, match="Could not reach"):
            await pp.discover("openai", "sk-x", client=c)
    async with _client(slow) as c:
        with pytest.raises(pp.DiscoveryError, match="Timed out"):
            await pp.discover("openai", "sk-x", client=c)
    async with _client(lambda r: httpx.Response(200, text="<html>not json</html>")) as c:
        with pytest.raises(pp.DiscoveryError, match="not JSON"):
            await pp.discover("openai", "sk-x", client=c)
    async with _client(lambda r: httpx.Response(200, json={"data": []})) as c:
        with pytest.raises(pp.DiscoveryError, match="no chat models"):
            await pp.discover("openai", "sk-x", client=c)


async def test_redirects_are_not_followed():
    hits = []

    def handler(req):
        hits.append(str(req.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})

    # owns its client -> the module builds one with follow_redirects=False
    import httpx as _h
    orig = _h.AsyncClient
    try:
        _h.AsyncClient = lambda **kw: orig(transport=_h.MockTransport(handler), **kw)
        with pytest.raises(pp.DiscoveryError):
            await pp.discover("openai", "sk-x")
    finally:
        _h.AsyncClient = orig
    assert len(hits) == 1 and "169.254" not in hits[0]
