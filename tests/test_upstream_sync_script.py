"""Tests for the automated upstream sync helper (.github/scripts/upstream_sync.py)."""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = ROOT / ".github" / "scripts" / "upstream_sync.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "upstream-sync.yml"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(module)
    return module


sync = _load_module("upstream_sync", SCRIPT_PATH)


def _config(**overrides):
    values = dict(
        source_repo="example/odysseus-fork-but-api",
        source_branch="dev",
        target_branch="main",
        sync_branch="sync/upstream",
        repo="example/odysseus-fork-but-api-dev",
        server_url="https://github.com",
        run_url="https://github.com/example/odysseus-fork-but-api-dev/actions/runs/1",
        dry_run=False,
        auto_merge=False,
        offline=False,
        token_source="pat",
    )
    values.update(overrides)
    return sync.Config(**values)


def _info(**overrides):
    cfg = overrides.pop("cfg", _config())
    values = dict(
        cfg=cfg,
        upstream_sha="1234567890abcdef1234567890abcdef12345678",
        target_sha="abcdef1234567890abcdef1234567890abcdef12",
        base_sha="86b886c611338282af6d4a717246ea4e256f58df",
        new_commits=12,
        changed_files=34,
        upstream_log=["1234567 feat: something", "89abcde fix: other"],
        both_sides=["static/js/chat.js"],
        downstream_delta=["app.py", "static/js/providerHub.js"],
        checks=[sync.Check("symbol a", True), sync.Check("symbol b", False, "missing")],
        tracking_issue=42,
        merge_commit="fedcba9876543210fedcba9876543210fedcba98",
    )
    values.update(overrides)
    return sync.SyncInfo(**values)


# ── The PR body must satisfy .github/scripts/check-pr-description.js ───────────
def _section(body: str, heading: str) -> str:
    match = re.search(rf"#+\s+{heading}[\s\S]*?(?=\n#+\s+|$)", body, re.I)
    text = re.sub(rf"#+\s+{heading}", "", match.group(0), flags=re.I) if match else ""
    return re.sub(r"<!--[\s\S]*?-->", "", text).strip()


def test_pr_body_passes_the_description_check_rules():
    body = sync.build_pr_body(_info())

    assert len(_section(body, "Summary")) >= 20
    assert re.search(r"#\d+\b", _section(body, "Linked Issue"))
    type_block = re.search(r"##\s+Type of Change[\s\S]*?(?=\n##\s|$)", body, re.I).group(0)
    assert re.search(r"- \[x\]", type_block, re.I)
    assert re.search(r"- \[x\] I searched", body, re.I)
    assert len(_section(body, "How to Test")) >= 30
    # Exactly one of the two runtime attestations is ticked (automation never runs the app).
    assert not re.search(r"- \[x\]\s+I actually ran the app\b", body, re.I)
    assert re.search(r"- \[x\]\s+I did not run the app/runtime validation\b", body, re.I)
    assert body.startswith(sync.PR_MARKER)
    assert "Part of #42" in body


@pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
@pytest.mark.parametrize("files", [["static/js/chat.js", "routes/x.py", ".github/workflows/ci.yml"], ["routes/x.py"], ["docs/a.md"]])
def test_pr_body_passes_the_real_description_checker(files):
    """Run the generated body through .github/scripts/check-pr-description.js itself."""
    harness = _load_module("test_pr_description_check", ROOT / "tests" / "test_pr_description_check.py")
    calls = harness._run_checker(files, sync.build_pr_body(_info()), owner="example", repo="odysseus-fork-but-api-dev")
    assert not [call for call in calls if call["method"] == "setFailed"], calls
    # Sync PRs are UI-sensitive/runtime-sensitive by nature; those labels are advisory, never failures.
    assert harness._added_labels(calls) <= {"ready for review", "needs runtime validation", "needs visual evidence"}


def test_pr_body_reports_failed_checks_and_the_github_token_gap():
    body = sync.build_pr_body(_info())
    assert "1 static quick-gate check(s) FAILED" in body
    assert "| symbol b | FAIL - missing |" in body
    assert "GITHUB_TOKEN" not in body  # token_source is "pat"

    body = sync.build_pr_body(_info(cfg=_config(token_source="github-token"), checks=[sync.Check("ok", True)]))
    assert "All static quick-gate checks passed." in body
    assert "UPSTREAM_SYNC_TOKEN" in body


def test_pr_title_is_conventional_commits():
    title = sync.pr_title(_info())
    assert title == "chore(sync): merge upstream fork odysseus-fork-but-api (dev @ 12345678) into main"
    # Regex from .github/workflows/pr-description-check.yml
    assert re.match(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([\w .\/-]+\))?!?: .+", title)


def test_merge_commit_message_follows_the_runbook_template():
    message = sync.merge_commit_message(_info())
    first, _, rest = message.partition("\n")
    assert first == "Merge upstream fork odysseus-fork-but-api (dev @ 12345678) into main"
    assert "12 upstream commits, 34 files, since 86b886c6." in rest
    assert "https://github.com/example/odysseus-fork-but-api" in rest


