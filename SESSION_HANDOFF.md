# Session Handoff

## Current state — 2026-10-31, ready to merge

| | |
|---|---|
| Branch | `arena/d5cf1ff7-odysseus-fork-but-api-dev` |
| PR | **#19** → `main`, open |
| Working tree | clean; everything pushed |
| CI on this branch | description check, gitleaks, actionlint, hadolint, zizmor, pip-audit, `node --check` all pass |
| Upstream baseline | `freeforall1932-design/odysseus-fork-but-api` @ `ef3467e8` (level with `odysseus-dev/dev`) |
| Downstream delta vs upstream | 93 files, +22,484 / −37 |

**Merge it with a merge commit (`gh pr merge 19 --merge`). Never squash or rebase this PR**: it
carries the upstream merge commits (`19c52bc0`, `515ae4a6`) that link the fork's history to
`odysseus-dev/odysseus`. Squashing drops the link and the next upstream sync conflicts everywhere
(`UPSTREAM_SYNC.md`, "Automation" step 1).

## What is on the branch

### 1. Chatbox AI provider (license key)

Paste a chatboxai.app license key in the provider dialog; the server activates the seat, lists the
plan's models, and routes turns through Chatbox's OpenAI- and Anthropic-compatible gateways. API
compatibility only — no Chatbox code is bundled or redistributed.

- `src/chatbox_ai.py` — license activate/validate/deactivate/detail, catalogue (`model_list`, with
  `model_manifest` fallback), gateway mapping, `Instance-Id` cache, key masking.
- `core/database.py::ChatboxAILicense` — encrypted key/instance/detail, SHA-256 fingerprint, one
  active row per owner.
- `routes/provider_routes.py` — chatbox branch on `POST /api/providers/models` plus
  `/api/providers/chatbox/{activate,status,deactivate}`.
- `src/llm_core.py`, `src/endpoint_resolver.py` — Claude gateway detected as Anthropic, `/v1`
  handling, `Instance-Id` merged into `build_headers`, "Chatbox AI" provider label.
- `static/js/providerHub.js` — license card (plan/quota/expiry), per-gateway connect, unsupported
  badges, unlink reporting disabled endpoints.
- `docs/CHATBOX_AI.md`.

### 2. API key pools + rotation (the BYOR orchestrator)

One provider, several keys. A rate-limited or exhausted key is skipped and the same turn continues on
the next one.

- `core/database.py::ProviderKey` — encrypted key, fingerprint, priority, enabled. The endpoint's own
  `api_key` is implicitly the first pool member, so nothing migrates.
- `src/key_pool.py` — priority → least-recently-used selection, key-scoped cooldowns (`401` 1 h,
  `402`/quota `403` 30 min, `429` honours `Retry-After` else 60 s), header swap, masking,
  `describe_pool()`. Health is process memory only; the chat path never writes to the DB to rotate.
- `resolve_endpoint_runtime()` consults the pool, so chat, agent tools, skills, research, webhooks and
  background tasks all rotate. **The endpoint's own key is never cached** — a revoked key stops being
  used on the next request.
- `stream_llm()` restarts before the first token; after a mid-answer failure it re-sends the exact
  partial text as an assistant prefix so the next key continues the sentence (tool-call streams are
  never spliced; 3 continuations max). `llm_call_async()` rotates instead of sleeping on the same key
  and no longer marks a key healthy when a `200` carries an `{"error": ...}` body.
- `routes/provider_routes.py` — `GET/POST/DELETE/PATCH /api/providers/keys*`, `POST
  /api/providers/keys/reset` (admin only).
- `static/js/providerHub.js` — "API key rotation (pool)" card, `poolKeyLabel()` exported for tests.
- `docs/KEY_POOL.md`.

### 3. Upstream syncs

- `19c52bc0` — `source/dev` @ `516f046f`, 191 commits. Conflicts: `.gitleaks.toml` (upstream
  allowlist kept, downstream historical-fixture block re-appended) and `static/sw.js` (`CACHE_NAME`
  bumped, `providerHub.js` re-added to `PRECACHE`).
- `515ae4a6` — `source/dev` @ `ef3467e8`, 10 commits, no conflicts. Upstream's model-routing fixes
  compose with `_first_default_model()`.

## Verification

- `upstream_sync.py --check-only` → **27/27 PASS** (symbols, downstream lines, precache assets,
  `node --check`, `py_compile`).
- Full suite, both trees run in full in this sandbox:

  | tree | failed | passed |
  |---|---|---|
  | this branch | 76 | 17,119 |
  | pristine upstream `ef3467e8` | 75 | 16,856 |

  The only difference is two known order-dependent `test_provider_and_auto_routes` cases that pass in
  isolation (WORKLIST B13). Everything else fails identically on pristine upstream here — Playwright,
  bubblewrap, tmux and ffmpeg are unavailable in the sandbox.
- Runtime: app boots on `0.0.0.0:7011`; `/api/providers/presets`, `/api/providers/chatbox/status` and
  `/api/auto/pool` answer 401 (registered, behind auth); `sw.js` and `index.html` serve the
  providerHub entry; `create_all` creates `chatbox_ai_licenses` and `provider_keys` on a fresh DB.
