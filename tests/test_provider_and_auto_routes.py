"""HTTP layer for provider onboarding, the Auto pool/router and the council runner (all collaborators mocked)."""
import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import routes.auto_routes as auto_routes
import routes.provider_routes as provider_routes
from src import provider_presets as pp


# --------------------------------------------------------------------------- provider routes
@pytest.fixture
def prov(monkeypatch):
    state = {"calls": [], "result": None, "error": None, "admin": True}

    def fake_admin(request):
        if not state["admin"]:
            raise HTTPException(403, "Admin only")

    async def fake_discover(preset_id, api_key="", base_url="", **kw):
        state["calls"].append((preset_id, api_key, base_url))
        if state["error"]:
            raise state["error"]
        return state["result"]

    monkeypatch.setattr(provider_routes, "require_admin", fake_admin)
    monkeypatch.setattr(pp, "discover", fake_discover)
    state["result"] = pp.Discovery(
        cards=[pp.ModelCard("a/free:free", free=True), pp.ModelCard("b/paid", free=False), pp.ModelCard("c/unknown")],
        key_info={"is_free_tier": True, "label": "sk-or-v1-abc...xyz"})
    app = FastAPI()
    app.include_router(provider_routes.setup_provider_routes())
    return state, TestClient(app)


def test_presets_and_guess(prov):
    _state, c = prov
    presets = c.get("/api/providers/presets").json()["presets"]
    assert {"openrouter", "google", "ollama", "custom"} <= {p["id"] for p in presets}
    assert c.post("/api/providers/guess", json={"api_key": "sk-or-v1-x"}).json() == {"candidates": ["openrouter"]}
    assert c.post("/api/providers/guess", json={"api_key": ""}).json() == {"candidates": []}


def test_models_returns_cards_counts_and_key_info(prov):
    state, c = prov
    r = c.post("/api/providers/models", json={"provider": "openrouter", "api_key": "sk-or-v1-x"})
    body = r.json()
    assert r.status_code == 200 and body["count"] == 3 and body["free_count"] == 1
    assert body["key_info"]["is_free_tier"] is True and body["models"][0]["id"] == "a/free:free"
    assert state["calls"] == [("openrouter", "sk-or-v1-x", "https://openrouter.ai/api/v1")]
    assert "sk-or-v1-x" not in r.text            # the key is never echoed back


def test_a_cloud_provider_address_cannot_be_overridden(prov):
    state, c = prov
    r = c.post("/api/providers/models", json={"provider": "openai", "api_key": "sk-x", "base_url": "https://evil.example/v1"})
    assert r.status_code == 400 and "fixed" in r.json()["detail"] and not state["calls"]


def test_custom_provider_uses_the_typed_address(prov):
    state, c = prov
    r = c.post("/api/providers/models", json={"provider": "custom", "base_url": "http://box:8000/v1"})
    assert r.status_code == 200 and state["calls"] == [("custom", "", "http://box:8000/v1")]
    assert r.json()["local"] is False


def test_local_provider_goes_through_the_docker_loopback_rewrite(prov, monkeypatch):
    import routes.model_routes as model_routes
    monkeypatch.setattr(model_routes, "_rewrite_loopback_for_docker", lambda url, **kw: url.replace("localhost", "host.docker.internal"))
    state, c = prov
    assert c.post("/api/providers/models", json={"provider": "ollama"}).status_code == 200
    assert state["calls"][0][2] == "http://host.docker.internal:11434/v1"


def test_custom_loopback_url_uses_docker_host_rewrite_too(prov, monkeypatch):
    import routes.model_routes as model_routes
    monkeypatch.setattr(model_routes, "_rewrite_loopback_for_docker", lambda url, **kw: url.replace("localhost", "host.docker.internal"))
    state, c = prov
    r = c.post("/api/providers/models", json={"provider": "custom", "base_url": "http://localhost:9000/v1"})
    assert r.status_code == 200
    assert state["calls"][0][2] == "http://host.docker.internal:9000/v1"
    assert r.json()["local"] is True and r.json()["models"][0]["local"] is True


def test_local_preset_override_is_classified_from_the_actual_address(prov):
    state, c = prov
    r = c.post("/api/providers/models", json={"provider": "ollama", "base_url": "https://api.example.com/v1"})
    assert r.status_code == 200 and state["calls"][0][2] == "https://api.example.com/v1"
    assert r.json()["local"] is False and r.json()["models"][0]["local"] is False


