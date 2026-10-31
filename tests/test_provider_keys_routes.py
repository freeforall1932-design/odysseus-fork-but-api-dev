"""HTTP layer for the multi-key pool (admin gate, masking, ownership)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes.provider_routes as pr
from core.database import ModelEndpoint, ProviderKey, engine, get_db_session
from src import key_pool

ENDPOINT_ID = "ep-keys-route"
KEY = "sk-route-key-1111"
SECOND = "sk-route-key-2222"


@pytest.fixture(autouse=True)
def _tables():
    ProviderKey.__table__.create(bind=engine, checkfirst=True)
    ModelEndpoint.__table__.create(bind=engine, checkfirst=True)
    key_pool.reset()
    with get_db_session() as db:
        db.query(ProviderKey).filter(ProviderKey.endpoint_id == ENDPOINT_ID).delete()
        db.query(ModelEndpoint).filter(ModelEndpoint.id == ENDPOINT_ID).delete()
        db.add(ModelEndpoint(
            id=ENDPOINT_ID,
            name="Pooled",
            base_url="https://api.example.test/v1",
            api_key=KEY,
            is_enabled=True,
        ))
    yield
    key_pool.reset()
    with get_db_session() as db:
        db.query(ProviderKey).filter(ProviderKey.endpoint_id == ENDPOINT_ID).delete()
        db.query(ModelEndpoint).filter(ModelEndpoint.id == ENDPOINT_ID).delete()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(pr, "require_admin", lambda request: None)
    monkeypatch.setattr(pr, "get_current_user", lambda request: "admin")
    app = FastAPI()
    app.include_router(pr.setup_provider_routes())
    return TestClient(app)


def test_admin_gate_is_enforced(monkeypatch):
    from fastapi import HTTPException

    def deny(request):
        raise HTTPException(403, "Admin only")

    monkeypatch.setattr(pr, "require_admin", deny)
    app = FastAPI()
    app.include_router(pr.setup_provider_routes())
    assert TestClient(app).get(f"/api/providers/keys?endpoint_id={ENDPOINT_ID}").status_code in (403, 404, 422)


def test_add_list_and_remove_a_key(client):
    added = client.post("/api/providers/keys", json={
        "endpoint_id": ENDPOINT_ID, "api_key": SECOND, "label": "backup",
    })
    assert added.status_code == 200
    body = added.json()
    assert body["ok"] is True and body["pool"]["key_count"] == 2
    assert SECOND not in added.text  # the key never comes back

    listed = client.get(f"/api/providers/keys?endpoint_id={ENDPOINT_ID}").json()
    assert [k["masked"] for k in listed["keys"]][1] == key_pool.mask_key(SECOND)

    removed = client.delete(f"/api/providers/keys/{body['id']}")
    assert removed.status_code == 200
    assert client.get(f"/api/providers/keys?endpoint_id={ENDPOINT_ID}").json()["key_count"] == 1


def test_unknown_endpoint_is_rejected(client):
    assert client.get("/api/providers/keys?endpoint_id=nope").status_code == 404
    assert client.post("/api/providers/keys", json={
        "endpoint_id": "nope", "api_key": SECOND,
    }).status_code == 404


def test_toggle_disables_a_key_and_reset_clears_cooldowns(client):
    added = client.post("/api/providers/keys", json={
        "endpoint_id": ENDPOINT_ID, "api_key": SECOND,
    }).json()
    key_pool.record_failure(ENDPOINT_ID, KEY, status=429)
    assert client.get(f"/api/providers/keys?endpoint_id={ENDPOINT_ID}").json()["healthy_count"] == 1

    assert client.patch(f"/api/providers/keys/{added['id']}", json={"is_enabled": False}).status_code == 200
    assert client.get(f"/api/providers/keys?endpoint_id={ENDPOINT_ID}").json()["key_count"] == 1

    assert client.post(f"/api/providers/keys/reset?endpoint_id={ENDPOINT_ID}").status_code == 200
    assert client.get(f"/api/providers/keys?endpoint_id={ENDPOINT_ID}").json()["healthy_count"] == 1


def test_blank_key_is_rejected(client):
    response = client.post("/api/providers/keys", json={"endpoint_id": ENDPOINT_ID, "api_key": "   "})
    assert response.status_code == 400
