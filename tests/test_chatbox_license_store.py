"""Encrypted Chatbox AI license storage (real SQLAlchemy table, isolated rows)."""
import json

import pytest

from core.database import ChatboxAILicense, engine, get_db_session
from src import chatbox_ai

KEY = "cbx-store-test-key-abcdef"
DETAIL = {"name": "Chatbox AI Pro", "plan": "pro", "status": "active",
          "unified_token_usage": 10, "unified_token_limit": 100}


@pytest.fixture(autouse=True)
def _table():
    ChatboxAILicense.__table__.create(bind=engine, checkfirst=True)
    chatbox_ai._clear_instance_cache()
    yield
    with get_db_session() as db:
        db.query(ChatboxAILicense).delete()
    chatbox_ai._clear_instance_cache()


def test_save_load_and_instance_lookup():
    chatbox_ai.save_license(None, KEY, "inst-1", DETAIL, instance_name="Odysseus")
    stored = chatbox_ai.load_license(None)
    assert stored["license_key"] == KEY
    assert stored["instance_id"] == "inst-1"
    assert stored["instance_name"] == "Odysseus"
    assert stored["detail"]["plan"] == "pro"
    assert stored["summary"]["quotas"]["unified_limit"] == 100
    assert stored["masked_key"] == chatbox_ai.mask_key(KEY)
    assert chatbox_ai.instance_id_for_key(KEY) == "inst-1"
    assert chatbox_ai.auth_headers(KEY, "https://api.chatboxai.app/gateway/openai/v1") == {
        "Instance-Id": "inst-1",
    }


def test_secrets_are_encrypted_at_rest():
    from sqlalchemy import text

    chatbox_ai.save_license(None, KEY, "inst-1", DETAIL)
    with get_db_session() as db:
        # Raw SQL bypasses the TypeDecorator: this is what a stolen DB file holds.
        raw_key, raw_instance = db.execute(
            text("SELECT license_key, instance_id FROM chatbox_ai_licenses")
        ).one()
    assert raw_key.startswith("enc:") and KEY not in raw_key
    assert raw_instance.startswith("enc:") and "inst-1" not in raw_instance


def test_new_license_deactivates_the_previous_one():
    chatbox_ai.save_license(None, KEY, "inst-1", DETAIL)
    other = "cbx-second-key-9999"
    chatbox_ai.save_license(None, other, "inst-2", {**DETAIL, "plan": "max"})
    stored = chatbox_ai.load_license(None)
    assert stored["license_key"] == other
    assert stored["plan"] == "max"
    assert chatbox_ai.instance_id_for_key(KEY) == ""
    assert chatbox_ai.instance_id_for_key(other) == "inst-2"


def test_owner_scope_is_respected():
    chatbox_ai.save_license("alice", KEY, "inst-a", DETAIL)
    assert chatbox_ai.load_license("alice")["license_key"] == KEY
    assert chatbox_ai.load_license("bob") is None


def test_remove_license_clears_cache_and_rows():
    chatbox_ai.save_license(None, KEY, "inst-1", DETAIL)
    assert chatbox_ai.instance_id_for_key(KEY) == "inst-1"
    removed = chatbox_ai.remove_license(None)
    assert removed["license_key"] == KEY
    assert chatbox_ai.load_license(None) is None
    assert chatbox_ai.instance_id_for_key(KEY) == ""


def test_unlink_disables_only_matching_endpoints():
    from core.database import ModelEndpoint

    ModelEndpoint.__table__.create(bind=engine, checkfirst=True)
    with get_db_session() as db:
        db.add(ModelEndpoint(id="cb1", name="Chatbox AI", base_url="https://api.chatboxai.app/gateway/openai/v1",
                             api_key=KEY, is_enabled=True))
        db.add(ModelEndpoint(id="cb2", name="Chatbox AI · Claude", base_url="https://api.chatboxai.app/gateway/anthropic/v1",
                             api_key=KEY, is_enabled=True))
        db.add(ModelEndpoint(id="other", name="OpenAI", base_url="https://api.openai.com/v1",
                             api_key="sk-other", is_enabled=True))
    assert chatbox_ai.disable_endpoints_for_key(KEY) == 2
    with get_db_session() as db:
        rows = {row.id: row for row in db.query(ModelEndpoint).all()}
        assert rows["cb1"].api_key is None and rows["cb1"].is_enabled is False
        assert rows["cb2"].api_key is None and rows["cb2"].is_enabled is False
        assert rows["other"].api_key == "sk-other" and rows["other"].is_enabled is True
        db.query(ModelEndpoint).delete()
    assert chatbox_ai.disable_endpoints_for_key("") == 0


def test_detail_json_is_not_double_encoded():
    chatbox_ai.save_license(None, KEY, "inst-1", DETAIL)
    with get_db_session() as db:
        stored = chatbox_ai.load_license(None)
    assert json.loads(json.dumps(stored["detail"]))["name"] == "Chatbox AI Pro"