@pytest.mark.parametrize("err,status", [
    (pp.DiscoveryError("OpenRouter rejected this key (HTTP 401).", 401), 400),   # never relay 401/403 to the browser
    (pp.DiscoveryError("rejected (HTTP 403).", 403), 400),
    (pp.DiscoveryError("no model list (HTTP 404).", 404), 400),
    (pp.DiscoveryError("rate-limiting (HTTP 429).", 429), 429),
    (pp.DiscoveryError("Could not reach api.x.com: ConnectError."), 502),
    (pp.DiscoveryError("Timed out reaching api.x.com."), 502),
    (pp.DiscoveryError("Paste your OpenAI API key first."), 400),
    (pp.DiscoveryError("Unknown provider 'zzz'."), 400),
    (pp.DiscoveryError("The base URL must start with http:// or https://"), 400),
])
def test_discovery_errors_map_to_safe_status_codes(prov, err, status):
    state, c = prov
    state["error"] = err
    r = c.post("/api/providers/models", json={"provider": "openai", "api_key": "sk-x"})
    assert r.status_code == status and r.json()["detail"] == err.message


def test_unknown_provider_and_non_admin(prov):
    state, c = prov
    assert c.post("/api/providers/models", json={"provider": "nope"}).status_code == 400
    state["admin"] = False
    for method, path, body in [("get", "/api/providers/presets", None), ("post", "/api/providers/guess", {"api_key": "x"}),
                               ("post", "/api/providers/models", {"provider": "openai", "api_key": "k"})]:
        r = getattr(c, method)(path, **({"json": body} if body else {}))
        assert r.status_code == 403


# --------------------------------------------------------------------------- auto / council routes
class FakeSkills:
    def read_skill_md(self, name, owner=None):
        return "---\nname: caveman-be-brief\ndescription: be brief\n---\nBE-BRIEF-BODY\nsecond line" if name == "caveman-be-brief" else None


@pytest.fixture
def env(monkeypatch):
    state = {
        "prefs": {},
        "index": {"or": {"name": "OpenRouter", "local": False}, "loc": {"name": "Ollama", "local": True}},
        "llm": [], "replies": {},
    }

    class Prefs:
        @staticmethod
        def _load_for_user(user):
            return json.loads(json.dumps(state["prefs"]))

        @staticmethod
        def _save_for_user(user, prefs):
            state["prefs"] = json.loads(json.dumps(prefs))

    def fake_resolve(ep_id, model, owner=None, require_exact_model=False):
        return (f"http://{ep_id}.test/v1/chat/completions", model, {"X": "1"}) if ep_id in state["index"] and model else None

    async def fake_llm(url, model, messages, **kw):
        state["llm"].append({"url": url, "model": model, "messages": messages, **kw})
        reply = state["replies"].get(model, f"reply from {model}")
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(auto_routes, "_prefs", lambda: Prefs)
    monkeypatch.setattr(auto_routes, "_endpoint_index", lambda owner: state["index"])
    monkeypatch.setattr(auto_routes, "require_api_token_scope", lambda request, scope: "tester")
    monkeypatch.setattr(auto_routes, "resolve_endpoint_by_id", fake_resolve)
    monkeypatch.setattr(auto_routes, "llm_call_async", fake_llm)
    app = FastAPI()
    app.include_router(auto_routes.setup_auto_routes(skills_manager=FakeSkills()))
    return state, TestClient(app)


POOL = [
    {"endpoint_id": "or", "model": "meta/llama:free", "label": "Llama Free", "tags": ["General", " code "], "free": True, "context_length": 131072},
    {"endpoint_id": "or", "model": "qwen/coder:free", "label": "Qwen Coder", "free": True, "vision": False},
    {"endpoint_id": "loc", "model": "qwen3:4b", "label": "Qwen3 4B local", "context_length": 8192},
]


def save_pool(c, pool=None, **settings):
    return c.put("/api/auto/pool", json={"pool": POOL if pool is None else pool, "settings": settings})


def sse(resp):
    events, done = [], False
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            payload = line[6:]
            if payload == "[DONE]":
                done = True
            else:
                events.append(json.loads(payload))
    return events, done


def test_provider_and_auto_routers_register_all_endpoints_together():
    # Exercise the same two-router wiring used in app.py and catch accidental route omissions or duplicates.
    app = FastAPI()
    app.include_router(provider_routes.setup_provider_routes())
    app.include_router(auto_routes.setup_auto_routes(skills_manager=None))
    paths = app.openapi()["paths"]
    got = {(method.upper(), path) for path, ops in paths.items() for method in ops}
    expected = {
        ("GET", "/api/providers/presets"), ("POST", "/api/providers/guess"), ("POST", "/api/providers/models"),
        ("GET", "/api/auto/pool"), ("PUT", "/api/auto/pool"), ("POST", "/api/auto/route"),
        ("POST", "/api/council/plan"), ("POST", "/api/council/run"),
    }
    assert expected <= got, expected - got


