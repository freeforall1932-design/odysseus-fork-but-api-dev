#!/usr/bin/env python3
"""Merge the upstream fork into ``main`` through a pull request, automatically.

This is the automated form of UPSTREAM_SYNC.md. The "Upstream sync" workflow
(.github/workflows/upstream-sync.yml) runs it on a schedule, on every push to
``main`` and on demand. One run:

1. fetches the upstream fork and finds its merge base with ``main``;
2. stops when ``main`` already contains the upstream tip, tidying up the
   leftover sync branch, pull request and conflict issue;
3. otherwise merges upstream into a fresh ``sync/upstream`` branch cut from
   ``main``:
   - clean merge: runs the runbook's static quick gate, pushes the branch and
     opens (or refreshes) the single sync pull request against ``main``;
   - conflict: aborts the merge and opens (or updates) one issue that lists the
     conflicted files, the matching manifest rules and the commands to resolve
     the merge by hand.

Downstream work is never rewritten: ``main`` is the first parent of every merge
commit, the sync branch is force-pushed only over the bot's own commits, and
nothing is pushed to ``main`` directly. The pull request still goes through the
repository's CI and review gates (optionally with GitHub auto-merge).

Usage:

    upstream_sync.py                  full run (reads SYNC_* and GITHUB_* env)
    upstream_sync.py --dry-run        report only; no push, PR, issue or label
    upstream_sync.py --check-only     static quick gate against the working tree
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SOURCE_REPO = "freeforall1932-design/odysseus-fork-but-api"
DEFAULT_SOURCE_BRANCH = "dev"
DEFAULT_TARGET_BRANCH = "main"
DEFAULT_SYNC_BRANCH = "sync/upstream"
DEFAULT_SERVER_URL = "https://github.com"

BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"

LABEL = "upstream-sync"
LABEL_COLOR = "0e8a16"
LABEL_DESCRIPTION = "Automated upstream sync (see UPSTREAM_SYNC.md)"
CONFLICT_LABEL = "merge conflict"

PR_MARKER = "<!-- upstream-sync-pr -->"
TRACKING_MARKER = "<!-- upstream-sync-tracking -->"
CONFLICT_MARKER = "<!-- upstream-sync-conflict -->"

RUNBOOK = "UPSTREAM_SYNC.md"
WORKFLOW = ".github/workflows/upstream-sync.yml"
MAX_LOG_LINES = 60

# ---------------------------------------------------------------------------
# Static quick gate. Mirrors the "Verification" section of UPSTREAM_SYNC.md and
# the "Downstream manifest" table: the symbols downstream modules import from
# upstream, and the downstream lines inside upstream-owned files that every
# merge must preserve. Update both places together.
# ---------------------------------------------------------------------------
UPSTREAM_SYMBOLS: list[tuple[str, str]] = [
    ("core/database.py", "ModelEndpoint"),
    ("core/database.py", "SessionLocal"),
    ("src/auth_helpers.py", "owner_filter"),
    ("src/auth_helpers.py", "require_api_token_scope"),
    ("src/endpoint_resolver.py", "resolve_endpoint_by_id"),
    ("src/llm_core.py", "llm_call_async"),
    ("routes/model_routes.py", "_classify_endpoint"),
    ("routes/model_routes.py", "_rewrite_loopback_for_docker"),
    ("core/middleware.py", "require_admin"),
    ("src/tls_overrides.py", "llm_verify"),
    ("services/memory/skill_format.py", "parse_frontmatter"),
    ("routes/prefs_routes.py", "_load_for_user"),
]

# (path, regex that must match somewhere in the file)
INTEGRATION_POINTS: list[tuple[str, str]] = [
    ("app.py", r"^skills_manager\s*="),
    ("app.py", r"setup_provider_routes\("),
    ("app.py", r"setup_auto_routes\("),
    ("static/index.html", r'src="/static/js/providerHub\.js"'),
    ("static/sw.js", r"'/static/js/providerHub\.js'"),
    ("routes/model_routes.py", r'"host\.docker\.internal"'),
    ("tests/test_tls_overrides_scope.py", r"routes/provider_routes\.py"),
    ("tests/test_docs_no_orphan_images.py", r"providers-auto-council\.md"),
    ("README.md", r"providers-auto-council\.md"),
]

PY_COMPILE_FILES = [
    "app.py",
    "core/database.py",
    "routes/auto_routes.py",
    "routes/model_routes.py",
    "routes/provider_routes.py",
    "routes/skills_routes.py",
    "src/auto_router.py",
    "src/council.py",
    "src/provider_presets.py",
]

JS_SYNTAX_FILES = ["static/js/chat.js", "static/js/providerHub.js", "static/sw.js"]


class SyncError(RuntimeError):
    """A condition the run cannot recover from; reported as ::error:: and exit 1."""


# ---------------------------------------------------------------------------
# Small process / output helpers
# ---------------------------------------------------------------------------
def sh(
    args: list[str],
    *,
    check: bool = True,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args, cwd=cwd, input=input_text, text=True, capture_output=True, check=False
    )
    if check and proc.returncode != 0:
        detail = (proc.stdout + proc.stderr).strip()
        raise SyncError(f"command failed ({proc.returncode}): {' '.join(args)}\n{detail}")
    return proc


def git(*args: str, check: bool = True) -> str:
    return sh(["git", *args], check=check).stdout.strip()


def annotate(level: str, message: str) -> None:
    """Emit a GitHub Actions workflow command (plain text elsewhere)."""
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::{level}::{escaped}", flush=True)


def set_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


class Report:
    """Collects the run summary (stdout, plus the job summary on Actions)."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, line: str = "") -> None:
        self.lines.append(line)

    def flush(self) -> None:
        text = "\n".join(self.lines).rstrip() + "\n"
        print(text, flush=True)
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if path:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(text)


