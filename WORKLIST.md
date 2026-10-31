# Worklist

Two tracks live here: the **orchestrator / agent team** work (sized from the
2026-10-31 Q&A) and the carried-over **security audit**. Tasks are sized for one
sitting each: S ≈ under an hour, M ≈ half a day, L ≈ a day or more.

## Decisions this worklist implements (from the Q&A)

| Question | Answer | What it means here |
|---|---|---|
| What is the "orchestrator / team"? | **In-app agent team**, minimalist first, ChatDev as the reference point | Roles (architect / implementer / reviewer) run inside Odysseus over one shared brief. "Bridge to the existing harness" and "rotation is enough" were not chosen. Reuse Council's multi-model call plumbing where it fits — do not build a second LLM stack. |
| Where does team memory live? | **Existing memory + RAG** | Every role artifact is written to and retrieved from the memory store/`MemoryVectorStore` already in the app. No parallel "team notes" database. |
| Key dies mid-answer? | **Continue seamlessly**, no wasted work | Shipped: partial text is pre-filled as the assistant turn and the next key resumes. Buffer-then-replay is kept only as a fallback for providers that reject prefilled assistant turns (§B3/B4). |

---

## Track A — In-app agent team (ChatDev-inspired, minimalist first)

**A1 — Role catalogue** · S · `src/agent_team.py`
- [ ] Define `Role` (key, label, system prompt, expected artifact, can_hand_off) and the three default roles: architect (plan), implementer (change), reviewer (verdict).
- [ ] Prompts must ask for a short, structured artifact (goal / steps / risks), not free prose, so the next role can consume it.
- [ ] Tests: every role has a non-empty prompt, unique key, and the catalogue is JSON-serialisable for the UI.

**A2 — Sequential runner over one shared brief** · M · `src/agent_team.py`
- [ ] `run_team(task, roles, call)` async generator: `role_start` → `role_done` per role, then `done` with the merged result.
- [ ] Each role receives: the task, the accumulated brief (prior artifacts, truncated deterministically), and its own instructions. No role sees another role's hidden reasoning.
- [ ] LLM call injected; default is `src.task_endpoint.task_llm_call_async` so the key pool and existing fallback chain protect the team automatically.
- [ ] Failure of one role stops the run with a `role_failed` event that carries the role key and a safe message (never the key or raw upstream body).
- [ ] Tests with a fake `call`: ordering, brief accumulation, truncation, failure path.

**A3 — Shared memory on the existing RAG store** · M · `src/agent_team.py`
- [ ] After each role, persist the artifact through the existing memory path (`MemoryVectorStore.add`, id `team:<run_id>:<role>`), and retrieve the top-k prior team notes for the next role as extra context.
- [ ] Must degrade to "brief only" when the vector store is unhealthy (the sandbox has no ChromaDB) and must never block or fail a run because memory is down.
- [ ] Tests: fake store records ids; unhealthy store → run still completes; retrieval failure is swallowed and logged once.

**A4 — Persist runs** · S · `core/database.py` + `routes/team_routes.py`
- [ ] `AgentTeamRun` (id, owner, task, status, merged result, created/updated) and `AgentTeamStep` (run_id, role, output, error, tokens) tables, created by `create_all`.
- [ ] Owner scoping like every other owned row; admin sees all.
- [ ] Tests: create/finish/fail a run, list by owner, ciphertext-free listing.

**A5 — API** · M · `routes/team_routes.py`
- [ ] `POST /api/team/run` — SSE stream of the events above (`text/event-stream`), admin-gated, owner taken from the session (never the body).
- [ ] `GET /api/team/runs` and `GET /api/team/runs/{id}` — history for the UI.
- [ ] `GET /api/team/roles` — catalogue for the UI.
- [ ] Tests: role ordering in the stream, 401/403 paths, owner isolation, run persisted after the stream ends.

**A6 — UI tab** · M · `static/js/providerHub.js`
- [ ] "Team" tab: task box, role checkboxes (default all three), live per-role output, merged result, "copy result" and "send to chat".
- [ ] Reuse `h()`/`api()`/`parseSseChunk()` — no innerHTML.
- [ ] Node test for the pure helpers (role list → labels, event → display state).

