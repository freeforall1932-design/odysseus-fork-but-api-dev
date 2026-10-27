# Minimal drift — adaptive council + quota-aware pool architecture (W-050 design only)

**Status:** design doc for minimal Option A — no runtime install, no provider calls, no installer change.
**Baseline:** `planning/Odysseus API model team kit/WORKLIST.md` W-050 + `PROJECT_CONTEXT.md §3` + `RESEARCH_AND_OPEN_QUESTIONS.md Q5/Q14` + `reports/FREE_PROVIDER_RESEARCH_2026-10-18.md` §10 + current Odysseus `src/provider_presets.py`, `src/auto_router.py`, `src/council.py`, `website/providers-auto-council.md`.

This file answers W-050’s required questions with *one* concrete example per mode plus a worked 429. It does **not** implement W-021/W-030/W-040/W-051.

---

## 1. Who does what (owner direction, not yet code)

| Role | Where it runs | What it does |
|---|---|---|
| **Odysseus** | `freeforall1932-design/odysseus-fork-but-api-dev` @ `63f39df` (now `8877273e` + planning) — native `uvicorn app:app --host 127.0.0.1 --port 7000`, AGPL-3.0 | Simpler *room/council surface* for writing/daily use + adaptive council (1 simulated → 2–3 real). Keeps provider keys in encrypted `model-endpoints` (never in `.env` for council). |
| **OAT** | `Root-IO-Labs/open-agent-teams` v0.1.0 via `kit/harness/install.sh` — outside Odysseus, on same Ubuntu/WSL host | *PR execution team* — `oat agent tell <agent> <text> --repo` in worktrees, opens PRs. Uses LiteLLM role names `architect/implementer/reviewer` that currently point at Odysseus pool via `harness connect-oat` (writes `~/.oat/config.toml` + `~/.oat/.env`). |
| **LiteLLM router** | `~/litellm-env` on `127.0.0.1:4000` — from kit’s `model_scout.py` output `~/.litellm/config.yaml` | One doorway: helpers ask `architect/implementer/reviewer`, router forwards to ranked provider/model. In minimal drift, router stays as *fallback* for OAT; Odysseus `auto_router.py` handles its own pool directly. |

Owner is merge gate (no auto-merge). Helpers run as same OS user as kit secrets — audit A-03 remains residual risk.

---

## 2. Adaptive council — three escalations

Based on `PROJECT_CONTEXT.md §3` clarification (2026-10-18) + `src/council.py` modes:

### Mode 1 — Light question / draft (1 simulated call)

- **When:** `needs_tools == False`, `has_image == False`, message < ~400 tokens, no conflict history, owner hasn’t forced escalation.
- **What:** pick **one** model from pool (prefer `free=conditional` with longest cooldown-until in future → skip; else prefer `free=eligible` lowest latency). Call it once with persona synthesis prompt:

```
System: You are 3 personas in one answer. Think as Researcher (facts), Logician (steps), Builder (actions). Then chair the synthesis into ONE answer. Show personas’ bullets, then Final:.
User: <question>
```

- **Cost:** 1 call, ~600 tokens. No member voting. `council.py` not used — single call simulates diversity. If answer contains `looks_like_refusal()` → auto-escalate to Mode 2.

### Mode 2 — Important/contested decision (2–3 real models)

- **When:** owner marks “council: hard”, or Mode 1 answer triggered refusal/uncertainty, or `FREE_PROVIDER_RESEARCH` guard says pool health < 2 eligible models.
- **What:** `src/council.py` `debate` with `members=2–3` (shuffled, anonymised), `rounds=2`, `chair` separate seat (never votes), `DEFAULT_PERSONAS` assigned round-robin, `skill_text` = `team-workflow` or owner skill, `skill_scope=chair`. Chair system: `CHAIR_SYSTEM` (“judge by reasoning, not counts”).
- **Guard:** one request in-flight per provider (enforce in `auto_router.py` + `council.py _round`), honour `Retry-After`, bounded retries with backoff/jitter that count visibly against task budget (W-015 rule).

### Mode 3 — Repository/PR execution (OAT agents, sequential)

- **When:** message starts with workspace agent intent (e.g. `fix:`, `docs:`, `feat:`, or `detectWorkspaceAgentIntent()` helper in `static/js/chat.js`).
- **What:** OAT `oat agent tell` → `architect` (plan) → `implementer` (code) → `reviewer` (check). Each step is a separate OAT agent with its own `litellm:role` model (from scout/LiteLLM). Normally sequential, not parallel, to avoid hammering quotas.

Owner override: `/council solo` / `/council full` / `/council off` in chat; UI switch `Keep local` hard-fails to 409 if no offline model.

---

## 3. Quota-aware pool — how Google/NVIDIA/OpenRouter/… become one