# ── Conflict issue ────────────────────────────────────────────────────────────
def test_conflict_issue_body_lists_files_with_manifest_rules_and_commands():
    info = _info(conflicts=["static/js/chat.js", "brand/new.py"])
    rules = {"static/js/chat.js": "Keep upstream's Agent-mode block byte-for-byte."}
    body = sync.build_conflict_issue_body(info, rules)

    assert body.startswith(sync.CONFLICT_MARKER)
    assert len(body) >= 50
    assert "| `static/js/chat.js` | Keep upstream's Agent-mode block byte-for-byte. |" in body
    assert "| `brand/new.py` | Not in the manifest" in body
    assert f"git merge --no-ff --no-commit {info.upstream_sha}" in body
    assert "git checkout -b sync/manual-12345678 origin/main" in body
    assert "Create a merge commit" in body
    assert sync.conflict_issue_title(info) == "Upstream sync conflict: example/odysseus-fork-but-api dev @ 12345678"


def test_tracking_issue_body_is_long_enough_for_the_issue_check():
    title, body = sync.build_tracking_issue(_config())
    assert title.startswith("Upstream sync:")
    assert body.startswith(sync.TRACKING_MARKER)
    assert len(re.sub(r"<!--[\s\S]*?-->", "", body).strip()) >= 50


# ── Runbook manifest parsing ──────────────────────────────────────────────────
def test_manifest_rules_maps_every_backticked_path_and_keeps_escaped_pipes():
    markdown = textwrap.dedent(
        """
        | File | Downstream change | Resolution rule when it conflicts |
        |---|---|---|
        | `a.py`, `b.py` | shared change | Keep ours. |
        | `c.js` | the `msg \\|\\| ''` literal | Keep upstream's block \\| byte-for-byte. |

        prose between tables

        | Name | What it is | Branch |
        |---|---|---|
        | `z.py` | not a manifest row | ignored |
        """
    )
    rules = sync.manifest_rules(markdown)
    assert rules == {
        "a.py": "Keep ours.",
        "b.py": "Keep ours.",
        "c.js": "Keep upstream's block | byte-for-byte.",
    }


def test_real_runbook_manifest_covers_the_integration_points():
    rules = sync.manifest_rules((ROOT / sync.RUNBOOK).read_text(encoding="utf-8"))
    assert len(rules) >= 20
    for path, _pattern in sync.INTEGRATION_POINTS:
        assert path in rules, f"{path} is checked by the quick gate but has no manifest row"
    assert "static/js/chat.js" in rules and "Agent-mode block" in rules["static/js/chat.js"]


# ── Static quick gate helpers ─────────────────────────────────────────────────
def test_parse_precache_and_script_tags_strip_query_strings():
    sw = "const CACHE_NAME = 'x';\nconst PRECACHE = [\n  '/',\n  '/static/css/a.css?v=1',\n  '/static/js/b.js',\n];\nother('/static/js/c.js');"
    assert sync.parse_precache(sw) == ["/static/css/a.css", "/static/js/b.js"]
    html = '<script defer src="/static/lib/h.js"></script>\n<script type="module" src="/static/js/ui.js?v=2"\n></script><script src="https://cdn/x.js"></script>'
    assert sync.parse_script_tags(html) == ["/static/lib/h.js", "/static/js/ui.js"]


def test_static_quick_gate_passes_on_this_tree():
    checks = sync.run_static_checks(ROOT)
    failed = [f"{c.name}: {c.detail}" for c in checks if not c.ok]
    assert not failed, failed
    assert len(checks) >= 25


# ── End to end against throwaway local repositories (offline: no gh calls) ────
def _git(cwd: Path, *args: str, env: dict[str, str]) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def _commit_all(cwd: Path, message: str, env: dict[str, str]) -> str:
    _git(cwd, "add", "-A", env=env)
    _git(cwd, "commit", "-q", "-m", message, env=env)
    return _git(cwd, "rev-parse", "HEAD", env=env)


@pytest.fixture
def sync_world(tmp_path: Path):
    """An 'upstream' repo, a bare 'origin' and a clone whose main carries downstream work."""
    env = dict(os.environ)
    env.update(
        GIT_CONFIG_GLOBAL=str(tmp_path / "gitconfig"),
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Dev",
        GIT_AUTHOR_EMAIL="dev@example.com",
        GIT_COMMITTER_NAME="Dev",
        GIT_COMMITTER_EMAIL="dev@example.com",
        GITHUB_REPOSITORY="example/repo",
    )
    for key in ("GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT", "GITHUB_RUN_ID", "SYNC_DRY_RUN", "SYNC_OFFLINE"):
        env.pop(key, None)
    (tmp_path / "gitconfig").write_text("")

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "dev", env=env)
    (upstream / "a.txt").write_text("line1\nline2\nline3\n")
    (upstream / "b.txt").write_text("b1\n")
    _commit_all(upstream, "u1: initial", env)

    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin), env=env)

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "-b", "dev", str(upstream), str(clone), env=env)
    _git(clone, "checkout", "-q", "-b", "main", env=env)
    (clone / "a.txt").write_text("line1\nline2\nline3 downstream\n")
    (clone / "d.txt").write_text("downstream only\n")
    (clone / "UPSTREAM_SYNC.md").write_text(
        "| File | Downstream change | Resolution rule when it conflicts |\n|---|---|---|\n"
        "| `a.txt` | line3 edited | Keep upstream's line, then re-add the downstream suffix. |\n"
    )
    _commit_all(clone, "d1: downstream work", env)
    _git(clone, "remote", "remove", "origin", env=env)
    _git(clone, "remote", "add", "origin", str(origin), env=env)
    _git(clone, "push", "-q", "-u", "origin", "main", env=env)
    return {"env": env, "upstream": upstream, "origin": origin, "clone": clone}


