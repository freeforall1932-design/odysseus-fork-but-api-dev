# Upstream sync runbook

How to pull new upstream commits into this repository while keeping the
downstream customizations. The first sync (PR #10, 2026-10-14) took hours
because this repo had been seeded from a ZIP and shared no git history with
upstream. That is fixed: the merge commit `0f5c3c94` links the histories, so
every later sync is an ordinary three-way merge. Follow the fast path; read the
rest only when a step surprises you.

Repository topology:

| Name | What it is | Branch |
|---|---|---|
| `origin` | this repo, `freeforall1932-design/odysseus-fork-but-api-dev` | `main` (integration branch; PRs target it) |
| `source` | the fork `freeforall1932-design/odysseus-fork-but-api`, updated from upstream by the owner | `dev` |
| upstream | `odysseus-dev/odysseus` (the fork's parent) | `dev` (`main` is release-curated there) |

The fork is normally a pure mirror of upstream `dev`. Merge from `source/dev`,
not from upstream directly, so the owner controls which upstream state arrives.

Since PR #10 the merge is automated (next section). The manual fast path is
what the automation runs; you need it when the workflow reports a conflict or
when you want to drive a sync by hand.

## Automation

`.github/workflows/upstream-sync.yml` runs `.github/scripts/upstream_sync.py`
on every push to `main`, daily at 02:17 UTC, on manual dispatch (Actions ->
"Upstream sync" -> Run workflow) and on a `repository_dispatch` event of type
`upstream-sync`. Each run fetches `source/dev`, finds the merge base with
`origin/main` and ends in one of these states:

| State | What the run does |
|---|---|
| `main` already contains the upstream tip | Nothing to merge. Closes a leftover sync PR, deletes the `sync/upstream` branch if only the bot committed to it, closes an open conflict issue. |
| Clean merge | Rebuilds `sync/upstream` = `origin/main` + merge of `source/dev` (`main` is the first parent), runs the static quick gate (`--check-only`, see Verification), pushes with `--force-with-lease`, opens **one** PR against `main` or refreshes the existing one in place (title `chore(sync): ...`, body in the PR template format, label `upstream-sync`, `Part of #<tracking issue>`). If the previous run produced the same tree, nothing is pushed. |
| Conflict | Aborts the merge, pushes nothing, opens or updates **one** issue (labels `upstream-sync` + `merge conflict`) listing the conflicted files with their manifest rule from the table below and the exact commands to resolve locally. A stale sync PR is closed because it can no longer merge. The run ends green with a warning annotation; the issue is the signal. |
| Refusal | Red run with an `::error::` annotation: no merge base (histories disconnected, see Appendix A), or `sync/upstream` carries commits the bot did not author (merge or delete that branch). |

What it never does: push to `main`, rewrite downstream commits, resolve a
conflict by itself, or overwrite a human's commit on `sync/upstream`. Review and
merge the PR as usual; CI runs on it like on any other PR.

One-time setup:

1. Merge PR #10 with **Create a merge commit**. It carries the merge commit that
   links the histories; until it is on `main` every run stops with "share no
   history". Never squash or rebase a sync PR (that drops the link and the next
   sync conflicts everywhere). Keep "Allow merge commits" enabled in Settings ->
   General.
2. Add the repository secret `UPSTREAM_SYNC_TOKEN`: a fine-grained personal
   access token (Settings -> Developer settings -> Fine-grained tokens),
   resource owner = the repository owner, repository access = only this
   repository, permissions **Contents: read and write**, **Pull requests: read
   and write**, **Issues: read and write**, **Workflows: read and write**
   (Metadata is added automatically). Reasons: pull requests opened with the
   default `GITHUB_TOKEN` do not trigger CI, and that token cannot push commits
   that touch `.github/workflows/*`, which upstream changes regularly. Note the
   expiry date; when the token expires the workflow silently falls back to
   `GITHUB_TOKEN` and says so in the PR body and in a warning annotation.
3. Optional, for hands-off merging: repository variable
   `UPSTREAM_SYNC_AUTO_MERGE` = `true`, plus Settings -> General -> "Allow
   auto-merge", plus a branch protection rule or ruleset on `main` with required
   status checks (the pytest shards, Secret scan, Workflow security, PR
   description check). GitHub refuses auto-merge without required checks; the
   run then logs a warning and leaves the PR for a human. Auto-merge is skipped
   when the static quick gate failed.
4. First run: Actions -> "Upstream sync" -> Run workflow with `dry_run` = true,
   then read the job summary. A dry run pushes and opens nothing.

Day to day:

- New upstream commits arrive when the fork is updated (`gh repo sync`, see
  below, or GitHub's "Sync fork" button); the next scheduled run picks them up.
  For an immediate run, dispatch the workflow by hand or send
  `gh api repos/freeforall1932-design/odysseus-fork-but-api-dev/dispatches -f event_type=upstream-sync`
  (a workflow in the fork can do that on push with a token that has
  Contents: write on this repository).
- Every push to `main` rebuilds the open sync PR on top of it, so downstream
  work never makes the sync PR stale; the PR number stays the same.
- To pause: close the sync PR. It is not reopened until `main` or upstream
  moves. To stop: disable the workflow in the Actions tab. GitHub also pauses
  schedules after 60 days without repository activity; re-enable from the same
  tab.
- A conflict issue means a 15-30 minute manual job: run the commands in the
  issue (the fast path below with the upstream commit filled in), open a normal
  PR, merge it with a merge commit. The next run closes the issue.
- The PR author is the token's owner, so the PR description and title checks
  run and pass on the generated body. A sync PR is UI-sensitive by nature
  (upstream touches `static/`), so the description bot leaves its advisory
  screenshot comment; that is expected.

Local use: `python .github/scripts/upstream_sync.py --dry-run` performs the
same analysis on your machine (needs `gh auth login` for the PR/issue lookups;
`--offline` skips them) and leaves `sync/upstream` checked out for inspection.
`--check-only` runs the static quick gate against the working tree.
`tests/test_upstream_sync_script.py` exercises the script end to end against
throwaway local repositories.

Known limits: conflicts are not auto-resolved (the hot spots in the manifest
need judgment; scripting the re-application of the manifest deltas is the
natural next step), and the static gate is a smoke test, not a substitute for
CI on the PR.

## Fast path

```bash
cd /path/to/odysseus-fork-but-api-dev

# 0. History + remote. Arena sandboxes clone shallow; a shallow clone has no
#    merge base and `git merge` would refuse with "unrelated histories".
git fetch --unshallow origin 2>/dev/null || git fetch origin
git remote add source https://github.com/freeforall1932-design/odysseus-fork-but-api.git 2>/dev/null
git fetch source --no-tags

# 1. Orientation: what is new, and what must survive.
BASE=$(git merge-base HEAD source/dev); echo "last synced upstream commit: $BASE"   # must not be empty
git log --oneline "$BASE..source/dev" | wc -l                     # new upstream commits
git diff --stat "$BASE" source/dev | tail -1                      # upstream churn
git diff --name-only "$BASE" HEAD                                 # downstream delta; compare with the manifest below
git diff "$BASE" HEAD > /tmp/downstream.patch                     # exact downstream changes, per file, for reference
comm -12 <(git diff --name-only "$BASE" HEAD | sort) \
         <(git diff --name-only "$BASE" source/dev | sort)        # files changed on BOTH sides = only possible conflicts

# 2. Dry run without touching the working tree (git >= 2.38). Exit 1 = conflicts, and it lists them.
git merge-tree --write-tree --name-only HEAD source/dev

# 3. Merge.
git merge --no-ff --no-commit source/dev
git diff --name-only --diff-filter=U                              # conflicted files -> "Conflict playbook" below
# resolve, then `git add` each file

# 4. Verify (commands in "Verification"), then commit with the message template, push, open the PR.
```

Budget: 15-30 minutes when only the known hot spots conflict. If
`git merge-base HEAD source/dev` prints nothing, the histories were disconnected
again; see Appendix A.

## Downstream manifest

`git diff --name-only source/dev HEAD` must list exactly these files after a
sync (plus anything added downstream since this table was written). Anything
else means upstream content was dropped or downstream content leaked.

| File | Downstream change | Resolution rule when it conflicts |
|---|---|---|
| `routes/provider_routes.py`, `routes/auto_routes.py`, `src/auto_router.py`, `src/council.py`, `src/provider_presets.py`, `static/js/providerHub.js`, `website/providers-auto-council.md`, `tests/test_auto_router.py`, `tests/test_council.py`, `tests/test_provider_presets.py`, `tests/test_provider_and_auto_routes.py` | Downstream-only: provider onboarding, Auto routing, Council UI. | Cannot conflict unless upstream adds a file at the same path (add/add). Then read both; keep the downstream file only if upstream's is unrelated, otherwise merge deliberately. Always run the symbol check below: these modules import upstream code. |
| `app.py` | Four lines after `app.include_router(setup_model_routes(model_discovery))`: import and include `setup_provider_routes()` and `setup_auto_routes(skills_manager)`. | Take upstream's file, re-insert the block right after the model routes include. `skills_manager` must still be defined above it. |
| `static/index.html` | One line: `<script type="module" src="/static/js/providerHub.js"></script>` after `settings.js`, before `assistant.js`. `app.js` must stay last. | Take upstream's script tags (they carry `?v=` cache-busters), re-insert the line. |
| `static/sw.js` | `'/static/js/providerHub.js'` in `PRECACHE` after the `settings.js` entry; `CACHE_NAME` bumped. | Take upstream's `PRECACHE`, re-add the entry. Take upstream's `CACHE_NAME` and bump it again (for example append `-providerhub`): the file's own rule is "bump whenever the precache list changes". |
| `static/js/chat.js` | (a) `detectWorkspaceAgentIntent()` helper near the top, a mirror of upstream's Agent-mode heuristic; (b) the Auto pre-send block (~25 lines ending in `window.odysseusAuto.beforeSend(...)`) immediately before `const messageInput = el('message');`. | Keep upstream's Agent-mode block (from `const _messageText = String(msg \|\| '');` through the `workspaceAgentIntent` assignment) byte-for-byte. If upstream changed any regex there, copy the new literals into the helper. Never write the literal text `const workspaceAgentIntent` in a comment: upstream's guard test reads the first line that contains it. Enforced by `tests/test_chat_route_tool_policy.py::test_frontend_generic_web_prose_does_not_grant_shell_authority` (upstream) and `tests/test_provider_and_auto_routes.py::test_auto_hint_mirrors_agent_mode_workspace_heuristic` (downstream, fails until helper and block match). |
| `routes/model_routes.py` | `"host.docker.internal"` added to `_LOCAL_HOSTS`; the Anthropic probe uses `_safe_build_headers(api_key, base)` so Chatbox's `Instance-Id` reaches `/v1/models`; first-endpoint default assignment falls back to a pinned model when the probe returned none. | Re-add all three hooks. |
| `src/chatbox_ai.py`, `docs/CHATBOX_AI.md`, `tests/test_chatbox_ai.py`, `tests/test_chatbox_license_store.py`, `tests/test_chatbox_routing.py`, `tests/test_provider_chatbox_routes.py`, `tests/test_provider_hub_chatbox_js.py` | Downstream-only **Chatbox AI provider**: license activation, encrypted license storage, model catalog, gateway routing and tests. | Cannot conflict unless upstream adds a file at the same path (add/add). Keep ours; they import upstream modules (`core.database`, `src.provider_presets`, `static/js/providerHub.js`). |
| `tests/test_model_routes.py` | `TestClassifyEndpoint::test_docker_host_gateway_is_local`. | Keep the test. |
| `tests/test_tls_overrides_scope.py` | `routes/provider_routes.py` added to `ALLOWED_CALLERS` (it calls `llm_verify()`); docstring says "known entry points". | Re-add the entry. |
| `tests/test_docs_no_orphan_images.py` | `"providers-auto-council.md"` in `PUBLIC_GUIDES`. | Re-add. |
| `README.md` | Nav links to `website/providers-auto-council.md` and `docs/CHATBOX_AI.md`, plus the Chatbox AI feature bullet. | Re-add the links and bullet in upstream's nav/features. |
| `core/database.py` | `from sqlalchemy.orm import declarative_base, declared_attr` (upstream still uses the deprecated `sqlalchemy.ext.declarative`) plus the downstream-only `ChatboxAILicense` table (encrypted license key/instance/detail; created by `create_all`). | Keep ours; if upstream fixes the import, take upstream's. Keep `ChatboxAILicense` and do not let a table migration drop it. |
| `routes/skills_routes.py` | `body.model_dump(exclude_none=True)` instead of `body.dict(...)`. | Same. |
| `.gitleaks.toml` | Upstream's file plus a second `[[allowlists]]` block for the historical `sk-LEAKTEST-123456` literal. | Keep every upstream block and the downstream block appended. Both are needed: upstream's for `THIRD_PARTY_PROVENANCE.json`, ours because `gitleaks git` scans history. |
| `audit.md`, `SESSION_HANDOFF.md`, `WORKLIST.md`, `UPSTREAM_SYNC.md` | Downstream documents. | Cannot conflict. |
| `.github/workflows/upstream-sync.yml`, `.github/scripts/upstream_sync.py`, `tests/test_upstream_sync_script.py` | The sync automation (see "Automation"). | Downstream-only. If upstream adds a file at the same path, keep ours and rename only if the two really collide. The script's symbol and integration-point lists mirror this table and the Verification section: update them together. |

Chatbox AI also touches upstream-owned routing files. Take upstream's version and re-apply only these hooks:
`src/endpoint_resolver.py` (`_anthropic_api_root` strips the Chatbox Anthropic gateway's `/v1`;
`build_headers` merges `_chatbox_extra_headers`), `src/llm_core.py` (`_detect_provider` maps
`/gateway/anthropic/` to `"anthropic"`; `_provider_label` names Chatbox AI), and
`static/js/providerHub.js` (license card, unsupported badges, per-gateway connect). The full list and
wire contract are in `docs/CHATBOX_AI.md`.

Upstream integration points the downstream UI depends on (check these if
upstream reworked the model picker or settings):

- DOM: `#model-picker-menu`, `#model-picker-list`, `#model-picker-add-models-btn` (defined in `static/index.html`, driven by `static/js/modelPicker.js`).
- Globals: `window.modelsModule` (set in `static/js/models.js`); `window.showToast` is optional and guarded.
- Upstream APIs: `/api/model-endpoints`, `/api/skills`.
- Python symbols: listed in the symbol check below.

## Conflict playbook

Work through `git diff --name-only --diff-filter=U` using the table above. The
quickest way to see what must be restored in a file is the downstream patch
from step 1: `grep -n -A40 'a/static/sw.js' /tmp/downstream.patch`. To see how
the same file was resolved last time: `git show <last merge commit> -- <file>`.

General rules:

- Take upstream's version of anything upstream owns, then re-apply the small downstream delta on top. Do not keep stale downstream copies of upstream code.
- Prefer byte-identical upstream blocks wherever a downstream feature only needs to *call* them (that is why `chat.js` has a mirror helper instead of an edited upstream block): byte-identical blocks merge cleanly next time.
- No `--allow-unrelated-histories`, no rebase of `main`, no force-push to `main`. `git merge --abort` is always available before the commit.

If upstream deleted or renamed something a downstream module imports, find
where it went with `git log -S'<symbol>' --oneline "$BASE..source/dev"` and
update the import in the downstream module.

## Verification

Environment (a fresh sandbox has nothing installed; `.venv` and `node_modules`
are git-ignored):

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest-xdist        # xdist is not in requirements.txt
npm ci --no-audit --no-fund                          # acorn for the JS tests; Playwright browsers cannot be downloaded in the sandbox
```

Quick gate (about a minute). Run before committing:

```bash
grep -rn -E '^(<<<<<<< |>>>>>>> )' --exclude-dir=.git --exclude-dir=node_modules . ; echo "markers exit=$? (1 = none left)"

# Static quick gate, the same one the automation runs after its merge: the upstream
# symbols downstream modules import, the downstream lines inside upstream-owned
# files (manifest rows), every precached asset and index.html script exists,
# `node --check` on the touched JS, `py_compile` on the downstream modules.
# All rows must say PASS. The lists live at the top of the script.
python .github/scripts/upstream_sync.py --check-only

# Downstream suites + upstream contracts on the files we touch (about 450 tests, ~10 s).
# The deselected test needs a Playwright browser, which the sandbox cannot download.
python -m pytest -q -p no:cacheprovider \
  tests/test_auto_router.py tests/test_council.py tests/test_provider_presets.py tests/test_provider_and_auto_routes.py \
  tests/test_chat_route_tool_policy.py tests/test_frontend_module_graph.py tests/test_model_routes.py \
  tests/test_docs_no_orphan_images.py tests/test_tls_overrides_scope.py tests/test_publication_plan_b.py \
  tests/test_upstream_sync_script.py \
  --deselect tests/test_publication_plan_b.py::test_browser_publication_behaviors

# Manifest: before the commit compare the index, after the commit compare HEAD.
git diff --cached --name-only source/dev        # pre-commit
git diff --name-only source/dev HEAD            # post-commit
```

Runtime check (the PR template asks for it; takes two minutes):

```bash
APP_BIND=0.0.0.0 APP_PORT=7011 DATABASE_URL=sqlite:////tmp/ody/odysseus.db python app.py   # mkdir -p /tmp/ody first
curl -s -o /dev/null -w '%{http_code}\n' localhost:7011/api/providers/presets   # 401 = registered and behind auth (404 = route lost)
curl -s -o /dev/null -w '%{http_code}\n' localhost:7011/api/auto/pool           # 401
curl -s localhost:7011/static/sw.js | grep -n 'CACHE_NAME = \|providerHub'
curl -s localhost:7011/static/index.html | grep -n providerHub
```

ChromaDB errors at startup are expected without that service.

Full suite (optional locally; CI runs it in four shards with bubblewrap and
browsers, which the sandbox lacks):

```bash
python -m pytest -q -rf -p no:cacheprovider -n 2 --dist loadfile      # ~11 min on 2 cores, ~26,600 tests
```

Do not use `-x`/`--maxfail`: the sandbox has about 70 failures that are
environment-only and they stop the run early. Known classes: Playwright/Chromium
(`*_browser_suite`, `test_document_rich_*`, `test_css_computed_style_snapshot`,
`test_frontend_foundation_offline_js`), bubblewrap containment
(`test_exact_approval_ungranted_process`, `test_wave3_local_control`,
`test_workspace_confine`, `test_execution_filesystem_boundary`), tmux
(`test_live_fallback_round_attribution`, cookbook launch tests), ffmpeg
(`test_inspect_media_tool`). `pytest-timeout` is not installed, so `--timeout`
errors out.

To prove a failure is environmental rather than merge-introduced, run the same
files against pristine upstream in a worktree and compare:

```bash
FILES="tests/test_a.py tests/test_b.py"
git worktree add --detach /tmp/upstream-dev source/dev && ln -s "$PWD/node_modules" /tmp/upstream-dev/node_modules
(cd /tmp/upstream-dev && python -m pytest $FILES -q -p no:cacheprovider -n 2 --dist loadfile -rf | grep '^FAILED' | sed 's/ - .*//' | sort -u) > /tmp/up.txt
python -m pytest $FILES -q -p no:cacheprovider -n 2 --dist loadfile -rf | grep '^FAILED' | sed 's/ - .*//' | sort -u > /tmp/ours.txt
comm -13 /tmp/up.txt /tmp/ours.txt           # anything printed here is ours to fix
git worktree remove --force /tmp/upstream-dev
```

## Commit, push, pull request

Merge commit message template (the subject is also a fine PR title once
prefixed, see below):

```
Merge upstream fork odysseus-fork-but-api (dev @ <short sha>) into main

Sync with https://github.com/freeforall1932-design/odysseus-fork-but-api.
<N> upstream commits, <M> files, since <previous upstream sha>.

Conflicts: <files, one line each on what was kept>.
Downstream features preserved: provider onboarding, Auto routing, Council UI,
host.docker.internal, SQLAlchemy/Pydantic deprecation fixes, audit docs.
Verification: <quick gate result, app boot, any full-suite note>.
```

Push to your working branch and open the PR against `main`. The repo's checks
enforce the following; getting them right the first time saves a round trip:

- **Title** must be Conventional Commits: `chore(sync): merge upstream fork odysseus-fork-but-api (dev @ <sha>) into main`.
- **Description** (`.github/scripts/check-pr-description.js`): `## Summary` with at least 20 characters; `## Linked Issue` containing `#<number>`; at least one `- [x]` under `## Type of Change`; the `- [x] I searched ...` checklist box ticked; `## How to Test` with at least 30 characters. Keep the template's headings.
- **Linked issue**: open a tracking issue first (`gh issue create --label enhancement`). The issue check requires the feature template's sections: `### Area` (a value from the template list, "Other" works), `### Problem or Motivation` and `### Proposed Solution` each at least 20 characters. Issue #9 is a model.
- A sync PR is always classified **UI-sensitive** (upstream touches `static/`). The bot then leaves an advisory comment about screenshots; it does not fail the check. State in the Visual section that rendering changes are upstream's own and that the downstream resolution adds no rendering.
- **gitleaks** scans the entire history with the repo's `.gitleaks.toml`. New downstream test placeholders must be letters-only or contain `fake`/`testing`/`example`, otherwise the `generic-api-key` rule fires (entropy >= 3.5 plus a keyword like `key =`). If it fails, the finding is redacted in the log; test the suspect string against the rule locally (Appendix B).

Sandbox limits that cost time last sync:

- `gh run view --log` fails from the sandbox (the log host is not reachable). Use annotations instead: `gh api repos/<owner>/<repo>/check-runs/<job-id>/annotations` with the job id from `gh pr checks <n>`'s URLs, and `gh api repos/<owner>/<repo>/actions/jobs/<job-id> --jq '.steps[] | "\(.conclusion)\t\(.name)"'` for the failing step.
- `gh pr edit` can fail with a GraphQL "Projects (classic)" deprecation error. Use the REST API: `gh api -X PATCH repos/<owner>/<repo>/pulls/<n> -f title='...'` or `-F body=@file.md`.
- Reachable: `github.com`, `api.github.com`, `codeload.github.com`, `pypi.org`, `registry.npmjs.org`. Not reachable: release assets (`release-assets.githubusercontent.com`, so no gitleaks binary), Playwright browser downloads, Go module proxy.
- A restored Arena sandbox can come back with `.git` reset to the session's base commit, the merged files sitting as uncommitted changes, the `source` remote gone, and directories named `build/` (for example `static/js/editor/build/`) stale, because snapshots exclude them. The pushed branch is the truth: `git fetch origin <branch> && git reset --hard origin/<branch> && git clean -fd`, then re-add the `source` remote (fast path step 0). Compare first if unsure: `cp .git/index /tmp/idx && GIT_INDEX_FILE=/tmp/idx git add -A && git diff --stat $(GIT_INDEX_FILE=/tmp/idx git write-tree) origin/<branch>`.
- Lint workflows locally with the same tools as CI: `pip install zizmor==1.25.2` works; the actionlint binary cannot be downloaded (release asset), but `npm install actionlint` in a scratch directory gives an older WASM build that still catches syntax and expression errors (it does not know the `vars` context or recent runner labels; ignore those two findings).

## Updating the fork from upstream first (optional)

The owner normally does this. If asked:

```bash
gh api repos/freeforall1932-design/odysseus-fork-but-api/compare/odysseus-dev:dev...dev --jq '"fork is ahead \(.ahead_by), behind \(.behind_by)"'
gh repo sync freeforall1932-design/odysseus-fork-but-api --branch dev     # fast-forwards the fork from odysseus-dev/odysseus
```

`gh repo sync` refuses if the fork has its own commits; do not add `--force`
without the owner's say-so, it discards them.

## Appendix A: recovering from disconnected histories

Needed only if `git merge-base HEAD source/dev` is empty (for example someone
re-created the repo from an archive again). This is what the first sync did.

1. Find the upstream commit the snapshot was taken from: the one with the fewest differing files.
   ```bash
   SNAP=<commit that imported the snapshot>
   for c in $(git log --format=%h source/dev --since='<a few weeks before the import>' --until='<import date>'); do
     echo "$(git diff --name-only $c $SNAP | wc -l) $c $(git log -1 --format='%ad %s' --date=short $c | cut -c1-70)"
   done | sort -n | head -5
   ```
   Expect a handful of files for the best candidate (first sync: `2992bf6d`, 5 files).
2. Graft the snapshot commit onto that upstream commit, locally and temporarily:
   `git replace --graft $SNAP <its existing parent(s)> <upstream commit>`.
   `git merge-base HEAD source/dev` now returns the upstream commit.
3. Merge as in the fast path. Only files changed on both sides can conflict.
4. After committing, `git replace -d $SNAP`. The merge commit's two parents keep
   the histories linked; the replace ref is never pushed.

## Appendix B: testing a string against gitleaks' generic-api-key rule

The binary cannot be downloaded in the sandbox, but the ruleset can:

```bash
curl -fsSL https://codeload.github.com/gitleaks/gitleaks/tar.gz/refs/tags/v8.30.1 | tar -xz -C /tmp gitleaks-8.30.1/config/gitleaks.toml
```

A `key = "<value>"` line is reported when the value matches
`[\w.=-]{10,150}`, has Shannon entropy >= 3.5, is not letters-only
(`^[a-zA-Z_.-]+$` is allowlisted) and contains none of the rule's stopwords
(`fake`, `testing`, `example`, ...). Pin the version to the one in
`.github/workflows/secret-scan.yml` (`GITLEAKS_VERSION`).

## Sync log

Add a row per sync. "Upstream" is the `source/dev` commit merged.

| Date | Upstream | Merge commit | PR | Notes |
|---|---|---|---|---|
| 2026-10-14 | `86b886c6` | `0f5c3c94` | #10 | First sync. Histories linked by grafting `9864cd0f` onto `2992bf6d`. Conflicts: `sw.js`, `index.html`, `chat.js` (upstream rewrote the workspace-intent heuristic; mirror helper + guard test added). Also cleared the pre-existing gitleaks failure (`sk-LEAKTEST-123456` placeholder). |
