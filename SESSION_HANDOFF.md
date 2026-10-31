# Session Handoff

## Latest session — Chatbox AI provider (2026-10-31)

Branch `arena/d5cf1ff7-odysseus-fork-but-api-dev` adds a first-class **Chatbox AI** provider
(a chatboxai.app subscription license key), matching the Chatbox desktop client's wire contract
but using only Odysseus's existing endpoint/encryption layers.

**Implemented**

- `src/chatbox_ai.py` — license activate/validate/deactivate/detail, model catalog (model-list with
  manifest fallback), per-gateway variants, plan/quota summary, encrypted storage helpers,
  `Instance-Id` header lookup (5-minute process cache, never network I/O in header building).
- `provider_presets.py` — `chatboxai` preset, `api_style`/`supported` on `ModelCard`, discovery adapter
  that activates + lists + groups models. Gemini-native and OpenAI-Responses models are catalogued but
  unsupported (Odysseus implements neither protocol yet).
- `routes/provider_routes.py` — chatbox branch on `POST /api/providers/models` (persists license, strips
  `instance_id`/`license_detail` from the response) plus admin-only
  `POST /api/providers/chatbox/activate`, `GET /api/providers/chatbox/status?refresh=`, and
  `POST /api/providers/chatbox/deactivate` (releases seat, disables matching endpoints, deletes row).
- `core/database.py` — `ChatboxAILicense` (`EncryptedText` key/instance/detail; SHA-256 fingerprint; one
  active row per owner). Created by `create_all`; no ALTER migration needed.
- `src/llm_core.py` / `src/endpoint_resolver.py` — detect Chatbox's `/gateway/anthropic/` as Anthropic,
  build `/messages` vs `/chat/completions` correctly, send `x-api-key` vs Bearer, attach `Instance-Id`,
  label the provider "Chatbox AI".
- `static/js/providerHub.js` — license card with plan/quota/expiry, refresh + unlink, disabled
  "not supported" badges, and per-gateway connect (one endpoint for OpenAI models, one for Claude).
- Docs: `docs/CHATBOX_AI.md`, `website/providers-auto-council.md`, README, ACKNOWLEDGMENTS.

**Validation**

- `234 passed` across provider presets, provider routes, endpoint URL/header/detection suites; the
  Chatbox-focused suites add `80 passed` (client/routing/routes/storage/JS helper checks).
- `node --check static/js/providerHub.js` clean; `python -c "import app"` boots and `create_all` creates
  `chatbox_ai_licenses` on a fresh database.
- Full suite on this branch: the same 73 failures as the base commit `c2d9bbd` (verified side by side) —
  they are frontend tests without `node_modules`/Playwright, sandbox-only workspace/subprocess checks, and
  two order-dependent provider tests that pass in isolation. No new failures; the one documentation link
  regression caught by the first full run is fixed.
- All Chatbox HTTP is mocked: the suite proves contract shape, key handling, routing and storage, **not**
  that a real license works. A live check needs a key and egress to `api.chatboxai.app` (blocked in the
  sandbox). Report this honestly before claiming it works end-to-end.

**Shipped**

- Commits `7602390` (feature), `05299dd` (keyless headers / pinned default), `51cad1f` (Pages link fix) on
  `arena/d5cf1ff7-odysseus-fork-but-api-dev`; PR #19 targets `main`.

**Deliberately not done**

- No first-party Odysseus-hosted API (the user clarified they want Chatbox AI itself, not a new gateway).
- No Gemini-native / OpenAI-Responses chat adapters; no image/embedding/RAG/account-login Chatbox features.
- No Electron/Android shell work (user deferred until after research). Odysseus is a local web server;
  the portable Windows and macOS launchers already open the local URL in the browser.

**Next likely steps**

1. Live-key smoke test on a machine that can reach `api.chatboxai.app`; verify `Instance-Id` is accepted and
   quota is attributed.
2. If Claude calls fail because the gateway expects a different beta header, capture the response and add it
   in `build_headers` (do not guess).
3. Decide whether to add a Gemini-native adapter (larger change) or hide those models entirely.

## Latest session — key rotation (BYOR pool) and upstream sync (2026-10-31)

**Upstream sync.** `source/dev` @ `516f046f` (191 commits) is merged into the branch as merge commit
`19c52bc0`. Only `.gitleaks.toml` and `static/sw.js` conflicted; both resolved by the manifest rules
(upstream allowlist kept + downstream historical fixture re-appended; upstream `CACHE_NAME`
`odysseus-v1115-pr40-editor-precache` bumped to `...-providerhub`). Every Chatbox hook survived in the
auto-merged upstream files. Gate: `upstream_sync.py --check-only` 27/27, 485 tests, app boots on
`0.0.0.0:7011`, `/api/providers/*` and `/api/auto/pool` answer 401 (registered behind auth).
**The mirror fork is 10 commits behind `odysseus-dev/dev`** and `gh repo sync` returns HTTP 403 from
this sandbox — those ten commits are still outstanding; the owner must sync the fork.

**Key pool (new).** One endpoint, many credentials, automatic rotation:

