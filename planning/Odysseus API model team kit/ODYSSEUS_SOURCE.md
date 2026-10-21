# Odysseus source pointer (the program files live in their own repo)

> **What this file is:** an address card, not a copy of the program.
>
> On **2026-10-17** the owner pointed this project at
> <https://github.com/freeforall1932-design/odysseus-fork-but-api-dev>
> as "the Odysseus aka the program file" source. This file records that
> address, the exact version inspected, and **exactly which files this
> project needs from that repo, and for what**.
>
> The whole Odysseus program is **not** copied into `dionysus`. It stays
> in its own repository and is cloned as its own project wherever it is
> studied, edited, or installed. What was pulled into this folder beside
> `README.md` is only this pointer. If the owner instead wants a real
> vendored copy or a git submodule inside `dionysus`, name that as its
> own task — it has size, licence, and sync consequences (below) that
> should be chosen on purpose, not by accident.
>
> This pointer does **not** unblock the missing AI Team Kit files, does
> **not** decide that Odysseus wins the Step 3 harness comparison, and
> does **not** authorize installing or running Odysseus. The owner names
> one task at a time (see `README.md` in this folder).

---

## 1. Exact source inspected (verified 2026-10-17; pin updated later the same day)

First verified in the 2026-10-17 session by GitHub metadata (`gh repo view`,
branch/commit APIs) and a read-only shallow clone in scratch space at
`c35a9256…`. Later that day the owner pointed out that `main` had moved, so
the new head was cloned and compared with the old pin before this file was
updated. Scratch clones were discarded. Nothing was installed, built, run,
or tested — only listed, read, and diffed.

