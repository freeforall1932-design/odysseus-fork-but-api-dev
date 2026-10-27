# Overlap & Drift — Odysseus API model team kit ↔ Odysseus (odysseus-dev/odysseus)

**Date:** 2026-10-27 — branch `arena/745e59b1-odysseus-fork-but-api-dev` at `63f39df` (upstream `8877273e` merged)
**Planning baseline:** `planning/Odysseus API model team kit/` — verbatim 38-file copy of `Odysseus API model team kit.zip` (reports restored)
**Question asked:** *Is there overlapping element (common goal/function/feature) between the planning kit and the original Odysseus, and what should we drift to?*

---

## 1. How this file was built

Read, in order:
- planning kit: `README.md`, `PROJECT_CONTEXT.md` §1–3, `WORKLIST.md` (W-001…W-090), `SESSION_HANDOFF.md`, `RESEARCH_AND_OPEN_QUESTIONS.md` §7 (Q1–Q14), `ODYSSEUS_SOURCE.md` §3 (files Odysseus needs), `reports/CODE_AUDIT_2026-10-17.md` P0/P1, `reports/FREE_PROVIDER_RESEARCH_2026-10-18.md` headline table, `kit/harness/GUIDE.md` flow, `kit/harness/model_scout.py` defaults, `kit/harness/harness.sh` services
- Odysseus app: `README.md` Features, `website/providers-auto-council.md` (Connect/Auto/Council), `src/provider_presets.py` PRESETS, `src/auto_router.py` PoolEntry/route, `src/council.py` MODES/personas, `specs/*.md` index, `UPSTREAM_SYNC.md` downstream manifest, `WORKLIST.md`/`audit.md` (Odysseus’ own audit), `ROADMAP.md`
- Cross-checked: `git diff --name-only source/dev HEAD` (downstream manifest), `git log HEAD..upstream/dev` (now 0)

Everything below cites the file/line it comes from — no inference.

---

## 2. Common goal — 85% overlap in “why”, different “for whom”

| Dimension | Kit (planning) | Odysseus (current) | Overlap? |
|---|---|---|---|
| **Goal statement** | `PROJECT_CONTEXT.md §1`: *small AI team for `gifscythe`*, free/cloud only, beginner-friendly, PR workflow, owner merges. Honest evidence. | `README.md`: *self-hosted AI workspace for chat, agents, research, documents, email, notes, calendar, local model workflows* | **Yes — both want a beginner-usable AI team.** Kit is *narrow* (one target repo, PRs); Odysseus is *general* (workspace for any project + personal tools). |
| **Free/cloud only** | `PROJECT_CONTEXT.md §3`: free tiers + cloud APIs only; local runners/paid not in plan. | `website/providers-auto-council.md`: lists Ollama/LM Studio as *local* options, and `src/provider_presets.py` includes `openai`, `together`, `cerebras` etc. without free check. Odysseus *supports* free, but does not *restrict* to free. | **Partial** — same provider APIs, opposite default. Odysseus even has `ollama`/`lmstudio` local; kit forbids them. |
| **Beginner-friendly** | `GUIDE.md`: one command `harness`, double-click Start/Stop, browser dashboard | `website/setup.md`: `docker compose up` or native `uvicorn`; provider picker is one click from model picker | **Yes** — both aim at “few commands + browser buttons”. Kit’s wording is more step-by-step. |
| **PR workflow, owner is merge gate** | `PROJECT_CONTEXT.md §3`: “owner reviews and merges”, `harness.sh add-repo --mq-enabled=false` | Odysseus has agent tools, shell/filesystem, skills, but *no* OAT PR team built-in. External agents via `routes/codex_routes.py`/`integrations/` can open PRs, but there is no `oat`-like worker fleet. | **No direct equivalent** — Odysseus can *edit code* and *call GitHub*, but does not ship the OAT team abstraction. |
| **Honest evidence** | `PROJECT_CONTEXT.md §1` + `SESSION_HANDOFF.md §3`: tested/not-tested tables | Odysseus audit `audit.md` + `SESSION_HANDOFF.md` do the same: list what was tested (81 focused, 832 security) vs what wasn’t | **Same principle** |