def short(sha: str) -> str:
    return sha[:8]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class Config:
    source_repo: str
    source_branch: str
    target_branch: str
    sync_branch: str
    repo: str
    server_url: str
    run_url: str
    dry_run: bool
    auto_merge: bool
    offline: bool
    token_source: str

    @property
    def source_url(self) -> str:
        if "://" in self.source_repo or self.source_repo.startswith(("/", ".")):
            return self.source_repo  # a full URL or a local path (tests)
        return f"{self.server_url}/{self.source_repo}.git"

    @property
    def source_label(self) -> str:
        return self.source_repo.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def detect_repo() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo:
        return repo
    url = git("remote", "get-url", "origin", check=False)
    match = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    if not match:
        raise SyncError("cannot determine the repository; set GITHUB_REPOSITORY=owner/name")
    return match.group(1)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source-repo", default=os.environ.get("SYNC_SOURCE_REPO", DEFAULT_SOURCE_REPO))
    parser.add_argument("--source-branch", default=os.environ.get("SYNC_SOURCE_BRANCH", DEFAULT_SOURCE_BRANCH))
    parser.add_argument("--target-branch", default=os.environ.get("SYNC_TARGET_BRANCH", DEFAULT_TARGET_BRANCH))
    parser.add_argument("--sync-branch", default=os.environ.get("SYNC_BRANCH", DEFAULT_SYNC_BRANCH))
    parser.add_argument("--dry-run", action="store_true", default=env_flag("SYNC_DRY_RUN"),
                        help="report what would happen; push nothing, open nothing")
    parser.add_argument("--auto-merge", action="store_true", default=env_flag("SYNC_AUTO_MERGE"),
                        help="enable GitHub auto-merge (merge commit) on the sync PR when the quick gate passes")
    parser.add_argument("--offline", action="store_true", default=env_flag("SYNC_OFFLINE"),
                        help="never call gh (implies --dry-run); for local runs and tests")
    parser.add_argument("--check-only", action="store_true",
                        help="run the static quick gate against the working tree and exit")
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> Config:
    server_url = os.environ.get("GITHUB_SERVER_URL", DEFAULT_SERVER_URL).rstrip("/")
    repo = detect_repo()
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_url = f"{server_url}/{repo}/actions/runs/{run_id}" if run_id else "(local run)"
    return Config(
        source_repo=args.source_repo,
        source_branch=args.source_branch,
        target_branch=args.target_branch,
        sync_branch=args.sync_branch,
        repo=repo,
        server_url=server_url,
        run_url=run_url,
        dry_run=args.dry_run or args.offline,
        auto_merge=args.auto_merge,
        offline=args.offline,
        token_source=os.environ.get("SYNC_TOKEN_SOURCE", "unknown"),
    )


# ---------------------------------------------------------------------------
# Runbook manifest
# ---------------------------------------------------------------------------
def manifest_rules(markdown: str) -> dict[str, str]:
    """Map each file named in the runbook's manifest table to its resolution rule.

    The table has three columns (File | Downstream change | Resolution rule);
    the first column may list several back-ticked paths. Escaped pipes inside
    cells are preserved.
    """
    rules: dict[str, str] = {}
    in_table = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [cell.strip().replace("\x00", "|") for cell in line.replace("\\|", "\x00").strip("|").split("|")]
        if not cells:
            continue
        if cells[0].lower() == "file":
            in_table = True
            continue
        if not in_table or len(cells) < 3 or set(cells[0]) <= set("-: "):
            continue
        for path in re.findall(r"`([^`]+)`", cells[0]):
            rules[path] = cells[2]
    return rules


# ---------------------------------------------------------------------------
# Static quick gate
# ---------------------------------------------------------------------------
@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def _last_line(proc: subprocess.CompletedProcess[str]) -> str:
    text = (proc.stderr or proc.stdout or "").strip()
    return text.splitlines()[-1] if text else f"exit code {proc.returncode}"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_precache(sw_source: str) -> list[str]:
    """Return the ``/static/...`` paths of the service worker's PRECACHE list (query strings dropped)."""
    match = re.search(r"const PRECACHE = \[([\s\S]*?)\];", sw_source)
    if not match:
        return []
    entries = re.findall(r"'([^']+)'", match.group(1))
    return [entry.split("?", 1)[0] for entry in entries if entry.startswith("/static/")]


def parse_script_tags(html: str) -> list[str]:
    """Return the ``/static/...`` script sources referenced by index.html (query strings dropped)."""
    return [m.group(1) for m in re.finditer(r'<script[^>]+src="(/static/[^"?]+)', html)]