| Fact | Value at inspection |
|---|---|
| Repository | `freeforall1932-design/odysseus-fork-but-api-dev` |
| URL | https://github.com/freeforall1932-design/odysseus-fork-but-api-dev |
| Default branch | `main` |
| Pinned commit (use this, not "latest") | `951d57db0e8758eadc3baed4af962860132a5f51` |
| That commit | 2026-10-17 13:20 +07, merge of that repo's PR #15 (`chore(sync): merge upstream fork odysseus-fork-but-api (dev @ 9712a540) into main`); its parents are the previous pin `c35a9256…` and sync commit `8c5e9e70…` |
| Previous pin | `c35a9256f88b2d166cd49297b79efe3e46a40897` (2026-10-14 PR #10 merge). It was `main` when first inspected on 2026-10-17, then superseded about ten minutes later by the PR #15 merge above. Kept here only as history and as the compare base — do not use it as the current pin. |
| Latest GitHub release | None (`latestRelease: null`) — the commit SHA is the version anchor |
| `HARNESS_VERSION` file | `0.20.19` |
| Licence (repo metadata + `LICENSE`) | **AGPL-3.0-or-later** (GitHub key `agpl-3.0`) |
| Size | GitHub disk usage reported 59,390 KB; fresh checkout at the current pin ~53 MB, 2,647 tracked files (1,457 of them under `tests/`) |
| Main languages | Python, JavaScript, CSS, HTML (plus shell/PowerShell/Swift extras) |
| Real entry points | `app.py` (FastAPI app), `setup.py` (first-run setup), `requirements.txt`; native run command in `website/setup.md` |
| GitHub "fork?" flag | `isFork: false`, no parent — see topology below before calling it a GitHub fork |

### Repository topology (from that repo's own docs, read at the pin)

- **This repo** (`odysseus-fork-but-api-dev`, branch `main`) is the
  integration repo holding downstream changes. Per its `UPSTREAM_SYNC.md`
  and `SESSION_HANDOFF.md`, it was originally seeded from a ZIP, then its
  history was linked to upstream by merge commit `0f5c3c94` in its PR #10
  (2026-10-14). That is why GitHub does not mark it as a fork object.
- Its upstream feed is an intermediate owner fork,
  `freeforall1932-design/odysseus-fork-but-api` (branch `dev`), which
  mirrors upstream `odysseus-dev/odysseus` (branch `dev`; upstream `main`
  is described as release-curated).
- Syncing is automated in that repo (the `upstream-sync.yml` workflow
  under its `.github/workflows/` folder
  + its `upstream_sync.py` helper script): it opens/refreshes a sync PR and
  never pushes to `main` by itself. Sync PRs there must be merged with a
  merge commit — never squash/rebase them (that would break the history
  link). All of that belongs to work **in that repo**, not in `dionysus`.

### Clone trap — read before ever cloning

The fork's own `README.md` and `website/setup.md` quick-starts still say
`git clone https://github.com/odysseus-dev/odysseus.git` — that clones
**upstream**, not the owner's program source. For this project, when an
owner-named task actually needs the code, clone the owner's repo and pin
the commit, for example in scratch space or on the target machine
(**outside** `dionysus`):

```bash
git clone https://github.com/freeforall1932-design/odysseus-fork-but-api-dev.git
cd odysseus-fork-but-api-dev
git checkout 951d57db0e8758eadc3baed4af962860132a5f51
git rev-parse HEAD   # must print the same SHA
```

Notes: a shallow clone (`--depth 1`) is fine for read-only evaluation but
has no merge base — never use one for sync/edit work in that repo (its
`UPSTREAM_SYNC.md` says to unshallow first). If `main` has moved past the
pin when a future task runs, do not silently float to latest: read that
repo's sync log/commits, then update the pin in this file deliberately,
in the same session, with the date and reason.

---

## 2. Why the program is not copied into this folder

- **Size and shape:** ~53 MB / 2,647 files of application code, tests,
  media and docs would land inside a dotfiles fork whose rule is "owner
  additions live under `workbench/`, upstream untouched". A dead copy
  would also go stale the moment the Odysseus repo's daily sync moves —
  exactly what happened between the two pins recorded in Section 1.
- **Licence:** Odysseus is AGPL-3.0-or-later, with third-party material
  inventoried in its `THIRD_PARTY_PROVENANCE.json`, `ACKNOWLEDGMENTS.md`
  and `licenses/`. Keeping it as a separate repo keeps those obligations
  attached to their own history instead of smearing them across
  `dionysus`. No Odysseus code may be copied into the kit until a named
  task has done the licence check for that specific reuse.
- **It only runs whole:** cherry-picking "the program file" does not
  work. The app needs its full tree (`app.py`, `core/`, `routes/`,
  `services/`, `src/`, `static/`, `resources/`, `config/`, requirements,
  and a locally created `.env` + data directory). The honest unit is
  "clone the repo at the pinned commit", on the machine that will run it.
- **This repo's own pattern:** the workbench already points at other
  projects instead of copying them (see `workbench/projects/` in the
  repository root). A pointer with a pinned commit is the local custom.

---

## 3. What this project needs from that repo — the file list

"Need" below means **need to read at the pinned commit** when the matching
owner-named task runs. Section 3.5 is the exception: an actual install
needs the whole clone, on the target machine, never committed here.
Every path below was confirmed to exist at the pin on 2026-10-17.

### 3.0 Needed inside `workbench/projects/ai-team-kit/` — done by this file

| File here | Why |
|---|---|
| This `ODYSSEUS_SOURCE.md` beside `README.md` | The address, pin, licence, traps, and this needs-list. Keep it truthful; update it in the session that changes anything about the Odysseus source. |

No other Odysseus file is needed inside `dionysus` today.

### 3.1 Identity, licence, security, and downstream truth (read first in Steps 1a/3)

| File in the Odysseus repo | Needed for |
|---|---|
| `README.md` | What the program claims to be; feature list; quick starts (with the clone trap above). |
| `LICENSE`, `ACKNOWLEDGMENTS.md`, `THIRD_PARTY_PROVENANCE.json`, `licenses/` | The licence check before any reliance, reuse, or redistribution decision. AGPL terms attach to network use of modified versions — read, do not paraphrase from memory. |
| `SECURITY.md`, `THREAT_MODEL.md` | Its own security posture; the app has powerful shell/file tools by design. |
| `SESSION_HANDOFF.md`, `WORKLIST.md`, `audit.md` | **Read before any install or exposure.** At the pin, `WORKLIST.md` still lists audit findings as pending owner approval (auth/session file permissions, a token-chat DNS-rebinding report, first-admin setup exposure, a fail-open privilege check, and unsandboxed agent shell/filesystem tools as documented residual risk). Whether any of that changed after the pin must be re-checked in that repo at task time. Parts of these files are dated 2026-10-05 and partly stale (for example an old branch name) — treat them as that repo's records to verify, not as current proof either way. |
| `UPSTREAM_SYNC.md` | Topology, the downstream-change manifest (what makes this repo different from upstream), verification commands, and the never-squash-a-sync-PR rule. |
| `HARNESS_VERSION` | The repo's own version string at the pin (`0.20.19`); the commit SHA remains the real anchor. |

### 3.2 Native install path (owner decision: native, not Docker)

At the pin, `website/setup.md` section "Native Linux / macOS" gives:
Python 3.11+, a virtualenv, `pip install -r requirements.txt`,
`python setup.py`, then
`python -m uvicorn app:app --host 127.0.0.1 --port 7000`.
(`tmux` is only needed for its Cookbook local-model background work; the
guide notes small hosts can connect to API/remote model servers instead —
which matches this project's cloud-API-only rule. The Docker quick start
uses port 7011; do not mix the two recipes.) **These are facts read from
the guide, not steps anyone has run for this project.**

| File in the Odysseus repo | Needed for |
|---|---|
| `website/setup.md` (especially Native Linux/macOS, Security Notes, Configuration, Built-in MCP servers) | The native recipe, exposure warnings (`AUTH_ENABLED`, loopback binding), and config pointers. |
| `website/configuration-reference.md` | The full generated list of settings the code reads. |
| `.env.example` | The settings **template only**. A real `.env` is created owner-local at install time and is never committed to either repo. |
| `requirements.txt`, `requirements-optional.txt` | Core vs optional Python deps. Note the guide's warning: requirements are intentionally unpinned, so two installs can differ; a lock snapshot is an install-task decision. |
| `setup.py`, `app.py` | The first-run setup script and the app entry point the native command serves. Read before running — never blind-run. |
| `pyproject.toml`, `tests/README.md`, `requirements-dev.txt` | How its tests are organised/run, for any future task that edits or verifies that repo. |
| `install-service.sh`, `odysseus-ui.service` | Only if a future native task chooses a systemd-service install. Optional; decide at design time. |

### 3.3 Providers, Auto pool, and Council (this repo's downstream additions)

Per `UPSTREAM_SYNC.md`'s downstream manifest and
`website/providers-auto-council.md`, these are downstream-only pieces on
top of upstream — directly relevant to this project's model-source and
council/persona questions, as **documentation and code to evaluate** in
Steps 1–3. Nothing below was executed in this session.

| File in the Odysseus repo | Needed for |
|---|---|
| `website/providers-auto-council.md` | The plain description: provider onboarding by pasting a key (presets listed there include OpenRouter, Google Gemini, NVIDIA NIM, Groq, Mistral, Cerebras, a custom OpenAI-compatible URL, and more), an Auto pool with a router model and a hard keep-local mode, and a Council (fan-out/debate/verify) with optional personas and a separate chair seat. Also states its deliberate limits (for example: never rewrites a prompt to dodge a refusal). Free-tier limits are **not** established by this doc — official lookups still required. |
| `src/provider_presets.py`, `routes/provider_routes.py` | How provider presets and key-check/model-list calls actually work. |
| `src/auto_router.py`, `routes/auto_routes.py` | The Auto pool/router and the council HTTP surface. |
| `src/council.py` | Council modes, persona handling, chair behaviour. |
| `static/js/providerHub.js` | The provider/Auto/Council UI (with small hooks in `static/js/chat.js`, `static/index.html`, `static/sw.js`, and the four routing lines in `app.py` — see the downstream manifest before touching any of them). |
| `tests/test_provider_presets.py`, `tests/test_auto_router.py`, `tests/test_council.py`, `tests/test_provider_and_auto_routes.py` | The downstream test suites (the doc claims 175 + 25 related tests, no network — a claim to re-measure if a task ever depends on it). |
| `specs/model-providers/_readme.md`, then per provider as needed (`openai-compatible.md`, `nvidia-nim.md`, `google.md`, `openrouter.md`, …) | What Odysseus itself records about each provider's API shape. Useful inside Odysseus; it does not answer what the AI Team Kit's picker supports (that is Step 0/2 on the kit). |
| `specs/llm-models.md`, `specs/settings-admin.md` | Model/endpoint behaviour and admin/settings surfaces for any router-integration design. |

### 3.4 MCP, shell, skills, and external-agent surfaces

| File in the Odysseus repo | Needed for |
|---|---|
| `specs/shell-mcp.md` | The map of shell routes (admin-only, powerful by design), background jobs, configured MCP servers, transports, and where MCP tool exposure/security lives. Read before believing any "Odysseus gives us MCP" summary. |
| `website/setup.md` "Built-in MCP servers" + `mcp_servers/email_server.py`, `image_gen_server.py`, `memory_server.py`, `rag_server.py` | The built-in MCP servers it ships. |
| `routes/mcp/mcp_routes.py`, `src/mcp_manager.py`, `src/builtin_mcp.py`, and the `odysseus-mcp` launcher | How MCP servers are configured and run — the code behind the spec. |
| `specs/memory-skills.md`, `docs/skills-lifecycle.md` | How skills (`SKILL.md` under its data dir) and memory actually work there, including GitHub skill import safety rules. |
| `docs/skills-audit-architecture.md`, `docs/skills-audit-second-review.md`, `services/skills/` (`evaluation.py`, `audit_workflow.py`, `agent_runner.py`, `job_coordinator.py`, `publication.py`, `model_selection.py`, `dependencies.py`, `prompts.py`), `routes/skills_routes.py` | Added/reshaped by the 2026-10-17 sync's skills evaluation/audit refactor. Needed before relying on any skill test/audit behaviour at the current pin; the spec remains the entry point. |
| `specs/agent-tools.md`, `specs/integrations.md` | Agent tool behaviour and the scoped external-agent HTTP surface (`/api/codex/*`, API tokens with scopes; Claude/Codex bundles under `integrations/`). |

### 3.5 Needed only at real install time (never committed to `dionysus`)

A future owner-named native install needs the **whole clone at the
pinned (or deliberately updated) commit** on the target Ubuntu/WSL
machine, then creates owner-local state there: `.env` (from
`.env.example`), the data directory (settings, database, auth, sessions,
uploads), and any API keys entered in Settings. None of that state —
and no key, token, or password — may be committed to either repository
or pasted into chat.

### 3.6 Deliberately not needed for this project (unless a task says so)

| In the Odysseus repo | Why not |
|---|---|
| `Dockerfile`, `docker-compose*.yml`, `docker/` | Owner decision D1 is native. Revisit only as a named design change. |
| `website/*.webm`, `website/index.html` demo/landing assets, `assets/branding/` | Demo media; weight without value here. |
| `swift/`, `start-macos.sh`, `build-macos-app.sh`, `launch-windows.ps1`, `build-windows-portable.ps1`, `update_windows.bat`, `Odysseus.spec` | Other platforms/packaging; only if a task targets them. |
| The full `tests/` tree copied here | Tests run in the Odysseus repo when that repo is the work target; copying 1,432 test files here proves nothing. |
| The `upstream-sync.yml` workflow and `upstream_sync.py` | That repo's sync machinery; only relevant to work inside that repo. |
| Local-model serving machinery (Cookbook serving, GPU overlays) | This project is cloud-API-only. (Odysseus also talks to API endpoints; the design question is which parts to use, decided in Step 3.) |

---

## 4. Facts vs claims (keep this separation)

**Verified in this session (2026-10-17):**

- At both pins: repo identity, default branch, licence key/file, and the
  existence of every path listed in Section 3 (checked one by one in each
  clone). At the current pin: head SHA/date/parents, `HARNESS_VERSION`
  still `0.20.19`, size/file counts in Section 1, and the downstream
  provider/Auto route lines still present in `app.py`.
- The textual contents summarized above were read at the first pin
  (`c35a9256…`) from: `README.md`, `SESSION_HANDOFF.md`, `WORKLIST.md`,
  `UPSTREAM_SYNC.md` (topology, downstream manifest, verification),
  `website/setup.md` (native recipe, headings, security notes),
  `website/providers-auto-council.md`, `specs/shell-mcp.md`,
  `specs/memory-skills.md`, `specs/integrations.md` (first sections),
  the provider specs for the generic OpenAI-compatible reader, NVIDIA
  NIM, and Google, `pyproject.toml`, `package.json`, `requirements.txt`
  (head), and `.env.example` (key names only; example values were
  redacted in output).
- At the pin bump to `951d57db…`, the compare `c35a9256…...951d57db…`
  was measured (ahead by 18 commits, behind by 0; 198 files changed,
  29,541 insertions, 7,959 deletions). Licence/security/handoff/audit/
  sync/setup/configuration/providers-Auto-Council docs, `.env.example`,
  requirements, `setup.py`, and all downstream provider/Auto/Council
  code and tests listed in Section 3.3 are byte-unchanged between the
  pins. Changed among Section 3 paths: `README.md` (community/star-history
  section only, in the diff read), `app.py`, `routes/mcp/mcp_routes.py`
  (OAuth callback handling, hunks read), `mcp_servers/image_gen_server.py`,
  and the spec files `llm-models`, `settings-admin`, `shell-mcp`,
  `memory-skills`, `agent-tools`, `integrations`, and the provider
  `_readme` (their new "Last updated" stamps and diff sizes were checked;
  the changed spec bodies were **not** fully re-read — a Step 3 session
  must read them at the current pin rather than trusting the summaries
  above). GitHub still reports no release; `main` was pushed
  2026-10-17 for the current pin.

**Claims by that repo's docs/specs (read, not re-proven here):**

- Feature behaviour (chat+agents with tools/MCP/files/shell/skills/
  memory, Deep Research, Compare, Documents, Email, Notes/Tasks/
  Calendar, 2FA), provider preset behaviour, Auto/Council semantics and
  its stated test counts, MCP runtime behaviour, and every dated test
  result inside `SESSION_HANDOFF.md` / `audit.md`. Specs carry their own
  "Last updated: dev@…" stamps from upstream and may lag this pin.
- Audit findings in `WORKLIST.md`: reported by that repo's own audit,
  listed as pending approval, not independently re-audited here. Treat
  them as **must-read before any install/exposure**, not as settled
  verdicts in either direction.

**Corrections to the old AI Team Kit chat, found while reading:**

- The Oct 10 answer said Odysseus's "agent mode is built on OpenCode".
  In the fork docs/spec set read at the pin, OpenCode appears as a
  **model-provider shape** (`specs/model-providers/opencode.md`, Zen/Go
  endpoints), and the external coding-agent surface is `/api/codex/*`
  for Codex/Claude integrations. No doc read here backs "agent mode
  built on OpenCode". Step 3 must settle what Odysseus's agent runtime
  actually is from primary source before repeating any of this.
- The old answer's "one review says persona group chats" can now be
  replaced with a primary-source lead: the downstream **Council** doc
  describes optional personas with a separate chair. That is still a
  doc claim to test in Step 3 — and a council is not automatically the
  owner's "persona room" design.
- Provider names inside Odysseus (presets/specs for NVIDIA NIM, Google,
  Groq, Cerebras, GitHub Models, …) say nothing about what the **AI Team
  Kit's** router/picker supports. Do not merge those two questions.

**Not verifiable here:** that Odysseus installs or runs at the pin (no
install, no server start, no test run was attempted); Windows/macOS
paths; any provider's current free-tier limits or terms; behaviour with
real keys; whether the pending audit items still apply to the pinned
tree line-by-line.

---

## 5. How future tasks should use this pointer

- **Step 1a / Step 3 (answers and comparison):** clone outside
  `dionysus` at the pin (Section 1), read Sections 3.1–3.4 in order,
  and cite file paths at that commit. Update this file if the pin or
  any summary here turns out wrong.
- **Any change to Odysseus itself** happens in the Odysseus repo, on its
  own branch/PR against its `main`, following `UPSTREAM_SYNC.md`'s
  downstream rules — never as edits to a copy inside `dionysus`.
- **Any install** is its own owner-named task after the Step 3 design is
  approved: native recipe, loopback-first exposure, auth on, audit
  worklist read first, keys only on the owner's machine.
- **Kit files (reorganised 2026-10-17):** the canonical kit is extracted in
  `kit/harness/`; the original snapshot files are preserved under
  `archive/2026-10-16-handoff-snapshot/`; and both uploaded zips plus the
  duplicate top-level guide were deleted after extraction. This Odysseus
  pointer still does not replace the kit learning/audit reports. Current
  navigation and next-task gating are in `README.md`,
  `SESSION_HANDOFF.md`, and `WORKLIST.md` (especially W-050/W-051).

---

## 6. Record

- 2026-10-17 — Pointer created in the AI Team Kit restart session at the
  owner's request ("point to" the fork + state what files are needed +
  pull that record in beside the README). Verified: `gh` metadata and a
  shallow read-only clone at `c35a9256…`; every Section 3 path checked
  to exist; selected docs/specs read as listed in Section 4. Changed in
  `dionysus`: this file plus the matching `README.md` links/decision/
  discrepancy entries. Left on purpose: no code copied, no submodule, no
  install/run/test of Odysseus, no Step 3 verdict. Not verifiable here:
  Odysseus runtime behaviour at the pin (see Section 4).
- 2026-10-17 (later) — Pin bumped `c35a9256…` → `951d57db…` after the owner
  flagged that `main` had moved that day. Verified: GitHub compare
  (18 commits ahead, 0 behind; 198 files; PR #15 parents), fresh shallow
  clone at the new head plus a fetch of the old pin for diffing, Section 3
  existence re-checked path by path, `HARNESS_VERSION` and key unchanged/
  changed files as recorded in Section 4. Left on purpose: changed spec
  bodies not fully re-read, no install/run/test, no verdict. The old pin is
  retained in Section 1 only as dated history.
- 2026-10-17 (reorganisation) — Section 5 wording updated for the extracted
  kit/archived snapshot layout and the new README/handoff/worklist files.
  The Odysseus pin was not changed or re-verified in this edit, and no
  Odysseus code was copied, installed, run, or tested. Re-check `main`
  against the pin in the next task that relies on this pointer.
