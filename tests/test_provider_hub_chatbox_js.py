"""Chatbox AI provider-hub helpers (connectGroups / licenseQuotaText) under Node."""
import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "static" / "js" / "providerHub.js"
_HAS_NODE = shutil.which("node") is not None


def _run(script: str):
    proc = subprocess.run(
        ["node", "--input-type=module"],
        input=script,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(_REPO),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip())


def _module_script(tmp_path: Path, body: str) -> str:
    module = tmp_path / "providerHub.mjs"
    module.write_text(_SRC.read_text(encoding="utf-8"), encoding="utf-8")
    return textwrap.dedent(
        f"""
        import {{ connectGroups, licenseQuotaText }} from {json.dumps(module.as_uri())};
        {body}
        """
    )


@pytest.mark.skipif(not _HAS_NODE, reason="node binary not on PATH")
def test_connect_groups_splits_gateways_and_keeps_the_selection(tmp_path):
    discovery = {
        "base_url": "https://api.chatboxai.app/gateway/openai/v1",
        "variants": [
            {"api_style": "openai", "base_url": "https://api.chatboxai.app/gateway/openai/v1",
             "model_ids": ["gpt-5.2", "o4-mini"]},
            {"api_style": "anthropic", "base_url": "https://api.chatboxai.app/gateway/anthropic/v1",
             "model_ids": ["claude-sonnet-4.5"]},
        ],
        "models": [
            {"id": "gpt-5.2", "supported": True},
            {"id": "o4-mini", "supported": True},
            {"id": "claude-sonnet-4.5", "supported": True},
            {"id": "gemini-2.5-flash", "supported": False},
        ],
    }
    groups = _run(_module_script(tmp_path, f"""
        console.log(JSON.stringify(connectGroups({json.dumps(discovery)}, ["gpt-5.2", "claude-sonnet-4.5"])));
    """))
    assert groups == [
        {"api_style": "openai", "label": "", "base_url": "https://api.chatboxai.app/gateway/openai/v1",
         "model_ids": ["gpt-5.2"]},
        {"api_style": "anthropic", "label": "", "base_url": "https://api.chatboxai.app/gateway/anthropic/v1",
         "model_ids": ["claude-sonnet-4.5"]},
    ]


@pytest.mark.skipif(not _HAS_NODE, reason="node binary not on PATH")
def test_connect_groups_falls_back_for_regular_providers(tmp_path):
    discovery = {
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            {"id": "a", "supported": True},
            {"id": "b", "supported": False},
            {"id": "c"},
        ],
    }
    groups = _run(_module_script(tmp_path, f"""
        console.log(JSON.stringify(connectGroups({json.dumps(discovery)}, ["a", "b", "c"])));
    """))
    assert groups == [{"api_style": "openai", "label": "", "base_url": "https://openrouter.ai/api/v1",
                       "model_ids": ["a", "c"]}]


@pytest.mark.skipif(not _HAS_NODE, reason="node binary not on PATH")
def test_license_quota_text_is_plain_and_hides_missing_numbers(tmp_path):
    summary = {"plan": "pro", "expires_at": "2027-01-31T00:00:00Z",
               "quotas": {"unified_used": 12300, "unified_limit": 50000, "remaining_images": 34}}
    text = _run(_module_script(tmp_path, f"""
        console.log(JSON.stringify(licenseQuotaText({json.dumps(summary)})));
    """))
    assert "Quota 12.3k/50k" in text
    assert "34 images left" in text
    assert "2027-01-31" in text
    empty = _run(_module_script(tmp_path, """
        console.log(JSON.stringify(licenseQuotaText({})));
    """))
    assert empty == ""


@pytest.mark.skipif(not _HAS_NODE, reason="node binary not on PATH")
def test_pool_key_label_summarises_health(tmp_path):
    module = tmp_path / "providerHub.mjs"
    module.write_text(_SRC.read_text(encoding="utf-8"), encoding="utf-8")
    script = textwrap.dedent(
        f"""
        import {{ poolKeyLabel }} from {json.dumps(module.as_uri())};
        console.log(JSON.stringify({{
          primary: poolKeyLabel({{ masked: 'sk-abc…1234', label: 'primary', persisted: false }}),
          cooling: poolKeyLabel({{ masked: 'sk-d…9999', label: 'backup', persisted: true,
                                   cooling_down: true, cooldown_seconds: 42, last_status: 429 }}),
          healthy: poolKeyLabel({{ masked: 'sk-e…8888', persisted: true, successes: 7 }}),
          failing: poolKeyLabel({{ masked: 'sk-f…7777', persisted: true, failures: 1 }}),
        }}));
        """
    )
    out = _run(script)
    assert out["primary"] == "sk-abc…1234 · primary"
    assert out["cooling"] == "sk-d…9999 · backup · cooling 42s (429)"
    assert out["healthy"] == "sk-e…8888 · ok"
    assert out["failing"] == "sk-f…7777 · 1 failure"