**A7 — Reviewer loop (ChatDev chat chain)** · M
- [ ] Reviewer can answer `REVISE` with concrete issues; those go back to the implementer for up to 2 extra rounds, then the run ends with the reviewer's summary.
- [ ] Cap the total LLM calls per run and surface the cap in the UI.
- [ ] Tests: one revision round, cap reached, reviewer approves first time.

**A8 — Parallel roles** · S
- [ ] Roles marked `parallel_safe` (e.g. two independent reviewers) run concurrently with `asyncio.gather`, results merged in declaration order.
- [ ] Tests: concurrency is observable (both started before either finished) and ordering is stable.

**A9 — Docs** · S
- [ ] `docs/AGENT_TEAM.md`: what the team is, role contracts, where memory goes, failure behaviour, cost per run, how to test.
- [ ] Link it from `README.md` and `website/providers-auto-council.md` (Pages links must stay inside `website/`).

---

## Track B — Key rotation follow-ups

**B1 — Pool + rotation** · done (`87395cee`) · `src/key_pool.py`, `routes/provider_routes.py`, `providerHub.js`
- [x] `ProviderKey` (encrypted), priority → least-recently-used selection, key-scoped cooldowns, `/api/providers/keys*`, provider-dialog card.

**B2 — Seamless mid-answer continuation** · done (`3e2405f4`) · `src/llm_core.py`
- [x] Pre-first-token failure restarts on the next key; mid-answer failure resumes from the partial text; tool-call streams are never spliced; capped at 3 continuations.

**B3 — Providers that reject a prefilled assistant turn** · S
- [ ] Detect the 4xx that follows a continuation attempt (no tokens emitted, message matches "assistant"/"prefill"/"last message"), remember it per endpoint (`supports_assistant_prefill` in the pool cache or a small prefs key), and answer 400-class errors with the original failure instead of a confusing one.
- [ ] Tests: continuation rejected → original error surfaces once, endpoint marked, next run restarts cleanly instead of trying to continue.

**B4 — Optional adaptive buffer (the "middle option")** · S
- [ ] Opt-in per endpoint: when prefill is unsupported (B3) hold the first N tokens (default 0 = off) before flushing, so a failure can restart invisibly.
- [ ] Must never change latency for endpoints that support prefill.
- [ ] Tests: buffered path emits in order, flush on completion, no duplication after a restart.

**B5 — Continuation visibility** · S (optional)
- [ ] Emit a lightweight `data: {"type": "resumed"}` event and show a subtle "continued on another key" marker in the message meta, so the user can see rotation happened without it interrupting the text.

**B6 — Which key served the turn** · S (optional)
- [ ] Include the masked key id in the existing usage event so the pool card and the message meta agree.

**B7 — Rotate in the sync `llm_call`** · S
- [ ] The sync path (`llm_call`, `llm_call_with_fallback`) has no pool hook: a scheduled job that uses it still dies on a 429. Either route it through `llm_call_async` or wrap it in the same retry loop.
- [ ] Tests mirroring the async ones.

**B8 — `200 + {"error": ...}` responses** · S (accounting fixed, rotation pending)
- [x] Accounting: the key is no longer marked successful when the body carries an error (`_note_key_failure`).
- [ ] Rotation: treat that case as key-scoped too, instead of raising straight away.

**B9 — Pool for Chatbox AI endpoints** · S
- [ ] `ChatboxAILicense` keeps **one active row per owner**, so a pooled second license loses its `Instance-Id` (`instance_id_for_key` filters `is_active`). Either allow several active licenses (one per endpoint key) or hide the pool card for Chatbox endpoints until that lands. Today the card lets you add a key that will rotate *without* its seat header.

**B10 — Pool UI never exercised in a browser** · S
- [ ] No Playwright in the sandbox: the card's add/remove/reset flow is only unit-tested (`poolKeyLabel`). Run it once against a real server with two keys of the same provider, then note the result here.

**B11 — Priority is stored but not editable** · S
- [ ] `describe_pool()` exposes `priority` and `POST /api/providers/keys` accepts it, but the card has no control. Add a number input, or drop the field from the response so the API does not promise what the UI cannot set.

**B12 — Rotation lookup cost** · S (optional)
- [ ] `endpoint_for_key()` decrypts every `ModelEndpoint` row until it finds a match. Fine on failure paths, wasteful with many endpoints: add a fingerprint index or cache the mapping.

---

## Track C — Upstream sync