# ---- pool storage ---------------------------------------------------------------------------------
def test_pool_round_trip_cleans_input_and_recomputes_local_server_side(env):
    state, c = env
    dirty = POOL + [
        {"endpoint_id": "ghost", "model": "x"},                     # endpoint doesn't exist
        {"endpoint_id": "or", "model": "meta/llama:free"},          # duplicate
        {"endpoint_id": "", "model": "x"}, {"endpoint_id": "a::b", "model": "m"},
    ]
    dirty[0] = {**dirty[0], "local": True}                           # a cloud model claiming to be local
    r = save_pool(c, dirty, router_ref="loc::qwen3:4b", default_ref="ghost::m", keep_local_default=1)
    assert r.status_code == 200 and r.json()["saved"] == 3 and r.json()["dropped"] == 4
    assert r.json()["settings"]["router_ref"] == "loc::qwen3:4b"
    assert r.json()["settings"]["default_ref"] == ""                 # points at an unknown endpoint -> cleared
    got = c.get("/api/auto/pool").json()
    by_model = {e["model"]: e for e in got["pool"]}
    assert by_model["meta/llama:free"]["local"] is False             # server truth, not the client's claim
    assert by_model["qwen3:4b"]["local"] is True
    assert by_model["meta/llama:free"]["tags"] == ["general", "code"]
    assert got["settings"]["keep_local_default"] is True
    assert {e["id"] for e in got["endpoints"]} == {"or", "loc"}


def test_malformed_pool_bodies_are_rejected_outright(env):
    _state, c = env
    assert c.put("/api/auto/pool", json={"pool": ["junk"], "settings": {}}).status_code == 422
    assert c.put("/api/auto/pool", json={"pool": [POOL[0]] * (auto_routes.MAX_POOL + 1), "settings": {}}).status_code == 422


def test_malformed_pool_metadata_is_sanitized_and_string_false_stays_false(env):
    _state, c = env
    entry = {**POOL[0], "tags": 7, "context_length": "unknown"}
    assert save_pool(c, [entry], keep_local_default="false").status_code == 200
    saved = c.get("/api/auto/pool").json()
    assert saved["pool"][0]["tags"] == [] and saved["pool"][0]["context_length"] is None
    assert saved["settings"]["keep_local_default"] is False


def test_removed_endpoints_show_as_unavailable_and_are_not_routed(env):
    state, c = env
    save_pool(c)
    del state["index"]["loc"]
    pool = c.get("/api/auto/pool").json()["pool"]
    assert [e["available"] for e in pool] == [True, True, False]
    r = c.post("/api/auto/route", json={"message": "hi"})
    assert r.status_code == 200 and r.json()["endpoint_id"] == "or"


# ---- routing --------------------------------------------------------------------------------------
def test_route_uses_the_router_model_and_returns_a_decision(env):
    state, c = env
    save_pool(c, router_ref="or::meta/llama:free")
    state["replies"]["meta/llama:free"] = '{"pick": 2, "reason": "code task"}'
    r = c.post("/api/auto/route", json={"message": "write a python function"})
    body = r.json()
    assert r.status_code == 200 and body["model"] == "qwen/coder:free" and body["source"] == "router" and body["reason"] == "code task"
    call = state["llm"][0]
    assert call["model"] == "meta/llama:free" and call["timeout"] == 15 and call["max_retries"] == 1
    assert call["temperature"] == 0.0 and "write a python function" in call["messages"][1]["content"]


def test_route_forwards_image_and_tool_capability_hints_to_router(env):
    state, c = env
    save_pool(c, router_ref="or::meta/llama:free")
    state["replies"]["meta/llama:free"] = '{"pick": 1}'
    r = c.post("/api/auto/route", json={"message": "describe this and edit the file", "has_image": True, "needs_tools": True})
    assert r.status_code == 200
    prompt = state["llm"][0]["messages"][1]["content"]
    assert "Task flags: has an image, needs tools" in prompt


def test_route_without_a_router_uses_pool_order_and_never_calls_a_model(env):
    state, c = env
    save_pool(c)
    body = c.post("/api/auto/route", json={"message": "hi"}).json()
    assert body["source"] == "fallback" and body["model"] == "meta/llama:free" and not state["llm"]


