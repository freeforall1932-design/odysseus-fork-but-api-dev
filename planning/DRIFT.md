# Drift log — owner intent → repo changes

> Create one heading per drift decision. The agent must not start a `W-` item without owner naming it (W-001 gate), but drift planning can proceed.

## 2026-10-21 — baseline established

- Source zip unpacked verbatim to `planning/Odysseus API model team kit/` (38 files, `diff -r` clean).
- Upstream synced: `f48aa82` (zip addition) → `594a44f5` merge of `upstream/dev @ 8877273e` (21 commits, 38 files, 0 conflicts). Intermediate fork still at `9712a540`.
- Evaluation + sync report: `ZIP_EVALUATION_AND_SYNC_REPORT.md`.

## 2026-10-27 — minimal drift (Option A) applied

- Baseline: `planning/Odysseus API model team kit/reports/FREE_PROVIDER_RESEARCH_2026-10-18.md` §1–6 + `src/provider_presets.py` PRESETS
- Change: added `free_evidence`/`guard_*` to `ProviderPreset`, updated notes for openrouter/google/groq/mistral/cerebras/nvidia with W-020 dated evidence (limits, 401/429/402 signals, daily ledger, training warnings); see `src/provider_presets.py` diff
- Reason: W-015 “assume_free” → evidence rule; minimal step before full quota ledger
- Promoted to: `src/provider_presets.py` (upstream-synced, 176 downstream tests pass)

- Baseline: `planning/Odysseus API model team kit/WORKLIST.md` W-050 + `PROJECT_CONTEXT.md §3` adaptive council
- Change: wrote `planning/ARCHITECTURE.drift.md` — roles (Odysseus room, OAT PR team, LiteLLM), 3 escalations (1 simulated → 2–3 real debate → OAT sequential), pool table per provider, quota ledger design, 3 call-count examples (light 2 calls/1.1k tok, hard 10 calls/12k tok, PR 3 agents), worked 429 minute-by-minute with Retry-After + circuit breaker + plain “resting until” message
- Reason: satisfy W-050 design requirement without implementation; keep calming-on-error policy
- Promoted to: `planning/ARCHITECTURE.drift.md` (docs-only, no runtime)

## Next — owner to choose (after minimal)

- [ ] **Drift: providers-pool** — wire `free_evidence`/`guard_*` into `auto_router.prefilter` (skip cooldown/rpd_used, one in-flight) + UI badges
- [ ] **Drift: audit** — P0 hardening (W-010…W-015) before trust
- [ ] **Drift: docs-only** — keep planning as reference, close

### How to record a drift

```markdown
## YYYY-MM-DD — <short title>

- Baseline: `planning/Odysseus API model team kit/<file>` §X / line Y
- Change: <what you want instead>
- Reason: <owner intent / audit / upstream change>
- Promoted to: <repo path if code, or "planning only">
```