**Conclusion on goal:** If you remove the target repo name (`gifscythe` vs “any workspace”), the *why* is identical. Drifting should keep the *why* and choose one *for whom*.

---

## 3. Function/feature overlap — detailed map

### 3.1 Provider onboarding & model selection

| Kit | Odysseus | Overlap assessment |
|---|---|---|
| `kit/harness/model_scout.py` DEFAULTS providers: `openrouter`, `nvidia`, `mistral`, `google` (4). Paced probing: one model at a time, pause, budgets; ranking for 3 roles `architect/implementer/reviewer` with weights, `min_context` 64k/128k; writes `~/.litellm/config.yaml` for LiteLLM. `exclude` regex for non-chat models. | `src/provider_presets.py` PRESETS: 15 — `openrouter`, `google`, `openai`, `anthropic`, `groq`, `mistral`, `deepseek`, `together`, `cerebras`, `nvidia`, `xai`, `huggingface`, `ollama`, `lmstudio`, `custom`. `routes/provider_routes.py` `POST /api/providers/models` lists models for a key *without saving*; saving via existing `POST /api/model-endpoints` with `pinned_models`. Free detection only for OpenRouter (pricing `0`). Google is explicitly “*Whether a model is free depends on your quota, so it is not flagged*”. | **Same primitive (pick provider → paste key → see models → save).** Kit is *narrower* (4 providers, free-only) but *deeper* (probing, ranking, LiteLLM generation). Odysseus is *broader* (15 presets, local included) but *shallower* (no probing/ranking — user ticks models manually; no LiteLLM scout). **Drift opportunity:** port kit’s `FREE_PROVIDER_RESEARCH` evidence rules + `model_scout` free-eligibility + guard defaults into `provider_presets.py`/`auto_router.py` (W-015 → Odysseus). |
| Kit W-015: per-provider evidence rules, free-eligible vs conditional vs paid-risk vs unknown; guard defaults (requests/min, cooldown, `Retry-After`, circuit breaker, quota ledger) | Odysseus `src/auto_router.py`: `PoolEntry.free`, `prefilter`, `route` via router model, `looks_like_refusal`, but no `Retry-After`, no per-provider `429` ledger, no token caps. `website/providers-auto-council.md: Known limits: non-streaming council/router` | **Missing in both**, but kit has dated research (2026-10-18) that Odysseus can reuse directly. Strongest drift candidate. |
| Kit `harness.sh` SERVICES fixed list `openrouter nvidia mistral google` + `env_name()`/`valid_service()` | Upstream manifest says `app.py` only adds 4 lines for provider/auto routes; `static/index.html` adds 1 script tag; downstream manifest is minimal — easy to extend | Low conflict — adding kit’s providers to Odysseus is additive. |

### 3.2 Auto routing / model pool

| Kit | Odysseus | Overlap |
|---|---|---|
| `harness.sh` `scout` writes router config; LiteLLM 3 stable role names `architect/implementer/reviewer`; fallback separate one-key dicts; `stickiness` 0.04, `max_per_provider` 2 | `src/auto_router.py` `PoolEntry` (endpoint+model+local/free/context/vision/tools), `prefilter` (vision/tools/context/keep-local), `route` (asks router model `{"pick": n}`), `PUT /api/auto/pool` max 60, `POST /api/auto/route` → `{endpoint_id,model,reason,source}` | **Same concept, different executor.** Both have “pool → router picks → answer”. Kit’s router is *external* LiteLLM; Odysseus’ is *embedded* `auto_router.py` called per-message. **Keep-local hard** is identical in both (never fall through; HTTP 409 if no local). Kit’s `max_per_provider` ≈ Odysseus’pool size limit 60 (both prevent one service dominating). |
| Kit intended: quota-aware pool + online Colab/KoboldCpp as core pool member while online, API fallback when offline; `WORKLIST.md` W-030 defines endpoint kind `owner-started session`, health, short-lived URL, session expiry | Odysseus currently has no Colab concept; `ollama`/`lmstudio` are local, but address check is loopback/private-LAN/Tailscale heuristic (`website/providers-auto-council.md: “Local is …”`). Custom URL can be any OpenAI-compatible — could host Colab tunnel *today* but with no health/session/expiry handling. | **No overlap yet — pure drift.** Kit’s Colab design (W-021/Q14 terms research + W-030 spec) is transferable as a new `provider_presets.py` flavor `colab/koboldcpp` with `local=False, needs_key=False`, `base_url` = tunnel URL, `W-015 guard` (one in-flight, cooldown, fallback). But both sides mark it unverified (no official terms proof). |