def test_router_failure_degrades_to_the_default_model(env):
    state, c = env
    save_pool(c, router_ref="or::meta/llama:free", default_ref="or::qwen/coder:free")
    state["replies"]["meta/llama:free"] = RuntimeError("429")
    body = c.post("/api/auto/route", json={"message": "hi"}).json()
    assert body["source"] == "fallback" and body["model"] == "qwen/coder:free"
    assert any("router unavailable" in n for n in body["notes"])


def test_keep_local_never_sends_the_message_to_a_cloud_router(env):
    state, c = env
    save_pool(c, router_ref="or::meta/llama:free")                   # a CLOUD router
    r = c.post("/api/auto/route", json={"message": "my private notes", "keep_local": True})
    body = r.json()
    assert r.status_code == 200 and body["model"] == "qwen3:4b" and body["local"] is True
    assert any("router skipped" in n for n in body["notes"])
    assert state["llm"] == []                                        # nothing left the machine


def test_keep_local_may_use_a_local_router_and_only_sees_local_candidates(env):
    state, c = env
    pool = POOL + [{"endpoint_id": "loc", "model": "phi4-mini", "label": "Phi4 Mini"}]
    save_pool(c, pool, router_ref="loc::qwen3:4b")
    state["replies"]["qwen3:4b"] = '{"pick": 2, "reason": "tiny task"}'
    body = c.post("/api/auto/route", json={"message": "summarise this", "keep_local": True}).json()
    assert body["model"] == "phi4-mini" and body["source"] == "router"
    prompt = state["llm"][0]["messages"][1]["content"]
    assert "Llama Free" not in prompt and "Qwen Coder" not in prompt
    assert state["llm"][0]["url"].startswith("http://loc.test")


def test_saved_keep_local_default_applies_unless_the_request_overrides_it(env):
    state, c = env
    save_pool(c, keep_local_default=True)
    assert c.post("/api/auto/route", json={"message": "hi"}).json()["local"] is True
    assert c.post("/api/auto/route", json={"message": "hi", "keep_local": False}).json()["local"] is False


def test_keep_local_without_any_local_model_is_a_409_not_a_silent_cloud_fallback(env):
    state, c = env
    save_pool(c, [p for p in POOL if p["endpoint_id"] == "or"])
    r = c.post("/api/auto/route", json={"message": "hi", "keep_local": True})
    assert r.status_code == 409 and "no offline model" in r.json()["detail"]


def test_exclude_supports_a_try_another_model_button(env):
    state, c = env
    save_pool(c)
    first = c.post("/api/auto/route", json={"message": "hi"}).json()
    tried = [f"{first['endpoint_id']}::{first['model']}"]
    second = c.post("/api/auto/route", json={"message": "hi", "exclude": tried}).json()
    assert second["model"] != first["model"]
    allrefs = tried + [r for r in second["candidates"]]
    r = c.post("/api/auto/route", json={"message": "hi", "exclude": allrefs})
    assert r.status_code == 409 and "No other model" in r.json()["detail"]


def test_empty_pool_is_a_409(env):
    _state, c = env
    assert c.post("/api/auto/route", json={"message": "hi"}).status_code == 409


# ---- council --------------------------------------------------------------------------------------
def members():
    return [{"ref": "or::meta/llama:free", "persona": "researcher"}, {"ref": "or::qwen/coder:free", "persona": "logician"},
            {"ref": "loc::qwen3:4b", "persona": "contrarian"}]


def test_council_plan(env):
    _state, c = env
    assert c.post("/api/council/plan", json={"mode": "debate", "members": 4, "rounds": 2}).json()["calls"] == 9
    assert c.post("/api/council/plan", json={"mode": "vote"}).status_code == 400
    assert c.post("/api/council/plan", json={"members": 99}).status_code == 422


def test_council_run_streams_events_and_calls_every_model(env):
    state, c = env
    r = c.post("/api/council/run", json={"question": "Is 7 prime?", "members": members(), "chair": "or::meta/llama:free", "mode": "debate", "rounds": 2})
    events, done = sse(r)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream") and done
    kinds = [e["type"] for e in events]
    assert kinds[0] == "start" and kinds[-1] == "done" and "chair" in kinds and kinds.count("member") == 6
    assert len(state["llm"]) == 7                                    # 3 members x 2 rounds + chair
    assert all(call["workload"] == "foreground" and call["max_retries"] == 2 for call in state["llm"])
    assert events[-1]["calls"] == 7 and events[-1]["answered"] == 3