Source: `FREE_PROVIDER_RESEARCH_2026-10-18.md` §1 + §10 (evidence rules + guard defaults) now encoded minimally in `src/provider_presets.py` (`free_evidence`, `guard_rpm/rpd`, `guard_note`) — this commit.

| Provider | `free_evidence` (W-015 rule) | `guard_rpm/rpd` encoded | What this means in code |
|---|---|---|---|
| OpenRouter `:free` | `eligible` — pricing `prompt==0 && completion==0` | 18 / 50 (→1000/day after ≥$10) | `parse_openrouter()` already parses `pricing`; `Discovery.free` True only when both 0. `GET /key` → `free_model_daily_requests {used,limit,remaining}` read before long tasks. |
| Google (Flash) | `conditional` — free only for Flash-class models, per-model pricing page; limits login-only, counted per project, RPD midnight PT; unpaid content may train Google. | 10 / None | `parse_google()` keeps only `generateContent` models; `id_strip models/` + include flash *heuristic* removed — now `free_evidence` decides, not `assume_free`. Note updated: “Flash-class only, login-only limits, may train”. |
| Groq | `eligible` — permanent free plan, per-model RPM/RPD/TPM/TPD published; no training. | 30 / 1000 | New preset note: “30 RPM/1K RPD/8K TPM/200K TPD example; strongest candidate”. Responses carry `x-ratelimit-remaining`/`retry-after`. |
| Mistral | `conditional` — Free mode = included monthly allowance (limits login-only); pay-as-you-go off to avoid billing; Labs models always train. | None (login-only) | Note: “Free mode monthly allowance, keep PAYG off, Free-mode data may train (opt-out), Labs excluded”. |
| NVIDIA NIM | `conditional` — no-cost trial for prototyping; credits removed; limits unpublished (show in build.nvidia.com UI, often ~40 RPM) | 6 / None | Note: “unpublished, show in account UI”; guard 1 in-flight, gentle pacing, manual my-account-limit field (W-015). |
| Cerebras | `paid-risk` — no permanent free since 2026-07; $5 after payment, 30d expiry | None | Note: “excluded by default, remove from free-only pool”. |

**Quota ledger (W-015, not yet coded — design):**

```
scout_state.json (or per-user prefs `auto/pool`):
  provider_states: {
    google: { attempts: 12, last_429: "2026-10-27T08:14:30Z", cooldown_until: "2026-10-27T08:20:00Z", rpd_used_today: 14 },
    openrouter: { rpd_used: 7, limit: 50, remaining: 43, from: "GET /key 2026-10-27T08:00Z" }
  }
```

Restart does not re-hammer: ledger survives restarts, `cooldown-until` is persisted, next run reads it first. When every pool member is cooling-down/exhausted → plain message “all free services are resting until 14:32 — daily free limit reached” (W-050), not loop.

---

## 4. Call-count examples — what the system does minute by minute

### 4.1 Light question — “What’s a good commit message for fixing the CSS mobile override?”

- `0:00` — `POST /api/auto/route {message, needs_tools: false}` → pool has 8 entries (OpenRouter 3, Google 2, Groq 1, NVIDIA 1, Mistral 1).
- `0:01` — `auto_router.prefilter` drops 0 (no image/tools/local constraint). Router model `gemini-2.5-flash` (pool’s designated router) sees numbered list, answers `{"pick": 3}` in 0.9s.
- `0:02` — single call to picked model `groq:llama-3.3-70b-versatile` with simulated-personas prompt → 420 tokens, no refusal.
- **Total: 2 calls (router pick + answer), ~1.1k tokens, ~3s.** Council not used. `DRIFT.md` records: “A1 light → simulated”.

### 4.2 Hard decision — “Should I merge the PR that adds Cerebras preset to the free pool, or keep it paid-risk?”

- `0:00` — user clicks **Council: debate**, 3 members: `openrouter:free-model-A`, `groq:llama-3.3-70b`, `google:gemini-2.5-flash`. Skill `team-workflow` → `skill_scope: chair`.
- `0:01–0:15` — `fanout`: 3 parallel calls (one per provider, 1 in-flight each) → each 500 tokens, 4s.
- `0:15–0:35` — `debate rounds=2`: each member reads others anonymised/shuffled, revises (2 × 3 calls = 6 calls, each prompt carries others’ answers → tokens ≈ 6× avg 1.5k).
- `0:35–0:45` — `chair` (separate `openrouter:free-model-B`) judges by reasoning, not counts → 900 tokens, verdict.
- **Total: 10 calls (3+6+1), ~12k tokens, ~45s** — reported via `POST /api/council/plan` estimate before run; UI streams `member`/`round_done`/`chair`. If one member returns `declined` → chair line “1 member declined; weighed remaining reasoning”.

### 4.3 PR task — “Fix the provider pool to exclude Cerebras from free-only”

