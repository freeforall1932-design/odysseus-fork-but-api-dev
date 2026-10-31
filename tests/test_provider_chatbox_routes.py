"""HTTP layer for Chatbox AI onboarding (license store and upstream mocked)."""
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes.provider_routes as pr
from src import chatbox_ai, provider_presets as pp

KEY = "cbx-route-test-key-abcdef123456"
DETAIL = {
    "name": "Chatbox AI Pro",
    "plan": "pro",
    "status": "active",
    "expires_at": "2027-01-31T00:00:00Z",
    "unified_token_usage": 1_000,
    "unified_token_limit": 10_000,
    "remaining_quota_image": 3,
}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(pr, "require_admin", lambda request: None)
    monkeypatch.setattr(pr, "get_current_user", lambda request: "admin")
    application = FastAPI()
    application.include_router(pr.setup_provider_routes())
    return application


def test_models_route_persists_license_and_strips_private_fields(app, monkeypatch):
    saved = {}

    def fake_save(owner, license_key, instance_id, detail, *, instance_name=None):
        saved.update(owner=owner, key=license_key, instance_id=instance_id,
                     detail=detail, instance_name=instance_name)
        return {"id": "x"}

    async def fake_discover(preset_id, api_key="", base_url="", **kw):
        return pp.Discovery(
            cards=[
                pp.ModelCard("gpt-5.2", api_style="openai", supported=True),
                pp.ModelCard("claude-sonnet-4.5", api_style="anthropic", supported=True),
                pp.ModelCard("gemini-2.5-flash", api_style="google", supported=False),
            ],
            key_info={
                "provider": "chatboxai",
                "masked_key": "cbx-…3456",
                "summary": {"plan": "pro"},
                "instance_id": "inst-1",
                "instance_name": "Odysseus",
                "license_detail": DETAIL,
                "variants": [{"api_style": "openai", "base_url": "https://api.chatboxai.app/gateway/openai/v1"}],
                "unsupported": [{"api_style": "google", "model_ids": ["gemini-2.5-flash"]}],
            },
        )

    monkeypatch.setattr(pp, "discover", fake_discover)
    monkeypatch.setattr(chatbox_ai, "save_license", fake_save)

    c = TestClient(app)
    r = c.post("/api/providers/models", json={"provider": "chatboxai", "api_key": KEY})
    body = r.json()
    assert r.status_code == 200
    assert body["count"] == 3
    assert body["models"][0]["api_style"] == "openai"
    assert body["variants"][0]["api_style"] == "openai"
    assert body["unsupported"][0]["api_style"] == "google"
    assert "instance_id" not in body["key_info"]
    assert "license_detail" not in body["key_info"]
    assert body["key_info"]["masked_key"] == "cbx-…3456"
    assert saved == {"owner": "admin", "key": KEY, "instance_id": "inst-1",
                     "detail": DETAIL, "instance_name": "Odysseus"}
    assert KEY not in r.text


def test_models_route_requires_a_key(app):
    c = TestClient(app)
    r = c.post("/api/providers/models", json={"provider": "chatboxai", "api_key": ""})
    assert r.status_code == 400
    assert "license key" in r.json()["detail"].lower()


def test_status_route_never_returns_the_key(app, monkeypatch):
    monkeypatch.setattr(chatbox_ai, "load_license", lambda owner: {
        "license_key": KEY,
        "masked_key": "cbx-…3456",
        "instance_id": "inst-1",
        "instance_name": "Odysseus",
        "plan": "pro",
        "status": "active",
        "detail": DETAIL,
        "summary": chatbox_ai.summarize_detail(DETAIL),
        "last_checked": None,
    })
    c = TestClient(app)
    r = c.get("/api/providers/chatbox/status")
    body = r.json()
    assert r.status_code == 200 and body["configured"] is True
    assert body["plan"] == "pro"
    assert body["has_instance"] is True
    assert KEY not in r.text
    assert "license_key" not in body