- [x] **C1** Merge `source/dev` @ `516f046f` (191 commits) — `19c52bc0`.
- [x] **C2** Retry after the owner fast-forwarded the fork: merge `source/dev` @ `ef3467e8` (10 commits) — `515ae4a6`; no conflicts; model-routing fixes compose with `_first_default_model`.
- [ ] **C3** Re-run the sync whenever the fork moves; `gh repo sync` returns HTTP 403 from the sandbox, so the owner must fast-forward the fork first.
- [ ] **C4** Keep `UPSTREAM_SYNC.md`'s manifest rows current for every new downstream file (key pool and agent team included).

---

## Track D — Chatbox AI follow-ups

**D0 — Delivery** · done (`7602390`, `05299dd`, `51cad1f`)
- [x] License activation + encrypted storage, model catalogue, two gateway endpoints, plan/quota card, unlink with seat release, unsupported-model badges, `docs/CHATBOX_AI.md`.
- [x] 80 tests across client, routing, routes, encrypted storage and the JS helpers.
- [ ] No live license has ever been run through it — see D1.

- [ ] **D1** Live-license smoke test on a machine with egress to `api.chatboxai.app` (the sandbox has none; every test is mocked).
- [ ] **D2** Decide whether to add Gemini-native / OpenAI-Responses adapters or hide those models entirely.
- [ ] **D3** If a Claude call fails on a gateway-specific beta header, capture the response and add it in `build_headers` — do not guess.

---

## Session audit (checked 2026-10-31, after the second upstream merge)

What was actually re-verified rather than assumed:

| Claim | How it was checked | Verdict |
|---|---|---|
| Anthropic (Claude) deltas can be continued mid-answer | read the `content_block_delta` branch: it emits `data: {"delta": text}`, the same shape `_stream_delta_text` parses | OK — continuation works for Claude models, not only OpenAI ones |
| Agent mode inherits key rotation | `agent_loop` uses `stream_llm_with_fallback` → `_stream_candidate_with_context_recovery` → `stream_llm` | OK — rotation applies to agent turns too |
| Non-streaming callers rotate | **was untested**; added two tests with a fake transport (429 then 200 → second key used; no second key → 429 still raised) | Fixed (`test_key_pool.py`) |
| A key that returns `200 + {"error": ...}` is not recorded as healthy | **was wrong**: `_note_key_success` ran before the error check. Moved after it, added `_note_key_failure` | Fixed; rotation for that case still open (B8) |
| No raw key is logged by the pool | grepped every `logger.*` in `key_pool.py` — fingerprints (`[:8]`) and masks only | OK |
| Every new route is admin-gated | enumerated all `@router.*` in `provider_routes.py` and matched `require_admin(request)` | OK — 6/6 |
| Pooled keys are encrypted at rest | existing test reads raw SQL and asserts an `enc:` prefix | OK |
| A locked-up pool cannot break routing | `_pooled_key()` swallows exceptions and falls back to the endpoint's own key; covered by `test_resolve_endpoint_runtime_survives_a_broken_pool` | OK |
| Full suite has no new failures | full run vs. the base-commit baseline (same 73 environment-only failures) | see the run recorded in `SESSION_HANDOFF.md` |
| The pool card works in a browser | **not possible here** (no Playwright/Chromium) | Open — B10 |
| A removed/replaced endpoint key stops being used immediately | **was wrong**: the pool cache also cached the endpoint's own key for 15 s, so a revoked key kept being sent. 28 upstream authority tests caught it; the primary is now never cached | Fixed (`d579f4ac`) — regression test added |
| A new env var is documented | **was wrong**: `ODYSSEUS_KEY_POOL_DISABLED` had no note, so the generated config reference went stale (3 failures) | Fixed — note added, page regenerated |
| The service-worker cache bump keeps upstream's editor suites green | **was wrong**: the previous sync appended `-providerhub`, but upstream asserts `re.fullmatch(r'odysseus-v\d+-pr40-editor-precache')` → 43 failures. Now `odysseus-v1116-pr40-editor-precache`, and the manifest rule says to increment the number | Fixed (`3029c8ce`) |
| Full suite vs pristine upstream | ran both trees in full and diffed the failure lists | **only** the 2 known order-dependent `test_provider_and_auto_routes` cases differ (they pass in isolation); everything else also fails on upstream `ef3467e8` in this sandbox |
| DeepSeek/other `data: {"error": ...}` 200-shaped streams rotate | only the HTTP-status path is handled | Open — B8 |