- `0:00` — workspace intent detected (`fix:`). Chat router skips council, returns `endpoint_id::model` for `architect` role (e.g. `openrouter::meta-llama-3.1-70b:free`).
- `0:01` — OAT: `oat agent tell architect "..." --repo odysseus-fork-but-api-dev` → architect writes plan `plans/fix-cerebras.md`, pushes branch, opens PR #N (no auto-merge).
- `0:10` — `implementer` agent applies diff to `src/provider_presets.py` (this commit’s `free_evidence=paid-risk`), runs `pytest -q tests/test_provider_presets.py` (6 tests).
- `0:15` — `reviewer` agent checks diff, suggests commit message, owner gets **Changes** pane (+/- counters) + **PR** merge button (squash/delete-branch explicit per A-17).
- **Total: 3 OAT agents + 3 LiteLLM role calls + 1 council if reviewer asks for second opinion**. Sequential, each counts against pool budget; no parallel hammering.

---

## 5. Worked failure — 429 mid-task (W-050 requirement)

**Task:** same hard decision as 4.2, but Groq returns `429` at `0:12` with `retry-after: 120`.

```
0:00 Council started — members: openrouter/A, groq/B, google/C; chair = openrouter/D
0:03 openrouter/A ok (410 tokens)
0:08 google/C ok (380 tokens)
0:12 groq/B → 429 + Retry-After 120s (headers: x-ratelimit-remaining-requests: 0, retry-after: 120)
     → auto_router: honour header; no retry on this attempt (retry budget 2, but this is 429, so bounded retry allowed).
     → mark groq/B cooldown-until = now+120s, persist to ledger, report to UI: “Groq is resting until 08:14”.
     → bounded retry #1 after 2s backoff+jitter → still 429 (consumed 1 of 2 retries, counted).
     → bounded retry #2 after 4s backoff+jitter → still 429 (budget exhausted).
     → open circuit-breaker for groq: no calls until cooldown-until, then allow exactly 1 trial.
     → council: groq/B marked declined (not hidden), chair told “Groq declined — rate-limited, resting until 08:14”.

0:15 fanout done with 2/3 (A+C). Proceed to debate with 2 alive; token prompts still include A+C only (no silent Groq text).

0:35 debate done — chair merges A+C, notes: “Groq’s view missing due to rate limit; conclusion rests on 2 members”.

0:45 done — UI shows: 8 calls answered, 2 retries counted, 1 provider resting. Ledger: groq cooldown-until 08:14, rpd_used 999/1000.
     Next message will skip Groq automatically (prefilter checks cooldown-until), so it does not re-hammer.

If *all* free members cooling-down/exhausted: stop with “all free services are resting until <time> — daily free limit reached” (W-050), no loop.
```

**Enforcement locations (minimal):**

- `src/provider_presets.py` guard notes (this commit) — docs + UI hint.
- `src/auto_router._prefilter` — already checks `keep_local`, `vision`, `tools`, `context_length`; minimal addition: skip entries where `cooldown-until > now` or `rpd_used >= guard_rpd`.
- `src/council.py _safe_call` — already catches `_Result(error)`; add `error="429 retry-after …"` → `ok=False, refused=False, error` → chair sees declined.

Full W-015 `Retry-After` + circuit-breaker + token caps + quota ledger + chaos tests belong to Option B, not this minimal doc. This file proves the *policy* is calming (fewer calls on failure, never more).

---

## 6. Where MCP belongs (minimal)

Keep existing Odysseus MCP (`specs/shell-mcp.md`, `routes/mcp/mcp_routes.py`, `src/mcp_manager.py`, `mcp_servers/*`). Do **not** add `harness mcp` to Odysseus; if OAT needs MCP, keep `mcp/oat_mcp_loader.py` in `dionysus`/OAT layer, allow-list read-only tools, expose one `odysseus-mcp` server to OAT workers. Cost: patch `~/.oat/config.toml`, test daemon-launched tool call (W-040).

---

## 7. Security & limits carried forward

- Shell/filesystem tools still unsandboxed (`THREAT_MODEL.md:75` residual). Keep `AUTH_ENABLED=true`, loopback-only for harness, branch rules requiring owner review, token scopes minimal (`WEBWORK_SYNC_TOKEN` needs Contents/Pull-requests/Issues/Workflows write, noted expiry).
- Data-use warnings: Google unpaid may train (note in preset), Mistral Free-mode may train (opt-out). Show in onboarding (A-16 dynamic services would surface this; for now note in providerHub modal).
- Installer trust (A-02) not fixed in minimal — keep guide warning “review before running”.

---

## 8. What’s next (owner names one W-)

This file satisfies W-050’s design requirement for minimal. Next owner choices:

- Promote `guard_*` into `auto_router` prefilter + UI pool state (conditional → show “login-only limits” badge, paid-risk → hide from free-only filter) — 1 PR.
- Or keep docs-only and close minimal with “download planning/ARCHITECTURE.drift.md + patch `provider_presets.py`”.