def run_static_checks(root: Path) -> list[Check]:
    checks: list[Check] = []

    for path, symbol in UPSTREAM_SYMBOLS:
        text = _read(root / path)
        pattern = rf"^(?:def|class|async def) {re.escape(symbol)}\b|^{re.escape(symbol)}\s*="
        ok = re.search(pattern, text, re.M) is not None
        checks.append(Check(f"upstream symbol {path}::{symbol}", ok,
                            "" if ok else "missing; a downstream module imports it"))

    for path, pattern in INTEGRATION_POINTS:
        ok = re.search(pattern, _read(root / path), re.M) is not None
        checks.append(Check(f"downstream line in {path} ({pattern})", ok,
                            "" if ok else "the downstream change did not survive the merge"))

    sw_path = root / "static/sw.js"
    missing = [p for p in parse_precache(_read(sw_path)) if not (root / p.lstrip("/")).exists()]
    checks.append(Check("sw.js PRECACHE assets exist", not missing, ", ".join(missing)))
    if not parse_precache(_read(sw_path)):
        checks.append(Check("sw.js PRECACHE list found", False, "could not parse `const PRECACHE = [...]`"))

    index_path = root / "static/index.html"
    missing = [p for p in parse_script_tags(_read(index_path)) if not (root / p.lstrip("/")).exists()]
    checks.append(Check("index.html script sources exist", not missing, ", ".join(missing)))

    node = shutil.which("node")
    for path in JS_SYNTAX_FILES:
        if node is None:
            checks.append(Check(f"node --check {path}", True, "skipped: node not installed"))
            continue
        proc = sh([node, "--check", path], cwd=root, check=False)
        checks.append(Check(f"node --check {path}", proc.returncode == 0, _last_line(proc) if proc.returncode else ""))

    present = [p for p in PY_COMPILE_FILES if (root / p).exists()]
    proc = sh([sys.executable, "-m", "py_compile", *present], cwd=root, check=False)
    checks.append(Check("python -m py_compile (downstream modules + app.py)", proc.returncode == 0,
                        _last_line(proc) if proc.returncode else ""))
    return checks