### 3.3 Council / personas / debate

| Kit | Odysseus | Overlap |
|---|---|---|
| `PROJECT_CONTEXT.md §3` + `RESEARCH_AND_OPEN_QUESTIONS.md §1A`: adaptive council by default — (1) one model simulates personas for light Q, (2) 2–3 real models deliberate for hard Q, (3) OAT agents for PR execution. W-050 design only (no code). Owner sees other multi-agent systems as benchmark but wants Odysseus-simpler. | `src/council.py` already implements `fanout` (parallel), `debate` (read others anonymised/shuffled, revise, chair merges), `verify` (worker drafts → members review → chair verdict), personas `Researcher/Logician/Contrarian/Builder` + custom, 4 default, `CHAIR_SYSTEM`/`REVIEW_SYSTEM` prompts, `skill_scope: chair|all`, `MAX_MEMBERS 8`, `MAX_ROUNDS 3`, streams `start→draft→member→round_done→chair→done`. Tests `test_council.py` (287 lines) + `WORKLIST.md W-050` expects call-count examples (light/hard/PR + 429 example). | **Odysseus already built the kit’s “next destination”.** The kit’s adaptive thresholds (when to escalate 1→2→3) + provider-pool budget + “OAT is executor” mapping is the *only* thing Odysseus lacks. **Drift = document + wire** — add council escalation policy (W-050 design doc) and a router→council bridge that selects `simulated vs real council` based on `needs_tools?`, `keep_local?`, pool health, and a per-task budget (tokens/calls). No new council engine needed. |
| Kit Q11 personas: “The Agency” repo licence Q4 | Odysseus `DEFAULT_PERSONAS` are exactly Agency-style roles, but baked into council — no licence check needed | Drop kit’s Agency import; use Odysseus personas directly. |

### 3.4 Harness / agent team / dashboard

| Kit | Odysseus | Overlap |
|---|---|---|
| `install.sh` → `uv`+LiteLLM+OAT, `harness` symlink, `skills` install | `setup.py` + `app.py` uvicorn, `requirements.txt` (includes `chromadb-client`, `fastembed`, `yt-dlp`), `install-service.sh` | **Different runtimes** — keep separate. Don’t port installer; use Odysseus native recipe (`website/setup.md`). |
| `harness.sh` 665 lines: `start/stop`, `scout`, `check`, `doctor`, `add-repo`, `github-login`, `connect-oat`, lifecycle, health `curl -s` (audit A-05/A-06/A-09/A-10) | Odysseus has `src/background_tool_jobs.py`, `src/bg_jobs.py`, `routes/`, admin settings, `static/js/*` — but no harness lifecycle. `WORKLIST.md` audit A-05/A-06/A-07/A-12 are harness-specific. | **No overlap** — harness is OAT glue; Odysseus agents are `agent_loop.py`/`agent_tools`/`agent_runtime`. If you want PR team, keep OAT *outside* Odysseus (as kit originally did) and call Odysseus as council via HTTP. W-051 `harness mcp`/`harness add-endpoint` would duplicate `src/mcp_manager.py`. |
| `harness_ui.py` 1273 lines: Chat, Tasks, Ask, Files, Changes, PRs, Models, Connections, Skills, Logs; single-flight missing (A-07), skill symlink bypass (A-08) | `static/index.html` + `static/js/providerHub.js` (696 lines) + `static/js/chat.js` + per-feature panels; `website/providers-auto-council.md`: one modal, 3 tabs, Pool/Council buttons, Auto/Keep-local switches | **UI overlap is exactly the file that already landed in Odysseus** (manifest: `providerHub.js` is downstream-only). Don’t rebuild kit dashboard inside Odysseus — reuse providerHub. |
| `skills/self-extend` + `skills/team-workflow` templates (`HANDOFF.md`, `WORKLIST.md`, `IMPROVEMENT_LOG.md`, `worker-prompt-extension.md`) | `specs/memory-skills.md`, `docs/skills-lifecycle.md`, `docs/skills-audit-architecture.md`, `services/skills/` (evaluation/audit/runner/job_coordinator), `routes/skills_routes.py`, GitHub skill import | **Same pattern (SKILL.md under data dir)**, different scope. Kit skills are *project-memory discipline*; Odysseus skills are *audited publication + evaluation*. Consolidation idea: keep Odysseus skill lifecycle as source of truth; add kit’s `team-workflow` as one more skill (no code change in Odysseus). |