def _run_sync(world, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--offline", "--source-repo", str(world["upstream"]), "--source-branch", "dev", *extra],
        cwd=world["clone"], env=world["env"], capture_output=True, text=True, check=False,
    )


def test_offline_run_builds_the_merge_locally_without_pushing(sync_world):
    env, upstream, clone = sync_world["env"], sync_world["upstream"], sync_world["clone"]
    (upstream / "b.txt").write_text("b1\nb2 upstream\n")
    upstream_sha = _commit_all(upstream, "u2: touch b", env)
    main_sha = _git(clone, "rev-parse", "main", env=env)

    proc = _run_sync(sync_world)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "## Upstream sync: clean merge" in proc.stdout
    assert "Dry run: would push" in proc.stdout
    merge = _git(clone, "rev-list", "--parents", "-n", "1", "sync/upstream", env=env).split()
    assert merge[1:] == [main_sha, upstream_sha], "main must be the first parent, upstream the second"
    assert _git(clone, "show", "sync/upstream:a.txt", env=env) == "line1\nline2\nline3 downstream"
    assert _git(clone, "show", "sync/upstream:b.txt", env=env) == "b1\nb2 upstream"
    assert _git(clone, "log", "-1", "--format=%ae", "sync/upstream", env=env) == sync.BOT_EMAIL
    assert _git(clone, "ls-remote", "--heads", "origin", "sync/upstream", env=env) == "", "dry runs never push"


def test_offline_run_reports_conflicts_with_manifest_rules_and_aborts_cleanly(sync_world):
    env, upstream, clone = sync_world["env"], sync_world["upstream"], sync_world["clone"]
    (upstream / "a.txt").write_text("line1\nline2\nline3 upstream\n")
    _commit_all(upstream, "u3: touch a", env)

    proc = _run_sync(sync_world)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "## Upstream sync: merge conflict, human needed" in proc.stdout
    assert "::warning::Upstream sync conflict in 1 file(s): a.txt" in proc.stdout
    assert "| `a.txt` | Keep upstream's line, then re-add the downstream suffix. |" in proc.stdout
    assert _git(clone, "status", "--porcelain", env=env) == "", "the aborted merge must leave a clean tree"
    assert not (clone / ".git" / "MERGE_HEAD").exists()


def test_offline_run_detects_an_up_to_date_main(sync_world):
    env, upstream, clone = sync_world["env"], sync_world["upstream"], sync_world["clone"]
    (upstream / "b.txt").write_text("b1\nb2 upstream\n")
    _commit_all(upstream, "u2: touch b", env)
    _git(clone, "fetch", "-q", str(upstream), "dev", env=env)
    _git(clone, "merge", "-q", "--no-ff", "-m", "manual sync", "FETCH_HEAD", env=env)
    _git(clone, "push", "-q", "origin", "main", env=env)

    proc = _run_sync(sync_world)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "## Upstream sync: up to date" in proc.stdout


def test_offline_run_fails_loudly_without_a_merge_base(sync_world, tmp_path):
    env = sync_world["env"]
    stranger = tmp_path / "stranger"
    stranger.mkdir()
    _git(stranger, "init", "-q", "-b", "dev", env=env)
    (stranger / "x.txt").write_text("unrelated\n")
    _commit_all(stranger, "unrelated history", env)
    sync_world["upstream"] = stranger

    proc = _run_sync(sync_world)

    assert proc.returncode == 1
    assert "::error::" in proc.stdout and "share no history" in proc.stdout


# ── Workflow wiring ───────────────────────────────────────────────────────────
def test_workflow_passes_everything_through_env_and_calls_the_script():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "python .github/scripts/upstream_sync.py" in text
    assert "persist-credentials: false" in text
    assert "fetch-depth: 0" in text
    for name in ("SYNC_SOURCE_REPO", "SYNC_SOURCE_BRANCH", "SYNC_DRY_RUN", "SYNC_AUTO_MERGE", "SYNC_TOKEN_SOURCE", "GH_TOKEN"):
        assert name in text, f"{name} missing from the workflow"
    # No expression interpolation inside run: blocks (template injection).
    for block in re.findall(r"run: \|?\n((?:[ \t]+.*\n?)+)", text):
        assert "${{" not in block