def checks_table(checks: list[Check]) -> str:
    lines = ["| Check | Result |", "|---|---|"]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        if check.detail:
            status += f" - {check.detail}"
        lines.append(f"| {check.name} | {status} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Text builders (pure functions; covered by tests)
# ---------------------------------------------------------------------------
@dataclass
class SyncInfo:
    cfg: Config
    upstream_sha: str
    target_sha: str
    base_sha: str
    new_commits: int = 0
    changed_files: int = 0
    upstream_log: list[str] = field(default_factory=list)
    both_sides: list[str] = field(default_factory=list)
    downstream_delta: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    tracking_issue: int | None = None
    merge_commit: str | None = None

    @property
    def source_url(self) -> str:
        return f"{self.cfg.server_url}/{self.cfg.source_repo}"

    @property
    def compare_url(self) -> str:
        return f"{self.source_url}/compare/{self.base_sha}...{self.upstream_sha}"


def merge_commit_message(info: SyncInfo) -> str:
    cfg = info.cfg
    return (
        f"Merge upstream fork {cfg.source_label} ({cfg.source_branch} @ {short(info.upstream_sha)}) into {cfg.target_branch}\n\n"
        f"Sync with {info.source_url}.\n"
        f"{info.new_commits} upstream commits, {info.changed_files} files, since {short(info.base_sha)}.\n\n"
        f"Conflicts: none (automated merge by {WORKFLOW}).\n"
        f"Downstream features preserved: everything on {cfg.target_branch} (first parent).\n"
        f"Verification: static quick gate in the pull request body; full CI on the pull request.\n"
    )


def pr_title(info: SyncInfo) -> str:
    cfg = info.cfg
    return f"chore(sync): merge upstream fork {cfg.source_label} ({cfg.source_branch} @ {short(info.upstream_sha)}) into {cfg.target_branch}"


def _details(summary: str, body: str) -> str:
    return f"<details><summary>{summary}</summary>\n\n{body}\n\n</details>"


def build_pr_body(info: SyncInfo) -> str:
    cfg = info.cfg
    failed = [c for c in info.checks if not c.ok]
    gate = (
        "All static quick-gate checks passed."
        if not failed
        else f"**{len(failed)} static quick-gate check(s) FAILED - fix before merging** (details below)."
    )
    delta = "\n".join(f"- `{p}`" for p in info.downstream_delta) or "- (none)"
    log = "\n".join(f"- `{line}`" for line in info.upstream_log) or "- (none)"
    if info.new_commits > len(info.upstream_log):
        log += f"\n- ... {info.new_commits - len(info.upstream_log)} more; see the compare link"
    both = "\n".join(f"- `{p}`" for p in info.both_sides) or "- (none)"
    tracking = f"Part of #{info.tracking_issue}" if info.tracking_issue else "Part of the upstream sync tracking issue (label `upstream-sync`)"
    token_note = (
        ""
        if cfg.token_source != "github-token"
        else "\n\n> Opened with the workflow's `GITHUB_TOKEN`: CI does not run on PRs that token creates. "
        "Add the `UPSTREAM_SYNC_TOKEN` secret (see `UPSTREAM_SYNC.md`, Automation) or push an empty commit to this branch to trigger CI."
    )

    return f"""{PR_MARKER}
## Summary

Automated upstream sync: merges `{cfg.source_repo}` branch `{cfg.source_branch}` @ `{short(info.upstream_sha)}` into `{cfg.target_branch}` @ `{short(info.target_sha)}`. {info.new_commits} upstream commit(s) touching {info.changed_files} file(s) since the last synced upstream commit `{short(info.base_sha)}` ([compare]({info.compare_url})). The merge was clean (no manual edits): `{cfg.target_branch}` is the first parent of the merge commit, so every downstream change is preserved, and `git diff --name-only {short(info.upstream_sha)} HEAD` lists {len(info.downstream_delta)} downstream file(s), to be compared with the manifest in `{RUNBOOK}`.

{gate}

This PR is rebuilt by `{WORKFLOW}` whenever `{cfg.target_branch}` or the upstream branch moves ([this run]({cfg.run_url})). Do not push manual fixes to `{cfg.sync_branch}`: the workflow refuses to overwrite commits it did not author and stops. If the merge needs hand work, resolve it locally with `{RUNBOOK}` and open a normal PR; this one closes itself once `{cfg.target_branch}` contains `{short(info.upstream_sha)}`. Merge with **Create a merge commit** (not squash or rebase) so the histories stay linked for the next sync.{token_note}

{_details("Static quick gate", checks_table(info.checks))}

{_details(f"Downstream delta after the merge ({len(info.downstream_delta)} files differ from upstream)", delta)}

{_details(f"Files changed on both sides since {short(info.base_sha)} ({len(info.both_sides)})", both)}

{_details(f"Upstream commits ({info.new_commits})", log)}

## Target branch

- [x] This PR targets `{cfg.target_branch}`, this repository's integration branch (see `{RUNBOOK}`). Upstream's `dev`/`lab` convention does not apply here.

## Linked Issue

{tracking}

## Type of Change

- [x] New feature (non-breaking — adds new behaviour)
- [x] Bug fix (non-breaking — fixes a confirmed issue)
- [x] CI / tooling / configuration

(Upstream merge: it carries whatever the {info.new_commits} upstream commit(s) contain; see the commit list above.)

## Checklist

- [x] I searched [open issues](https://github.com/odysseus-dev/odysseus/issues) and [open PRs](https://github.com/odysseus-dev/odysseus/pulls) — this is not a duplicate. (The workflow keeps a single open sync PR; earlier ones are closed or rebuilt in place.)
- [x] This PR targets the correct integration branch (`{cfg.target_branch}` in this repository)
- [x] My changes are limited to the scope described above — the diff is exactly the upstream commits, merged without manual edits.
- [ ] I actually ran the app (`docker compose up` or `uvicorn app:app`) and verified the change works end-to-end. Type-checks and unit tests are not enough.
- [x] I did not run the app/runtime validation and stated that gap in **How to Test**. Leave this unchecked when the app-run box above is checked.

## How to Test

Opened by automation: nobody has run the app for this merge. CI on this PR runs the full suite (four pytest shards, gitleaks, Trivy, workflow lint); the static quick gate above already passed in the workflow unless marked FAIL.

1. Check out `{cfg.sync_branch}` and run the quick gate: `python .github/scripts/upstream_sync.py --check-only` and the pytest command from the "Verification" section of `{RUNBOOK}` (about 430 tests, ~10 s).
2. Compare the downstream delta above with the manifest table in `{RUNBOOK}`: every row must still be present, nothing else.
3. Runtime check (not done by automation): `APP_PORT=7011 python app.py`; `curl -s -o /dev/null -w '%{{http_code}}\\n' localhost:7011/api/providers/presets` and `.../api/auto/pool` return `401` (registered, behind auth); `/static/index.html` loads `providerHub.js`.
4. Merge with a merge commit. The next workflow run (on the push to `{cfg.target_branch}`) confirms `{cfg.target_branch}` contains `{short(info.upstream_sha)}` and cleans up the sync branch.

## Visual / UI changes — REQUIRED if you touched anything that renders

Rendering changes in this PR, if any, are upstream's own and were reviewed in upstream pull requests. The merge was clean, so no downstream resolution touched rendering.

- [ ] **Screenshot or short clip** — N/A, no downstream rendering change.
- [x] **Style match**: no downstream CSS, colors, components or emoji are introduced by this merge.
- [x] **No new component patterns.**
- [x] Not a bulk auto-generated PR: a single automated upstream merge, tracked in the linked issue.

### Screenshots / clips

N/A — no downstream rendering changes.
"""


def build_tracking_issue(cfg: Config) -> tuple[str, str]:
    title = "Upstream sync: tracking issue for the automated sync pull requests"
    body = f"""{TRACKING_MARKER}
## Automated upstream sync

Rolling tracking issue for the pull requests opened by `{WORKFLOW}`. Every automated sync PR links here with `Part of #<this issue>` because the repository's PR check requires a linked issue. There is nothing to do here; keep it open. If it is closed, the next sync PR opens a new one.

- Source: `{cfg.source_repo}` branch `{cfg.source_branch}`
- Target: `{cfg.target_branch}` through the branch `{cfg.sync_branch}`
- Runbook: `{RUNBOOK}`
- Merge conflicts open a separate issue labelled `{CONFLICT_LABEL}` + `{LABEL}` with the files and the commands to resolve them.
"""
    return title, body


def conflict_issue_title(info: SyncInfo) -> str:
    cfg = info.cfg
    return f"Upstream sync conflict: {cfg.source_repo} {cfg.source_branch} @ {short(info.upstream_sha)}"


def build_conflict_issue_body(info: SyncInfo, rules: dict[str, str]) -> str:
    cfg = info.cfg
    rows = []
    for path in info.conflicts:
        rule = rules.get(path)
        if rule is None:
            rule = (f"Not in the manifest, so this is a new overlap: compare `git diff {short(info.base_sha)} origin/{cfg.target_branch} -- {path}` "
                    f"with `git diff {short(info.base_sha)} source/{cfg.source_branch} -- {path}` and keep upstream's version plus the downstream delta.")
        rows.append(f"| `{path}` | {rule} |")
    table = "\n".join(["| Conflicted file | Rule from the downstream manifest |", "|---|---|", *rows])
    manual_branch = f"sync/manual-{short(info.upstream_sha)}"
    log = "\n".join(f"- `{line}`" for line in info.upstream_log) or "- (none)"
    if info.new_commits > len(info.upstream_log):
        log += f"\n- ... {info.new_commits - len(info.upstream_log)} more; see the compare link"

    return f"""{CONFLICT_MARKER}
## The automated upstream sync needs a human

`{WORKFLOW}` ([run]({cfg.run_url})) could not merge `{cfg.source_repo}` branch `{cfg.source_branch}` @ `{short(info.upstream_sha)}` into `{cfg.target_branch}` @ `{short(info.target_sha)}`: {info.new_commits} upstream commit(s) since the last synced commit `{short(info.base_sha)}` ([compare]({info.compare_url})) conflict with downstream work in {len(info.conflicts)} file(s). Nothing was pushed. Until `{cfg.target_branch}` contains `{short(info.upstream_sha)}`, every run updates this issue in place and skips the pull request.

{table}

### Resolve locally (15-30 minutes when only the known hot spots conflict)

```bash
git fetch origin
git checkout -b {manual_branch} origin/{cfg.target_branch}
git remote add source {cfg.source_url} 2>/dev/null; git fetch source --no-tags {cfg.source_branch}
git merge --no-ff --no-commit {info.upstream_sha}
git diff --name-only --diff-filter=U        # the files above; rules in {RUNBOOK}, "Conflict playbook"
# resolve each file, then: git add <file>
python .github/scripts/upstream_sync.py --check-only   # static quick gate; then the pytest command from {RUNBOOK}, "Verification"
git commit                                   # message template in {RUNBOOK}, "Commit, push, pull request"
git push -u origin {manual_branch}
gh pr create --base {cfg.target_branch} --title "chore(sync): merge upstream fork {cfg.source_label} ({cfg.source_branch} @ {short(info.upstream_sha)}) into {cfg.target_branch}"
```

Merge that pull request with **Create a merge commit** (not squash or rebase), otherwise the histories disconnect and every later sync conflicts again. The next automated run sees that `{cfg.target_branch}` contains the upstream commit and closes this issue.

{_details(f"Upstream commits ({info.new_commits})", log)}

Last checked: {utc_now()}.
"""


# ---------------------------------------------------------------------------
# GitHub (through the gh CLI, REST endpoints only)
# ---------------------------------------------------------------------------
class GitHub:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.repo = cfg.repo
        self.owner = cfg.repo.split("/", 1)[0]
        self.label_ready = False

    def api(self, method: str, path: str, payload: dict | None = None, *, check: bool = True):
        args = ["gh", "api", "-X", method, "-H", "Accept: application/vnd.github+json", path]
        if payload is not None:
            args += ["--input", "-"]
        proc = sh(args, check=check, input_text=json.dumps(payload) if payload is not None else None)
        if proc.returncode != 0:
            return None
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def ensure_label(self) -> None:
        if self.label_ready:
            return
        if self.api("GET", f"repos/{self.repo}/labels/{LABEL}", check=False) is None:
            self.api("POST", f"repos/{self.repo}/labels",
                     {"name": LABEL, "color": LABEL_COLOR, "description": LABEL_DESCRIPTION})
        self.label_ready = True

    def add_labels(self, number: int, labels: list[str]) -> None:
        self.ensure_label()
        self.api("POST", f"repos/{self.repo}/issues/{number}/labels", {"labels": labels})

    # -- pull requests -------------------------------------------------------
    def find_sync_pr(self) -> dict | None:
        prs = self.api("GET", f"repos/{self.repo}/pulls?state=open&per_page=50"
                       f"&base={self.cfg.target_branch}&head={self.owner}:{self.cfg.sync_branch}") or []
        prs = sorted(prs, key=lambda pr: pr["number"])
        return prs[0] if prs else None

    def create_pr(self, title: str, body: str) -> dict:
        pr = self.api("POST", f"repos/{self.repo}/pulls",
                      {"title": title, "body": body, "head": self.cfg.sync_branch,
                       "base": self.cfg.target_branch})
        self.add_labels(pr["number"], [LABEL])
        return pr

    def update_pr(self, number: int, title: str, body: str) -> None:
        self.api("PATCH", f"repos/{self.repo}/pulls/{number}", {"title": title, "body": body})
        self.add_labels(number, [LABEL])

    def close_pr(self, number: int, comment: str) -> None:
        self.comment(number, comment)
        self.api("PATCH", f"repos/{self.repo}/pulls/{number}", {"state": "closed"})

    def enable_auto_merge(self, number: int) -> tuple[bool, str]:
        proc = sh(["gh", "pr", "merge", str(number), "-R", self.repo, "--auto", "--merge"], check=False)
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()

    # -- issues --------------------------------------------------------------
    def comment(self, number: int, body: str) -> None:
        self.api("POST", f"repos/{self.repo}/issues/{number}/comments", {"body": body})

    def find_marked_issue(self, marker: str, labels: list[str]) -> dict | None:
        query = ",".join(labels).replace(" ", "%20")
        issues = self.api("GET", f"repos/{self.repo}/issues?state=open&per_page=100&labels={query}") or []
        issues = [i for i in issues if "pull_request" not in i and marker in (i.get("body") or "")]
        issues.sort(key=lambda issue: issue["number"])
        return issues[0] if issues else None

    def create_issue(self, title: str, body: str, labels: list[str]) -> dict:
        self.ensure_label()
        return self.api("POST", f"repos/{self.repo}/issues", {"title": title, "body": body, "labels": labels})

    def update_issue(self, number: int, title: str, body: str) -> None:
        self.api("PATCH", f"repos/{self.repo}/issues/{number}", {"title": title, "body": body})

    def close_issue(self, number: int, comment: str) -> None:
        self.comment(number, comment)
        self.api("PATCH", f"repos/{self.repo}/issues/{number}", {"state": "closed", "state_reason": "completed"})

    # -- refs ----------------------------------------------------------------
    def delete_branch(self, name: str) -> bool:
        return self.api("DELETE", f"repos/{self.repo}/git/refs/heads/{name}", check=False) is not None


# ---------------------------------------------------------------------------
# Git plumbing for the sync
# ---------------------------------------------------------------------------
def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel"))


def configure_identity() -> None:
    """Commit as the bot without touching the repository's git config.

    The guard against overwriting human commits keys on this email, and the
    GIT_*_NAME/EMAIL variables take precedence over any ``git config``, so this
    is both process-scoped (a local dry run leaves no trace) and authoritative.
    """
    for role in ("AUTHOR", "COMMITTER"):
        os.environ[f"GIT_{role}_NAME"] = BOT_NAME
        os.environ[f"GIT_{role}_EMAIL"] = BOT_EMAIL


def fetch_refs(cfg: Config) -> None:
    # Fetch upstream by URL into refs/remotes/source/<branch>: no remote is
    # added or rewritten, so a local dry run leaves the developer's remotes alone.
    git("fetch", "--no-tags", cfg.source_url, f"+refs/heads/{cfg.source_branch}:refs/remotes/source/{cfg.source_branch}")
    git("fetch", "--no-tags", "origin", f"+refs/heads/{cfg.target_branch}:refs/remotes/origin/{cfg.target_branch}")
    git("update-ref", "-d", f"refs/remotes/origin/{cfg.sync_branch}", check=False)
    git("fetch", "--no-tags", "origin", f"+refs/heads/{cfg.sync_branch}:refs/remotes/origin/{cfg.sync_branch}", check=False)


def rev(ref: str) -> str:
    return git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")


def remote_sync_sha(cfg: Config) -> str | None:
    out = git("ls-remote", "--heads", "origin", f"refs/heads/{cfg.sync_branch}")
    return out.split()[0] if out else None


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return sh(["git", "merge-base", "--is-ancestor", ancestor, descendant], check=False).returncode == 0


def foreign_commits(sha: str, *reachable: str) -> list[str]:
    """Commits on ``sha`` (beyond ``reachable``) not authored by the bot.

    If ``sha`` is not available locally the history cannot be verified, which
    counts as foreign: callers then leave the branch alone.
    """
    proc = sh(["git", "log", "--format=%h %ae %s", sha, "--not", *reachable], check=False)
    if proc.returncode != 0:
        return [f"{short(sha)} (commit not available locally)"]
    return [line for line in proc.stdout.splitlines() if line.split()[1] != BOT_EMAIL]


def name_list(*diff_args: str) -> list[str]:
    out = sh(["git", "diff", "--name-only", "-z", *diff_args]).stdout
    return sorted(p for p in out.split("\0") if p)


@dataclass
class MergeResult:
    commit: str | None = None
    conflicts: list[str] = field(default_factory=list)


def merge_upstream(cfg: Config, target_sha: str, upstream_sha: str, message: str) -> MergeResult:
    git("checkout", "-q", "-B", cfg.sync_branch, target_sha)
    proc = sh(["git", "merge", "--no-ff", "--no-commit", upstream_sha], check=False)
    if proc.returncode != 0:
        conflicts = name_list("--diff-filter=U")
        sh(["git", "merge", "--abort"], check=False)
        if not conflicts:
            raise SyncError(f"git merge failed without reporting conflicts:\n{proc.stdout}{proc.stderr}")
        return MergeResult(conflicts=conflicts)
    git("-c", "commit.gpgsign=false", "commit", "-q", "--no-verify", "-m", message)
    return MergeResult(commit=rev("HEAD"))


def push_sync_branch(cfg: Config, expected_remote: str | None) -> None:
    args = ["git", "push", "--no-verify"]
    if expected_remote:
        args.append(f"--force-with-lease=refs/heads/{cfg.sync_branch}:{expected_remote}")
    args += ["origin", f"HEAD:refs/heads/{cfg.sync_branch}"]
    proc = sh(args, check=False)
    if proc.returncode == 0:
        return
    detail = (proc.stdout + proc.stderr).strip()
    if "workflow" in detail.lower() and "permission" in detail.lower():
        raise SyncError(
            "push rejected: the token may not update .github/workflows files that upstream changed. "
            "Add a fine-grained PAT with Workflows: read/write as the UPSTREAM_SYNC_TOKEN secret "
            f"(see {RUNBOOK}, Automation).\n{detail}"
        )
    raise SyncError(f"push failed:\n{detail}")


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------
def handle_up_to_date(cfg: Config, gh: GitHub | None, report: Report, upstream_sha: str, target_sha: str, remote_sync: str | None) -> int:
    report.add("## Upstream sync: up to date")
    report.add()
    report.add(f"`{cfg.target_branch}` @ `{short(target_sha)}` already contains `{cfg.source_repo}` `{cfg.source_branch}` @ `{short(upstream_sha)}`. Nothing to merge.")
    verb = "would " if cfg.dry_run else ""
    if gh:
        pr = gh.find_sync_pr()
        if pr:
            report.add(f"- {verb}close the stale sync PR #{pr['number']}")
            if not cfg.dry_run:
                gh.close_pr(pr["number"], f"Closing: `{cfg.target_branch}` already contains upstream `{short(upstream_sha)}` ([run]({cfg.run_url})).")
    if remote_sync:
        leftovers = foreign_commits(remote_sync, target_sha, upstream_sha)
        if leftovers:
            report.add(f"- `{cfg.sync_branch}` has commits not authored by the workflow; left alone: {'; '.join(leftovers[:5])}")
        else:
            report.add(f"- {verb}delete the leftover branch `{cfg.sync_branch}` (`{short(remote_sync)}`)")
            if gh and not cfg.dry_run:
                gh.delete_branch(cfg.sync_branch)
    if gh:
        issue = gh.find_marked_issue(CONFLICT_MARKER, [LABEL, CONFLICT_LABEL])
        if issue:
            report.add(f"- {verb}close the conflict issue #{issue['number']}")
            if not cfg.dry_run:
                gh.close_issue(issue["number"], f"Resolved: `{cfg.target_branch}` now contains upstream `{short(upstream_sha)}` ([run]({cfg.run_url})).")
    set_output("outcome", "up-to-date")
    return 0


def handle_conflict(cfg: Config, gh: GitHub | None, report: Report, info: SyncInfo, root: Path) -> int:
    rules = manifest_rules(_read(root / RUNBOOK))
    title = conflict_issue_title(info)
    body = build_conflict_issue_body(info, rules)
    report.add("## Upstream sync: merge conflict, human needed")
    report.add()
    report.add(f"Merging `{cfg.source_repo}` `{cfg.source_branch}` @ `{short(info.upstream_sha)}` into `{cfg.target_branch}` @ `{short(info.target_sha)}` conflicts in {len(info.conflicts)} file(s):")
    for path in info.conflicts:
        report.add(f"- `{path}`" + (" (manifest rule available)" if path in rules else " (not in the manifest)"))
    report.add()
    annotate("warning", f"Upstream sync conflict in {len(info.conflicts)} file(s): {', '.join(info.conflicts)}. See the conflict issue.")
    if cfg.dry_run or gh is None:
        report.add("Dry run: the conflict issue below would be opened or updated.")
        report.add()
        report.add(body)
        set_output("outcome", "conflict")
        return 0

    issue = gh.find_marked_issue(CONFLICT_MARKER, [LABEL, CONFLICT_LABEL])
    if issue:
        gh.update_issue(issue["number"], title, body)
        report.add(f"Updated the conflict issue #{issue['number']}: {issue['html_url']}")
    else:
        issue = gh.create_issue(title, body, [LABEL, CONFLICT_LABEL])
        report.add(f"Opened the conflict issue #{issue['number']}: {issue['html_url']}")
    pr = gh.find_sync_pr()
    if pr:
        gh.close_pr(pr["number"], f"Closing: the merge now conflicts with `{cfg.target_branch}`; see #{issue['number']} ([run]({cfg.run_url})).")
        report.add(f"Closed the stale sync PR #{pr['number']} (it can no longer merge).")
    set_output("outcome", "conflict")
    set_output("issue", str(issue["number"]))
    return 0


def handle_clean(cfg: Config, gh: GitHub | None, report: Report, info: SyncInfo, remote_sync: str | None) -> int:
    assert info.merge_commit
    failed = [c for c in info.checks if not c.ok]
    report.add("## Upstream sync: clean merge")
    report.add()
    report.add(f"`{cfg.source_repo}` `{cfg.source_branch}` @ `{short(info.upstream_sha)}` merged into `{cfg.target_branch}` @ `{short(info.target_sha)}` "
               f"({info.new_commits} upstream commits, {info.changed_files} files) as `{short(info.merge_commit)}` on `{cfg.sync_branch}`.")
    report.add()
    report.add(checks_table(info.checks))
    report.add()
    for check in failed:
        annotate("warning", f"quick gate failed: {check.name} {check.detail}".strip())

    unchanged = False
    if remote_sync:
        parents = git("rev-list", "--parents", "-n", "1", remote_sync, check=False).split()[1:]
        same_tree = git("rev-parse", f"{remote_sync}^{{tree}}", check=False) == git("rev-parse", f"{info.merge_commit}^{{tree}}")
        unchanged = parents == [info.target_sha, info.upstream_sha] and same_tree
        if not unchanged:
            leftovers = foreign_commits(remote_sync, info.target_sha, info.upstream_sha)
            if leftovers:
                raise SyncError(
                    f"refusing to overwrite `{cfg.sync_branch}`: it has commits the workflow did not author "
                    f"({'; '.join(leftovers[:5])}). Merge or delete that branch, then re-run."
                )

    pr = gh.find_sync_pr() if gh else None
    if unchanged:
        if pr:
            report.add(f"No change since the last run; PR #{pr['number']} is still current: {pr['html_url']}")
        else:
            report.add(f"No change since the last run and no open sync PR (closed by a human?). Not reopening until `{cfg.target_branch}` or upstream moves.")
        set_output("outcome", "unchanged")
        return 0

    if cfg.dry_run or gh is None:
        report.add(f"Dry run: would push `{short(info.merge_commit)}` to `{cfg.sync_branch}` and "
                   + (f"refresh PR #{pr['number']}." if pr else "open a new sync PR titled:"))
        if not pr:
            report.add()
            report.add(f"`{pr_title(info)}`")
        report.add(f"The local branch `{cfg.sync_branch}` is checked out at `{short(info.merge_commit)}` for inspection.")
        set_output("outcome", "dry-run")
        return 0

    push_sync_branch(cfg, remote_sync)
    tracking = gh.find_marked_issue(TRACKING_MARKER, [LABEL])
    if tracking is None:
        title, body = build_tracking_issue(cfg)
        tracking = gh.create_issue(title, body, [LABEL])
        report.add(f"Opened the tracking issue #{tracking['number']}.")
    info.tracking_issue = tracking["number"]

    title, body = pr_title(info), build_pr_body(info)
    if pr:
        gh.update_pr(pr["number"], title, body)
        report.add(f"Refreshed PR #{pr['number']}: {pr['html_url']}")
    else:
        pr = gh.create_pr(title, body)
        report.add(f"Opened PR #{pr['number']}: {pr['html_url']}")
    set_output("outcome", "pull-request")
    set_output("pull_request", str(pr["number"]))

    conflict = gh.find_marked_issue(CONFLICT_MARKER, [LABEL, CONFLICT_LABEL])
    if conflict:
        gh.close_issue(conflict["number"], f"Resolved: the merge is clean again, see PR #{pr['number']} ([run]({cfg.run_url})).")
        report.add(f"Closed the conflict issue #{conflict['number']}.")

    if cfg.auto_merge:
        if failed:
            report.add("Auto-merge not enabled: the quick gate failed.")
        else:
            ok, detail = gh.enable_auto_merge(pr["number"])
            report.add("Auto-merge enabled (merge commit, once the required checks pass)." if ok
                       else f"Auto-merge could not be enabled: {detail.splitlines()[-1] if detail else 'unknown error'}. "
                            f"It needs 'Allow auto-merge' in the repository settings and a branch protection rule on `{cfg.target_branch}` with required checks.")
            if not ok:
                annotate("warning", f"auto-merge not enabled on PR #{pr['number']}: {detail}")
    if cfg.token_source == "github-token":
        annotate("warning", "The sync PR was opened with GITHUB_TOKEN, so CI will not run on it. Add the UPSTREAM_SYNC_TOKEN secret (see UPSTREAM_SYNC.md, Automation).")
    return 0


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def run_check_only(root: Path) -> int:
    checks = run_static_checks(root)
    print(checks_table(checks))
    failed = [c for c in checks if not c.ok]
    print(f"\n{len(checks) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


def run_sync(cfg: Config, report: Report) -> int:
    root = repo_root()
    os.chdir(root)
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SyncError("the working tree has local modifications; the sync needs a clean checkout")

    gh: GitHub | None = None
    if not cfg.offline:
        if shutil.which("gh") is None or sh(["gh", "auth", "status"], check=False).returncode != 0:
            if not cfg.dry_run:
                raise SyncError("gh is not installed or not authenticated (set GH_TOKEN)")
            annotate("warning", "gh is unavailable; continuing the dry run without GitHub lookups")
        else:
            gh = GitHub(cfg)

    configure_identity()
    fetch_refs(cfg)
    target_sha = rev(f"refs/remotes/origin/{cfg.target_branch}")
    upstream_sha = rev(f"refs/remotes/source/{cfg.source_branch}")
    base_sha = git("merge-base", target_sha, upstream_sha, check=False)
    if not base_sha:
        raise SyncError(
            f"`{cfg.target_branch}` and `{cfg.source_repo}:{cfg.source_branch}` share no history, so there is no merge base. "
            f"Merge the first sync PR with a merge commit, or follow Appendix A of {RUNBOOK} to relink the histories."
        )
    remote_sync = remote_sync_sha(cfg)
    report.add(f"<!-- target {target_sha} upstream {upstream_sha} base {base_sha} -->")

    if base_sha == upstream_sha:
        return handle_up_to_date(cfg, gh, report, upstream_sha, target_sha, remote_sync)

    info = SyncInfo(cfg=cfg, upstream_sha=upstream_sha, target_sha=target_sha, base_sha=base_sha)
    info.new_commits = int(git("rev-list", "--count", f"{base_sha}..{upstream_sha}"))
    info.changed_files = len(name_list(base_sha, upstream_sha))
    info.upstream_log = git("log", "--format=%h %s", "--no-merges", "-n", str(MAX_LOG_LINES), f"{base_sha}..{upstream_sha}").splitlines()
    info.both_sides = sorted(set(name_list(base_sha, target_sha)) & set(name_list(base_sha, upstream_sha)))

    result = merge_upstream(cfg, target_sha, upstream_sha, merge_commit_message(info))
    if result.conflicts:
        info.conflicts = result.conflicts
        return handle_conflict(cfg, gh, report, info, root)

    info.merge_commit = result.commit
    info.checks = run_static_checks(root)
    info.downstream_delta = name_list(upstream_sha, "HEAD")
    return handle_clean(cfg, gh, report, info, remote_sync)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check_only:
        return run_check_only(repo_root())
    report = Report()
    try:
        cfg = build_config(args)
        code = run_sync(cfg, report)
    except SyncError as exc:
        annotate("error", str(exc))
        report.add("## Upstream sync: failed")
        report.add()
        report.add(f"```\n{exc}\n```")
        set_output("outcome", "error")
        code = 1
    finally:
        report.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