def test_council_run_injects_a_skill_without_its_frontmatter(env):
    state, c = env
    r = c.post("/api/council/run", json={"question": "Q", "members": members()[:2], "chair": "or::meta/llama:free",
                                         "mode": "fanout", "skill": "caveman-be-brief"})
    assert r.status_code == 200
    chair_call = state["llm"][-1]
    system = chair_call["messages"][0]["content"]
    assert "BE-BRIEF-BODY" in system and "description: be brief" not in system and "name: caveman" not in system
    assert all("BE-BRIEF-BODY" not in call["messages"][0]["content"] for call in state["llm"][:-1])   # chair-only by default


def test_council_verify_mode_with_a_local_worker(env):
    state, c = env
    state["replies"]["qwen3:4b"] = "LOCAL DRAFT"
    r = c.post("/api/council/run", json={"question": "Q", "members": members()[:2], "chair": "or::meta/llama:free",
                                         "mode": "verify", "worker": "loc::qwen3:4b"})
    events, _ = sse(r)
    assert state["llm"][0]["model"] == "qwen3:4b" and [e for e in events if e["type"] == "draft"][0]["text"] == "LOCAL DRAFT"
    assert "LOCAL DRAFT" in state["llm"][1]["messages"][1]["content"]       # reviewers get the draft


def test_council_verify_draft_does_not_require_an_unused_worker(env):
    state, c = env
    body = {
        "question": "Q", "members": [{"ref": "loc::qwen3:4b", "persona": "researcher"}],
        "chair": "loc::qwen3:4b", "mode": "verify", "draft": "PREWRITTEN DRAFT",
        "worker": "ghost::unavailable", "keep_local": True,
    }
    response = c.post("/api/council/run", json=body)
    events, done = sse(response)
    assert response.status_code == 200 and done and events[-1]["type"] == "done"
    assert len(state["llm"]) == 2 and all(call["model"] == "qwen3:4b" for call in state["llm"])


def test_council_keep_local_rejects_any_cloud_model_before_a_single_call(env):
    state, c = env
    r = c.post("/api/council/run", json={"question": "Q", "members": members(), "chair": "loc::qwen3:4b", "keep_local": True})
    assert r.status_code == 409 and "cloud model" in r.json()["detail"] and state["llm"] == []
    local_only = [{"ref": "loc::qwen3:4b", "persona": "researcher"}, {"ref": "loc::phi4-mini", "persona": "logician"}]
    r = c.post("/api/council/run", json={"question": "Q", "members": local_only, "chair": "loc::qwen3:4b", "keep_local": True, "mode": "fanout"})
    assert r.status_code == 200 and all(call["url"].startswith("http://loc.test") for call in state["llm"])


@pytest.mark.parametrize("body,status,needle", [
    ({"members": [{"ref": "ghost::m"}], "chair": "or::m"}, 400, "Model not available"),
    ({"members": [{"ref": "or::m"}], "chair": "ghost::m"}, 400, "Model not available"),
    ({"members": [{"ref": "or::m", "persona": "wizard"}], "chair": "or::m"}, 400, "unknown persona"),
    ({"members": [{"ref": "or::m"}], "chair": "or::m", "mode": "vote"}, 400, "mode must be"),
    ({"members": [{"ref": "or::m"}], "chair": "or::m", "skill": "no-such-skill"}, 404, "not found"),
    ({"members": [{"ref": "or::m"}], "chair": "or::m", "worker": "ghost::w", "mode": "verify"}, 400, "Model not available"),
])
def test_council_run_validates_before_streaming(env, body, status, needle):
    state, c = env
    r = c.post("/api/council/run", json={"question": "Q", **body})
    assert r.status_code == status and needle in r.json()["detail"] and state["llm"] == []


def test_a_member_failing_mid_run_is_reported_not_fatal(env):
    state, c = env
    state["replies"]["qwen/coder:free"] = RuntimeError("503")
    events, done = sse(c.post("/api/council/run", json={"question": "Q", "members": members(), "chair": "or::meta/llama:free", "mode": "fanout"}))
    assert done and events[-1]["type"] == "done" and events[-1]["failed"] == 1


def test_an_unexpected_crash_ends_the_stream_cleanly(env, monkeypatch):
    state, c = env

    async def boom(*a, **k):
        raise ValueError("kaboom")
        yield  # pragma: no cover

    monkeypatch.setattr(auto_routes.cn, "run_council", boom)
    events, done = sse(c.post("/api/council/run", json={"question": "Q", "members": members()[:1], "chair": "or::meta/llama:free"}))
    assert done and events[-1] == {"type": "error", "message": "The council failed unexpectedly."}   # no stack trace leaks