### 3.5 MCP, tools, shell

| Kit | Odysseus | Overlap |
|---|---|---|
| W-040: rebuild `mcp/oat_mcp_loader.py` + `oat_mcp_apply.py`, `harness mcp` allow-listed, reversible, read-only first. Not present (lost). | `specs/shell-mcp.md`, `routes/mcp/mcp_routes.py`, `src/mcp_manager.py`, `src/builtin_mcp.py`, `mcp_servers/email_server.py` etc., already shipped and tested. | **Odysseus is ahead.** Don’t port kit MCP — if OAT MCP is wanted, implement it in `dionysus`/`oat` layer and expose one Odysseus MCP server for OAT workers via `odysseus-mcp` launcher. Keep concerns separate. |

### 3.6 Toolchains, guide, packaging

| Kit | Odysseus | Overlap |
|---|---|---|
| W-060 `toolchains.sh` (Qt6/CMake/Ninja/g++/Xvfb/dotnet-8/clangd/Node), W-070 GUIDE.md, W-080 repackage ZIP with hashes | `ROADMAP.md` already lists Cookbook SGLang, hardware-fit ranking, speculative decoding, prompt-injection audit — *toolchains are not in ROADMAP*. Odysseus has no Qt/CMake focus (except `gifscythe` is external). | **No overlap** — keep kit toolchains in `dionysus`/`gifscythe` world; don’t add them to Odysseus. Guide/packaging stay in kit. |

---

## 4. What to drift — three concrete options

### Option A — Minimal (recommended first, 1–2 days)

**Keep kit as reference only; make two surgical improvements to Odysseus that the kit already researched:**

1. **Providers:** add Groq preset *for real* (kit verified free), mark `google` as per-model free, add guard defaults from `FREE_PROVIDER_RESEARCH` into `provider_presets.py` (RPM/RPD, `Retry-After`, one in-flight default). File: `src/provider_presets.py` PRESETS + `website/providers-auto-council.md` table.
2. **Council docs:** add `planning/ARCHITECTURE.drift.md` that maps kit adaptive thresholds → Odysseus `council.py` modes, with call-count examples required by W-050 (light=1 simulated, hard=2–3 real debate, PR=fanout+chair). No code.

*Why first:* smallest diff to downstream manifest, leverages the kit’s only *verified* output (free-tier table) without touching lifecycle/skills.

### Option B — Integrated pool + council (2–4 weeks, W-015/W-050)

**Make Odysseus the quota-aware pool the kit wanted but never built:**

- Extend `src/auto_router.py` `PoolEntry` with `free_evidence: eligible|conditional|paid-risk|unknown`, `quota_ledger` (attempts, last 429, cooldown-until), `capability` (tools/vision), `health/cooldown` (W-015). Render guard settings (RPM, cooldown, one-in-flight) from `FREE_PROVIDER_RESEARCH` table; persist small ledger so restart doesn’t re-hammer provider (kit chaos tests: 429+Retry-After, 5xx storm, timeout, refused key, exhausted quota — each proves *fewer* calls, not more).
- Add adaptive escalation in `routes/auto_routes.py`: `needs_tools`+`has_image`+`keep_local`+pool health → pick `fanout(1 simulated)` vs `debate(2–3 real)` vs `verify(worker=offline)`. Chair is separate seat; members never vote; answers anonymised/shuffled (already in `council.py` — reuse).
- Optional Colab: new preset `colab-koboldcpp` with `base_url` = tunnel URL, health check, short-lived URL, session expiry, capability limits, API fallback — but only after W-021 terms research (Q14 open) confirms allowed use; otherwise keep as `custom` URL with manual fallback.
- Add `POST /api/auto/pool` guard: `keep_local` hard (already), daily budget, per-task call/token ceiling + reserve (kit W-050 “no task drains the day”, plain status “resting until 14:32”).

