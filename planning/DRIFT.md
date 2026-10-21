# Drift log — owner intent → repo changes

> Create one heading per drift decision. The agent must not start a `W-` item without owner naming it (W-001 gate), but drift planning can proceed.

## 2026-10-21 — baseline established

- Source zip unpacked verbatim to `planning/Odysseus API model team kit/` (38 files, `diff -r` clean).
- Upstream synced: `f48aa82` (zip addition) → `594a44f5` merge of `upstream/dev @ 8877273e` (21 commits, 38 files, 0 conflicts). Intermediate fork still at `9712a540`.
- Evaluation + sync report: `ZIP_EVALUATION_AND_SYNC_REPORT.md`.

## Next — owner to choose

<!-- Replace this section with your first drift direction. Examples: -->

- [ ] **Drift: providers** — Groq preset + Google/NVIDIA/Mistral free-evidence fixes
- [ ] **Drift: council** — adaptive council design (W-050) around Odysseus `src/council.py`
- [ ] **Drift: audit** — P0 hardening before trust (W-010…W-015)
- [ ] **Drift: docs-only** — keep planning as reference, no code change

### How to record a drift

```markdown
## YYYY-MM-DD — <short title>

- Baseline: `planning/Odysseus API model team kit/<file>` §X / line Y
- Change: <what you want instead>
- Reason: <owner intent / audit / upstream change>
- Promoted to: <repo path if code, or "planning only">
```

