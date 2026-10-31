"""Chatbox AI gateway URLs, provider detection and request headers."""
from src import chatbox_ai
from src import endpoint_resolver as er
from src import llm_core


def test_chatbox_anthropic_gateway_is_detected_as_anthropic():
    base = "https://api.chatboxai.app/gateway/anthropic/v1"
    assert llm_core._detect_provider(base) == "anthropic"
    assert er._detect_provider(base) == "anthropic"
    assert llm_core._provider_label(base) == "Chatbox AI"
    assert er.build_chat_url(base) == "https://api.chatboxai.app/gateway/anthropic/v1/messages"
    assert llm_core._normalize_anthropic_url(base) == "https://api.chatboxai.app/gateway/anthropic/v1/messages"


def test_chatbox_openai_gateway_stays_openai_compatible():
    base = "https://api.chatboxai.app/gateway/openai/v1"
    assert llm_core._detect_provider(base) == "openai"
    assert llm_core._provider_label(base) == "Chatbox AI"
    assert er.build_chat_url(base) == "https://api.chatboxai.app/gateway/openai/v1/chat/completions"


def test_headers_use_bearer_for_openai_and_api_key_for_anthropic(monkeypatch):
    monkeypatch.setattr(chatbox_ai, "instance_id_for_key", lambda key: "inst-1")

    openai_headers = er.build_headers("lic", "https://api.chatboxai.app/gateway/openai/v1")
    assert openai_headers["Authorization"] == "Bearer lic"
    assert openai_headers["Instance-Id"] == "inst-1"

    claude_headers = er.build_headers("lic", "https://api.chatboxai.app/gateway/anthropic/v1")
    assert claude_headers["x-api-key"] == "lic"
    assert claude_headers["anthropic-version"] == "2023-06-01"
    assert claude_headers["Instance-Id"] == "inst-1"
    assert "Authorization" not in claude_headers


def test_headers_do_not_gain_instance_id_for_other_hosts(monkeypatch):
    monkeypatch.setattr(chatbox_ai, "instance_id_for_key", lambda key: "inst-1")
    headers = er.build_headers("sk-openai", "https://api.openai.com/v1")
    assert "Instance-Id" not in headers
    assert headers["Authorization"] == "Bearer sk-openai"


def test_missing_license_row_is_safe(monkeypatch):
    # Header building must never raise when the DB/store is unavailable.
    def boom(key):
        raise RuntimeError("no db")

    monkeypatch.setattr(chatbox_ai, "instance_id_for_key", boom)
    headers = er.build_headers("lic", "https://api.chatboxai.app/gateway/openai/v1")
    assert headers == {"Authorization": "Bearer lic"}