- Targeted suites: 726 passed across model-routing, provider, Chatbox, key-pool and sync suites.
- Secret scan: `gitleaks` failed on **every** run of this branch (its first four runs back to
  `05299dd1`) while `main` stayed green. Cause: the mocked licence fixture in
  `tests/test_provider_chatbox_routes.py` (`cbx-route-test-key-abcdef123456`, entropy 4.16) tripped
  the default `generic-api-key` rule, and the workflow scans with `fetch-depth: 0`, so fixing the
  current tree alone would not clear it. Fixed in `342db66a`: the fixture is now letters-only
  (`cbx-route-fixture-license`, which the rule's own `^[a-zA-Z_.-]+$` allowlist skips) and the
  retired literal is allowlisted by an exact anchored regex next to the existing `sk-LEAKTEST-123456`
  block. Verified green. Appendix B of `UPSTREAM_SYNC.md` has the local check procedure.

## Known limitations (all tracked in `WORKLIST.md`)

- **No live Chatbox license has ever been used** — no egress to `api.chatboxai.app` here; every test is
  mocked. A real key is still unverified (D1).
- The key pool has not been exercised in a browser (no Playwright here) — B10.
- Not yet rotating: the sync `llm_call` (B7), and providers that answer `200` with an error body (B8,
  now accounted as a failure but not rotated).
- Pools on Chatbox endpoints are incomplete: a second license has no active row, so it rotates without
  its `Instance-Id` — B9.
- Gemini-native / OpenAI-Responses Chatbox models are listed but disabled (D2).
- Desktop/Android shells remain deferred by the user.
- Security audit findings are still **pending approval and unfixed** (`audit.md`, below).

## Merge and after-merge steps

1. `gh pr merge 19 --merge` (see the warning at the top — merge commit only).
2. Run the upstream-sync workflow once against the new `main`, or wait for its nightly run, to confirm
   the manifest still matches (C4).
3. If the owner fast-forwards the mirror fork again, the next sync is the same procedure; `gh repo
   sync` returns HTTP 403 from this sandbox, so fork updates must come from the owner.

## Next session packet (Track A — in-app agent team)

Read in this order: this file → `WORKLIST.md` Track A → `src/council.py` and `src/task_endpoint.py`
(the LLM plumbing to reuse) → `src/memory_vector.py` (`MemoryVectorStore.add(memory_id, text)`, the
RAG store the team writes into).

Start at **A1 + A2** (`src/agent_team.py` role catalogue and sequential runner — additive, no DB, no
UI, no routes). Then A3 (RAG-backed shared memory), A4 (run persistence), A5 (SSE API), A6 (Team tab),
A7 (reviewer loop), A8 (parallel roles), A9 (docs).

Cold-start limits to expect: no ChromaDB (memory degrades to "brief only"), no Playwright/Chromium,
no `node_modules` (the static gate's `node --check` still works), and `pytest` needs the repo-local
`.venv` recreated from `requirements.txt`.

## Commit history (this session, current branch)

```
342db66a Allowlist the retired Chatbox licence fixture for the history secret scan
17784f72 Sweep the handoff and sync manifest before merging
338c7c35 Record the final audit numbers and the order-dependent test item
4f6a836e Close the audit table with the upstream-vs-ours full-suite diff
3029c8ce Bump the service-worker cache version instead of suffixing it
f4ec8356 Record the two audit regressions in the worklist audit table
d579f4ac Fix a stale-key cache and document the pool's env switch
567df7d8 Audit the key pool: fix bad success accounting, cover non-stream rotation
95dd7b62 Split the orchestrator Q&A into a sized worklist
515ae4a6 (merge) upstream fork dev @ ef3467e8 — 10 commits, no conflicts
3e2405f4 Continue a stream on the next key instead of cutting the answer
87395cee Add API key pools with automatic rotation
19c52bc0 (merge) upstream fork dev @ 516f046f — 191 commits, 2 conflicts
2bc48a1e Record Chatbox AI validation and shipped commits in the handoff
51cad1fb Keep the Pages guide's Chatbox link inside the website tree
05299dd1 Make keyless endpoint headers and pinned defaults explicit
76023907 Add Chatbox AI license-key provider support
```

Earlier commits on this branch (provider onboarding, Auto routing, Council UI, the sync automation
and the security audit) predate this session; see `git log main` and `audit.md`.

## Upstream sync (read before any merge or rebase)

- This repository shares git history with upstream since merge commit `0f5c3c94` (PR #10, 2026-10-14,
  upstream `dev` @ `86b886c6`).
- New upstream commits arrive automatically: the "Upstream sync" workflow
  (`.github/workflows/upstream-sync.yml`, script `.github/scripts/upstream_sync.py`) merges the fork
  into a `sync/upstream` PR on every push to `main` and daily, and files an issue when the merge
  conflicts. Setup (PAT secret `UPSTREAM_SYNC_TOKEN`, optional auto-merge) and the manual procedure are
  in `UPSTREAM_SYNC.md`; a manual sync is a 15–30 minute three-way merge.
- Never re-import the project from an archive: that disconnects the histories (recovery recipe in
  `UPSTREAM_SYNC.md`, Appendix A). Never squash or rebase a sync PR.

## Carried over: security audit (pending approval)

Findings recorded in `audit.md`; **none has been fixed** — approval is still pending, and the only
source edits since the audit are unrelated deprecation cleanups.

1. High: `core/atomic_io.py` and setup paths create auth/session files without owner-only permissions;
   raw session tokens are persisted in `sessions.json`.
2. High: token-chat URL validation is vulnerable to DNS rebinding (checked address not pinned to the
   later HTTPX connection); resumed sessions skip the direct URL validation branch.
3. High, conditional: `/api/auth/setup` is auth-exempt and can create the first admin from a remote
   request if the instance is exposed before setup completes.
4. Medium: `require_privilege()` fails open on malformed privilege data or lookup errors.
5. Documented residual risk: agent shell/filesystem tools have no OS-level sandbox, per
   `THREAT_MODEL.md`.

Baseline at audit time: 81 focused tests and 832 security-area tests passed. Tests pass against the
current code but do not cover every reported gap; rerun after any approved remediation.