def test_status_route_refresh_keeps_cached_summary_on_failure(app, monkeypatch):
    monkeypatch.setattr(chatbox_ai, "load_license", lambda owner: {
        "license_key": KEY, "masked_key": "cbx-…3456", "instance_id": "i",
        "instance_name": "Odysseus", "detail": DETAIL, "summary": chatbox_ai.summarize_detail(DETAIL),
        "last_checked": None,
    })

    async def boom(client, key, **kw):
        raise chatbox_ai.ChatboxError("Chatbox AI is having trouble right now (HTTP 503).", status=503)

    monkeypatch.setattr(chatbox_ai, "license_detail", boom)
    c = TestClient(app)
    body = c.get("/api/providers/chatbox/status?refresh=true").json()
    assert body["configured"] is True
    assert body["summary"]["plan"] == "pro"
    assert body["detail_error"]["code"] == "refresh_failed"


def test_activate_route_stores_the_license(app, monkeypatch):
    saved = {}

    async def fake_activate(client, key, instance_name=None, **kw):
        assert key == KEY
        return {"valid": True, "instance_id": "inst-2", "error": ""}

    async def fake_detail(client, key, **kw):
        return DETAIL, None

    def fake_save(owner, license_key, instance_id, detail, *, instance_name=None):
        saved.update(owner=owner, instance_id=instance_id, key=license_key)

    monkeypatch.setattr(chatbox_ai, "activate_license", fake_activate)
    monkeypatch.setattr(chatbox_ai, "license_detail", fake_detail)
    monkeypatch.setattr(chatbox_ai, "save_license", fake_save)

    c = TestClient(app)
    r = c.post("/api/providers/chatbox/activate", json={"license_key": KEY, "instance_name": "Desk"})
    body = r.json()
    assert r.status_code == 200 and body["ok"] is True
    assert body["summary"]["plan"] == "pro"
    assert saved["instance_id"] == "inst-2" and saved["owner"] == "admin"
    assert KEY not in r.text


def test_activate_route_rejects_an_invalid_license(app, monkeypatch):
    async def fake_activate(client, key, instance_name=None, **kw):
        return {"valid": False, "instance_id": "", "error": "not found"}

    monkeypatch.setattr(chatbox_ai, "activate_license", fake_activate)
    c = TestClient(app)
    r = c.post("/api/providers/chatbox/activate", json={"license_key": KEY})
    assert r.status_code == 400
    assert "rejected" in r.json()["detail"].lower()
    assert KEY not in r.text


def test_deactivate_route_releases_and_removes(app, monkeypatch):
    released = {}

    monkeypatch.setattr(chatbox_ai, "load_license", lambda owner: {
        "license_key": KEY, "instance_id": "inst-3", "masked_key": "x",
    })

    async def fake_deactivate(client, key, instance_id, **kw):
        released.update(key=key, instance_id=instance_id)

    monkeypatch.setattr(chatbox_ai, "deactivate_license", fake_deactivate)
    monkeypatch.setattr(chatbox_ai, "remove_license", lambda owner: True)
    monkeypatch.setattr(chatbox_ai, "disable_endpoints_for_key", lambda key: 2)

    c = TestClient(app)
    r = c.post("/api/providers/chatbox/deactivate")
    assert r.status_code == 200 and r.json()["ok"] is True
    assert r.json()["disabled_endpoints"] == 2
    assert released == {"key": KEY, "instance_id": "inst-3"}


def test_deactivate_without_a_license_is_idempotent(app, monkeypatch):
    monkeypatch.setattr(chatbox_ai, "load_license", lambda owner: None)
    c = TestClient(app)
    assert c.post("/api/providers/chatbox/deactivate").json()["configured"] is False


def test_status_route_requires_admin(monkeypatch):
    application = FastAPI()
    application.include_router(pr.setup_provider_routes())

    def deny(request):
        from fastapi import HTTPException
        raise HTTPException(403, "Admin only")

    monkeypatch.setattr(pr, "require_admin", deny)
    c = TestClient(application)
    assert c.get("/api/providers/chatbox/status").status_code == 403