*Files touched:* `src/provider_presets.py`, `src/auto_router.py`, `routes/auto_routes.py`, `static/js/providerHub.js` (pool state: free evidence, cooling-down, fallback), `website/providers-auto-council.md`.

### Option C — Full kit-in-Odysseus (discard — do not do)

Re-implement `harness.sh` lifecycle, `harness_ui.py` dashboard, OAT team, `toolchains.sh` inside Odysseus. **Not recommended:** duplicates `install-service.sh`/`setup.py`, reintroduces audit P0s (secrets, PID, skill symlinks), conflicts with `ROADMAP.md` (Cookbook/SGLang vs Qt/CMake), and expands downstream manifest beyond mergeable size. Keep OAT outside Odysseus; call Odysseus council via HTTP if a PR worker needs a decision.

---

## 5. Recommended drift sequence (owner names one W- at a time)

```text
A1 (providers guard) → A2 (council escalation doc) → B-pool (quota ledger) → B-council (adaptive bridge) → B-colab (only if W-021 permits) → re-evaluate W-001
```

- Each step: update `planning/DRIFT.md`, add one `planning/WORKLIST.drift.md` entry, implement, run `upstream-sync --check-only` + `pytest -q tests/test_provider* tests/test_auto_router tests/test_council tests/test_provider_and_auto_routes` (200 tests), record tested/not-tested in `SESSION_HANDOFF.md`.
- Never run `install.sh`/`harness` in the Odysseus checkout; keep runtime state (`keys.env`, `scout_state.json`, `.env`, `data/`) out of git (already in `.gitignore`).
- When ready, ask the agent to `promote planning/patches/<name>` into a real downstream file and run the manifest check: `git diff --name-only source/dev HEAD` must still match `UPSTREAM_SYNC.md` manifest (+ the new planning docs you explicitly allow).

---

## 6. Files to keep / drop / reuse

| Keep as reference (planning) | Promote to Odysseus (small patches) | Drop / keep in dionysus |
|---|---|---|
| `planning/Odysseus API model team kit/WORKLIST.md` (queue), `CODE_AUDIT` P0 for awareness | `FREE_PROVIDER_RESEARCH` guard table → `provider_presets.py`; adaptive thresholds → `auto_router.py`/`council.py` bridge | `kit/harness/install.sh`, `harness.sh`, `harness_ui.py`, `model_scout.py` — do not copy; they target OAT+LiteLLM, not Odysseus agents |
| `RESEARCH_AND_OPEN_QUESTIONS.md` Q1–Q14 | `ODYSSEUS_SOURCE.md` pin `951d57d` → update to `63f39df` after verification | `toolchains.sh`, GIFSCYTHE planning/report, gifscythe review — gifscythe-only |
| `SESSION_HANDOFF.md` gate W-001 | `PROJECT_CONTEXT.md` §3 “Errors must calm” → encode as `auto_router` chaos tests | `archive/*` — history only |

---

## 7. Immediate next step — pick one

> If the owner replies “next” or “continue” alone, the agent must ask which option.

- **Option A1** — Owner says “drift providers guard” → I’ll patch `src/provider_presets.py` with Groq + free-evidence labels + guard defaults from the dated research and add one test that `assume_free` is gone for `mistral/nvidia/google`.
- **Option A2** — Owner says “drift council doc” → I’ll write `planning/ARCHITECTURE.drift.md` with the W-050 call-count examples (light/hard/PR + 429 failure minute-by-minute) and a PR against `website/providers-auto-council.md`.
- **Option B** — Owner says “drift full quota-aware pool” → I’ll start with the small `PoolEntry` ledger + one in-flight-per-provider + `Retry-After` handling, with chaos tests that prove attempt count stays within budget.
