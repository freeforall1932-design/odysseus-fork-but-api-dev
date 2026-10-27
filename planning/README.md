# Planning folder — drift base from `Odysseus API model team kit.zip`

**Source:** `Odysseus API model team kit.zip` (261,906 bytes, 51 members, extracted 2026-10-21) — the live team-kit project originally under `workbench/projects/ai-team-kit` in `dionysus`, now the fourth portable drop-in (`freeforall1932-design/dionysus` @ `9b5e0e6`).

**Copy:** `planning/Odysseus API model team kit/` is a verbatim copy of the unpacked kit (38 payload files + manifest-equivalent). Verified `diff -r` → no diff. Keep this as the **baseline**; drift edits go in new files or in `planning/DRIFT.md`, not by overwriting baseline without record.

## How to use

1. **Do not edit `planning/Odysseus API model team kit/` directly** — treat it as read-only reference (original `README.md`, `WORKLIST.md`, `PROJECT_CONTEXT.md`, `RESEARCH_AND_OPEN_QUESTIONS.md`, `ODYSSEUS_SOURCE.md`, `reports/*`, `kit/harness/*`).
2. **Drift toward what you want** by creating new docs in `planning/`:
   - `planning/DRIFT.md` — one-line decisions: what to keep, drop, or change (e.g. “keep provider pool, drop OAT merge-queue, add Odysseus council as default”).
   - `planning/WORKLIST.drift.md` — your fork of `WORKLIST.md` with only your chosen `W-` items.
   - `planning/ARCHITECTURE.drift.md` — your target architecture (pool + council + Odysseus surface).
   - Any prototype patches stay in `planning/patches/` until you promote them to `planning/Odysseus API model team kit/kit/harness/` or to the Odysseus app (`src/`, `routes/`, `static/js/`).
3. **Traceability**: every drift file must cite the baseline file/line it changes and the reason (owner intent, audit finding, or new requirement).

## Upstream sync status at time of drift creation

- This repo’s `origin/main` was at `f48aa82 Add files via upload` (which = `951d57d` sync PR #15 @ `9712a540` + the zip).
- Now synced to **upstream `odysseus-dev/odysseus` `dev` @ `8877273e`** (2026-10-20, PR #6742 email export) via merge `594a44f5` — **21 commits, 38 files, 0 conflicts**.
- Intermediate fork `freeforall1932-design/odysseus-fork-but-api` `dev` @ `9712a540` is still 21 behind; the merge above went directly from `upstream/dev` (owner-controlled fork update is still pending if you want to restore the normal topology).
- Verification on the merged tree: `upstream-sync --check-only 27 passed`, downstream Auto/Council `176 passed` (see `ZIP_EVALUATION_AND_SYNC_REPORT.md` for dry-run log).

## Next actions — pick one to tell the agent

- `drift: providers` — map `FREE_PROVIDER_RESEARCH_2026-10-18.md` → `src/provider_presets.py` + `routes/provider_routes.py` (add Groq preset, fix free-evidence for Google/NVIDIA/Mistral, encode W-015 guard defaults).
- `drift: council` — design `W-050` adaptive council (simulated personas → small real council → OAT) with `ODYSSEUS_SOURCE.md` pin `951d57d` + current `src/council.py`.
- `drift: audit-p0` — cherry-pick `CODE_AUDIT_2026-10-17.md` P0s into this repo (secrets, installer pinning, lifecycle, dashboard jobs, skill symlinks).
- `drift: minimal` — keep only the planning reference and do not integrate the kit into Odysseus (docs-only drift).

## Files

```
planning/
├─ README.md                         ← this file
├─ DRIFT.md                          ← create next: your decisions
├─ Odysseus API model team kit/      ← verbatim kit (read-only baseline)
│  ├─ README.md                      status + verdict
│  ├─ SESSION_HANDOFF.md             gate: W-001
│  ├─ WORKLIST.md                    queue W-001…W-090
│  ├─ PROJECT_CONTEXT.md             goal + decisions
│  ├─ RESEARCH_AND_OPEN_QUESTIONS.md Q1–Q14, A1–A11
│  ├─ READING_GUIDE.md               10-min/45-min paths
│  ├─ FILE_MAP.md                    where everything went
│  ├─ ODYSSEUS_SOURCE.md             pinned Odysseus repo @ 951d57d
│  ├─ kit/harness/                   v1 harness source
│  ├─ reports/CODE_AUDIT_2026-10-17.md
│  ├─ reports/FREE_PROVIDER_RESEARCH_2026-10-18.md
│  ├─ reports/KIT_LEARNING_AND_CHAT_MATCH.md
│  ├─ reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md
│  └─ archive/                       snapshots + harness-zip extras
└─ (your drift files)                ← add here
```

The planning folder is intentionally **outside** the Odysseus app tree (`app.py`, `routes/`, `static/`) so it does not affect the app’s downstream manifest or CI until you explicitly promote a change.