- `core/database.py::ProviderKey` — encrypted `api_key`, SHA-256 `key_fingerprint`, `priority`,
  `is_enabled`, endpoint FK. The endpoint's own `api_key` is implicitly the first pool member, so
  nothing migrates.
- `src/key_pool.py` — selection (priority → least-recently-used), cooldowns (`429` honors
  `Retry-After` else 60 s, `402`/quota `403` 30 min, `401` 1 h, three provider-wide failures rest a key
  30 s), rotation, header swap, masking, `describe_pool()`. Health is **process memory only** (no DB
  write on the chat path); credentials are cached 15 s with invalidation on mutation.
- `resolve_endpoint_runtime()` consults the pool, so chat, agent tools, skills, research, webhooks and
  background tasks all rotate without knowing about it. `stream_llm()` retries a pre-first-token
  `401/402/403/429` on the next key; `llm_call_async()` retries immediately instead of sleeping.
  After output starts, the error is surfaced (a silent splice would duplicate text).
- Routes `GET/POST/DELETE/PATCH /api/providers/keys*` (admin), and an "API key rotation (pool)" card in
  the provider dialog (`static/js/providerHub.js`, `poolKeyLabel` exported for tests).
- `docs/KEY_POOL.md` documents policy, storage and seams. 726 tests pass across the touched suites.

**Not built yet** (user's next asks): multi-agent "team" orchestration (architect / implementer /
reviewer roles with a shared handoff), and any cross-process health sharing.

## Upstream sync (read this first)

- This repository shares git history with upstream since merge commit `0f5c3c94` (PR #10, 2026-10-14, upstream `dev` @ `86b886c6`).
- New upstream commits arrive automatically: the "Upstream sync" workflow (`.github/workflows/upstream-sync.yml`, script `.github/scripts/upstream_sync.py`) merges the fork into a `sync/upstream` PR on every push to `main` and daily, and files an issue when the merge conflicts. Setup (PAT secret `UPSTREAM_SYNC_TOKEN`, optional auto-merge) and the manual procedure are in `UPSTREAM_SYNC.md`; a manual sync is a 15-30 minute three-way merge, and the file lists every downstream customization that must survive, the per-file conflict rules, the verification commands, and the PR/CI gotchas.
- Never re-import the project from an archive: that disconnects the histories again (recovery recipe is in `UPSTREAM_SYNC.md`, Appendix A).

## Current state (historical: 2026-10-05 extraction session)

- Repository: `/home/user/odysseus-fork-but-api-dev`
- Branch at the time: `arena/01a10a87-odysseus-fork-but-api-dev` (merged since; use your own working branch and open PRs against `main`)
- The source archive `odysseus-fork-but-api-dev.zip` was deleted at the user's request. The extracted project files remain in the repository root.
- Audit findings are recorded in `audit.md`; they are **pending approval**. No security-finding remediations were applied. The only source edits after the audit are unrelated deprecation-warning cleanups.
- Root handoff files created: `audit.md`, `SESSION_HANDOFF.md`, and `WORKLIST.md`.

## Audit summary

1. High: `core/atomic_io.py` and setup paths create auth/session files without owner-only permissions; raw session tokens are persisted in `sessions.json`.
2. High: Token-chat URL validation is vulnerable to DNS rebinding because the checked address is not pinned to the later HTTPX connection; resumed sessions skip the direct URL validation branch.
3. High, conditional: `/api/auth/setup` is auth-exempt and can create the first admin from a remote request if the instance is exposed before setup completes.
4. Medium: `require_privilege()` fails open on malformed privilege data or lookup errors.
5. Documented residual risk: agent shell/filesystem tools have no OS-level sandbox, per `THREAT_MODEL.md`.

See `audit.md` for exact locations, impact, remediation suggestions, and evidence.

## Validation status

- Created repo-local, Git-ignored `.venv/` and installed `requirements.txt`; no dependency manifest was changed.
- Focused audit tests: **81 passed, no warnings** across API chat security, auth policy/privileges, root-path auth, session revocation, and atomic I/O.
- Security area: **832 passed, 5,124 deselected, no warnings** via `tests/run_focus.py --area security`.
- Cleaned up the SQLAlchemy `declarative_base()` import and Pydantic `.dict()` deprecations; the security-area run confirms both warnings are gone.
- AST parsing succeeded for 1,159 Python files with no syntax errors.
- A standard-library permission probe confirmed mode `0644` for atomic JSON writes under umask `022`.
- `git diff --check` was clean.

Tests pass against the current code but do not cover every reported gap. No audit finding has been fixed; rerun relevant tests after any approved security remediation.

## Working-tree notes

The initial repository contained a tracked archive and a minimal README. The archive is now deleted; the extracted project files are untracked, and the README was replaced during extraction. The current branch is still the Arena session branch. No commit or push was made.

## Next step

Wait for the user's approval on the findings/remediation scope. Then address approved items on the current branch, add regression tests, and rerun the focused tests plus relevant neighboring suites with the existing repo-local `.venv/`; run the broader suite as practical.