Not done, and not hidden: Track A (agent team) has not been started; B3/B4/B5, B7–B12,
C3–C4 and D1–D3 are open. Nothing from this session was left uncommitted.

## How to verify each task

```bash
.venv/bin/python -m pytest -q tests/test_key_pool.py tests/test_provider_keys_routes.py   tests/test_provider_hub_chatbox_js.py tests/test_llm_core_streaming.py tests/test_llm_core_fallback.py
.venv/bin/python .github/scripts/upstream_sync.py --check-only     # 27/27 PASS expected
node --check static/js/providerHub.js
```

A task is done when its tests pass, `upstream_sync.py --check-only` still says
27/27, and any new upstream-owned file it touched has a manifest row.

---

# Security audit (carried over)

**Status:** Security findings are pending user approval; no security remediation has started. Two unrelated deprecation warnings were cleaned up separately.

**Status:** Security findings are pending user approval; no security remediation has started. Two unrelated deprecation warnings were cleaned up separately.

## Priority 0 — Obtain approval

- [ ] Confirm which audit findings should be fixed and whether the agent shell/filesystem sandbox risk is in scope.
- [ ] Keep all work on `arena/01a10a87-odysseus-fork-but-api-dev`.

## Priority 1 — Protect auth and session persistence (A-1, High)

- [ ] Add a secure atomic-write path for secret-bearing JSON files that creates temp files with owner-only permissions before writing/renaming.
- [ ] Re-lock existing `auth.json` and `sessions.json` files on startup; handle failure explicitly and preserve Windows ACL behavior.
- [ ] Restrict the data directory where compatible, including Docker bind-mount behavior and ownership.
- [ ] Create `.env` with owner-only permissions rather than inheriting the example file's mode.
- [ ] Consider hashing persisted session tokens and add POSIX permission tests for newly created and pre-existing files.
- [x] Baseline auth/session and atomic-I/O tests run (81 focused tests passed without warnings); rerun after an approved fix.

## Priority 1 — Close token-chat DNS rebinding (A-2, High)

- [ ] Design an outbound transport that pins each connection to a validated public IP while preserving Host/SNI.
- [ ] Apply it to `/api/v1/chat` initial calls and resumed sessions; ensure redirects cannot bypass validation.
- [ ] Add deterministic regression tests for DNS changing between validation and connection, including a resumed session.
- [ ] Update the relevant `THREAT_MODEL.md` entry to describe the residual behavior accurately.
- [x] Baseline API-chat and security-area tests run (832 security-area tests passed without warnings); add direct DNS-rebinding regressions and rerun after an approved fix.

## Priority 1 — Secure bootstrap (A-3, conditional High)

- [ ] Restrict `/api/auth/setup` to trusted loopback access or a strong, one-time bootstrap secret.
- [ ] Decide whether startup should fail when auth is enabled but bootstrap/setup fails.
- [ ] Add tests for remote first-run rejection, valid local bootstrap, and concurrency/one-time behavior.
- [x] Baseline auth-policy and root-path middleware tests run (included in the 81 focused tests); add remote-bootstrap coverage and rerun after an approved fix.

## Priority 2 — Fail closed on invalid privilege data (A-4, Medium)

- [ ] Change `require_privilege()` to deny when the privilege record is malformed or lookup fails.
- [ ] Update the existing fail-open regression test and add tests for lookup exceptions and malformed stored maps.
- [x] Baseline privilege/auth security tests run (included in the focused and security-area suites); add fail-closed assertions and rerun after an approved fix.

## Priority 3 — Validate and document residual risk

- [ ] Decide whether an OS-level sandbox or stronger isolation for shell/Python/file tools is required by the deployment threat model.
- [ ] If approved, scope a separate design for least-privilege execution, filesystem confinement, and network egress controls; do not treat prompt instructions as a sandbox.

## Test environment

- [x] Established repo-local ignored `.venv/` and installed `requirements.txt`.
- [x] Ran focused audit tests: 81 passed, no warnings.
- [x] Ran security area: 832 passed, 5,124 deselected, no warnings.
- [x] Replaced deprecated SQLAlchemy and Pydantic APIs responsible for the two warnings; confirmed they are gone in the security-area run.
- [ ] After approved security changes, rerun focused tests, related security suites, then the broader suite as practical.
- [x] Recorded the validation commands/results in `audit.md`; baseline passes do not prove the audit findings are fixed.
