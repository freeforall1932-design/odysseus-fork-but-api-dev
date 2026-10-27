# Zip evaluation + dionysus testing + upstream sync — 2026-10-21

> Branch: `arena/745e59b1-odysseus-fork-but-api-dev` (HEAD = `f48aa82 Add files via upload`)
> Date: 2026-10-21 Asia/Jakarta

## 1. What was in the zip

The file `Odysseus API model team kit.zip` (261,906 bytes, 51 members) was unpacked to `/tmp/unpack/Odysseus API model team kit/` and compared to the live copy in `https://github.com/freeforall1932-design/dionysus` at `/Odysseus API model team kit/` — they are **byte-identical** (38 payload files + manifest).

### Contents

| Path | Purpose |
|---|---|
| `README.md`, `READING_GUIDE.md`, `SESSION_HANDOFF.md`, `PROJECT_CONTEXT.md`, `WORKLIST.md`, `FILE_MAP.md`, `MIGRATION.md`, `ODYSSEUS_SOURCE.md`, `RESEARCH_AND_OPEN_QUESTIONS.md` | Curated docs — the “slim” re-organisation of the old `HANDOFF.md/PROVEN.md/OPEN.md/FILES.md` snapshots (archive/2026-10-16-handoff-snapshot) + the former `2026-10-17-next-session-readme.md`. |
| `kit/harness/` (16 files: `harness.sh`, `harness_ui.py`, `model_scout.py`, `install.sh`, `GUIDE.md`, skills, launchers) | **Canonical v1 kit** extracted byte-for-byte from `ai-team-kit.zip`. Not edited during audit. |
| `archive/harness-zip-extras/` (4 files) | The 4 extra docs that were only in `harness.zip` (planning report, guide lineage, review, draft query). |
| `reports/CODE_AUDIT_2026-10-17.md` | Static audit (26 findings A-01…A-26, P0–P2) with verification commands. |
| `reports/FREE_PROVIDER_RESEARCH_2026-10-18.md` | **W-020** desk research on 8 providers from official pricing/terms (no signups/keys). |
| `reports/KIT_LEARNING_AND_CHAT_MATCH.md` | How v1 works + old-chat claim matching + one isolated scout self-test (62 passed, 0 failed, LiteLLM skipped). |
| `reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md` | Owner’s own old-chat requests quoted/extracted. |

Full inventory and SHA-256 hashes are in `FILE_MAP.md` §5 and `KIT_LEARNING_AND_CHAT_MATCH.md` Appendix A. The dionysus copy was added as the **fourth portable drop-in** in PR #4 (commit `17139af`, 2026-10-18).

## 2. Is it useful? — verdict: **conditionally useful, in the right repo**

### For `odysseus-fork-but-api-dev` (this repo) — **not directly useful as code to commit**

- This repo is the **Odysseus application itself** (FastAPI workspace + agents, `app.py`, `routes/`, `services/`, `static/`). The zip’s harness (`kit/harness/*`) is a **separate project** that *orchestrates* OAT + LiteLLM + scout + dashboard to produce PRs *against* a repo like this one. It does not integrate into Odysseus by being dropped into the root.
- `ODYSSEUS_SOURCE.md` inside the zip **points to this repo** (`freeforall1932-design/odysseus-fork-but-api-dev` @ `951d57d`) as “the Odysseus aka the program file” — the relationship is pointer, not vendoring. W-050/W-051 explicitly say Odysseus integration is *not yet implemented* and must pass a design comparison (Odysseus vs OpenCode vs Goose vs OAT).
- The zip’s `WORKLIST.md` documents 22 open work items (W-010…W-090). None are authorized just by being listed; the owner must name one `W-` item (W-001 gate).
- **Committing the zip file itself at the repo root (`Odysseus API model team kit.zip`) violates the downstream manifest** in `UPSTREAM_SYNC.md`: that manifest lists exactly which files may differ from upstream (`app.py` 4-line router include, `static/index.html` 1-line script, `static/sw.js` precache bump, etc.). A root zip is not in that allow-list and will be flagged as “downstream leaked” in `git diff --name-only source/dev HEAD`.
- If you want the research, keep it as **reference docs outside the application tree** (e.g. `docs/reference/ai-team-kit/`), or just read it from `dionysus` — do not ship the binary zip in `main`.

### When it *is* useful

- **Provider pool design**: `FREE_PROVIDER_RESEARCH_2026-10-18.md` is the only dated, official-source verification of what “free” means per provider (OpenRouter `:free` 20/min 50/day → 1000/day after 10 credits; Groq free; Google per-model Flash + training-use; NVIDIA trial unpublished; Mistral monthly allowance; Cloudflare 10k Neurons/day; Cerebras **no permanent free tier**; GitHub Models **retired**). Its per-provider evidence rules and guard defaults (`requests/min`, `in-flight cap`, `cooldown`, `Retry-After`, circuit breaker) are exactly what `W-015` must encode into `kit/harness/model_scout.py` and what `W-050` must design for Odysseus’ router. Odysseus’ own `src/provider_presets.py` currently lists presets but does not enforce those free-tier limits — cross-reference with this report before expanding presets.
- **Worklist as roadmap**: W-010…W-016 (P0 hardening: secrets, installer pinning, lifecycle, dashboard jobs, skill symlinks, scout free-evidence) must pass before trusting a real install. The kit is *not runtime-proven* (audit tested only static parsing + one scout self-test; no installer/LiteLLM/OAT/dashboard/provider/GitHub/platform run).
- **Dionysus context**: the zip is the “live team-kit project” that dionysus now serves as its fourth drop-in. If your task is to work on `dionysus`, the folder at `/Odysseus API model team kit/` *is* the correct place.

**Bottom line**: keep the zip in `dionysus` (its home), read its research before adding any provider or council feature to Odysseus, but do **not** bundle it into `odysseus-fork-but-api-dev`’s `main`.

## 3. https://github.com/freeforall1932-design/dionysus — testing coverage

Dionysus is designated “skills testing ground” (not an application). Recent state (branch `dionysus`, HEAD `9b5e0e6` PR #4 merged 2026-10-19T22:56Z):

- **Portable drop-ins**: `package_dropins.py` builds 4 deterministic ZIPs (gifscythe, shotgun-king-anew, skills, `Odysseus API model team kit`), each with `DROPIN_MANIFEST.sha256`, byte-verified after extraction, symlink-free, reproducible (`date_time=(2026,10,18,0,0,0)`).
- **Recorded verification on 2026-10-18**:
  - `workbench` validator: **376 passed, 0 failed**
  - portable skills gate: **74 passed, 0 failed** (also after independent extraction)
  - packaging suite: **5 passed** (deterministic archives, real roots/legacy symlinks, symlink-refusal, output containment)
  - `python -m compileall` on live roots/workbench: passed
  - Qt lint self-test: PASS
  - magnet-excavator: **142 passed**
- **What it does NOT prove**: live installation, provider quotas/keys, LiteLLM/OAT compatibility, Odysseus runtime, model quality, real Colab GPU/model/tunnel, game/GUI acceptance, or with/without-skill uplift (explicitly listed “Not verifiable here” in `MIGRATION_SESSION.md` and `MIGRATION.md`).
- **For the team kit**: the fourth drop-in was added unchanged (38 files); nested `kit/harness/skills` are kept as project-specific runtime assets, not as competing copies of the root `skills/` catalog.

## 4. Upstream sync status — are we latest?

### Topology (from `UPSTREAM_SYNC.md`)

| Remote | Repo | Branch |
|---|---|---|
| `origin` | `freeforall1932-design/odysseus-fork-but-api-dev` (this repo) | `main` |
| `source` | `freeforall1932-design/odysseus-fork-but-api` (intermediate fork, owner-controlled) | `dev` |
| `upstream` | `odysseus-dev/odysseus` (original) | `dev` (curated `main` there) |

One-time history link: merge `0f5c3c94` (PR #10, 2026-10-14, upstream `86b886c6`) grafted the ZIP-seeded history onto upstream. Current tip:

```
f48aa82 Add files via upload (2026-10-21T03:40 +07)  ← HEAD / origin/main / arena branch
  └─ 951d57d Merge PR #15 (sync @ 9712a540)         ← previous sync PR #15
     └─ 8c5e9e70 Merge upstream fork dev @ 9712a540 into main
        └─ 9712a540 Merge PR #6434 fix/5598-oauth-expired-state (2026-10-16T19:05 +03)
```

- **This repo vs `source/dev`**: `git merge-base HEAD source/dev` = `9712a540`, `git log HEAD..source/dev | wc -l` = **0** — **fully synced to the intermediate fork’s latest**. The only local addition on top of that sync is the zip file itself (verified `git diff 951d57d f48aa82 --stat` shows only `Odysseus API model team kit.zip` +0/-0).
- **This repo vs `upstream/dev`**: `git log HEAD..upstream/dev | wc -l` = **21** — **behind upstream** by 21 commits (latest upstream = `8877273 Merge PR #6742 email export` 2026-10-20). This is expected: the fork has not yet been advanced.
- **`source` vs `upstream`**: `git log source/dev..upstream/dev | wc -l` = **21** identical list — all 21 are email, iOS safe-area, scheduler, governance, etc. (see §5).

### Dry upstream merge (2026-10-21, from HEAD to `upstream/dev`)

```
git fetch --unshallow origin; git fetch source; git fetch upstream
git merge-tree --write-tree --name-only HEAD upstream/dev  →  af24adb9 (exit 0)
git merge --no-ff --no-commit upstream/dev                 →  Auto-merging static/index.html / static/js/chat.js; Automatic merge went well
conflicted files: 0
staged: 38 files, 3207 insertions(+), 162 deletions(-)
```

No conflicts — manifest-critical downstream files (`app.py` router includes, `static/index.html` providerHub script tag, `static/sw.js` precache, `static/js/chat.js` heuristic) auto-merged. Detailed list:

- `CONTRIBUTING.md`, `docs/maintainers/**` (8 new files), `frontend/src/features/notes/ui/panel.js`, `routes/email/email_routes.py`, `src/task_scheduler.py`, `src/tools/system.py`, 7 CSS files, `static/index.html`, `static/js/chat.js`, 5 `static/js/**`, `tests/css_snapshot/baseline.json`, `tests/test_email_library_bulk_actions.py`, `tests/test_email_library_print_browser.cjs`, `tests/test_manage_tasks_admin_action_policy.py`, `tests/test_scheduler_research_settings_guard.py`.

Quick gate on current HEAD: **27 passed, 0 failed** (`python .github/scripts/upstream_sync.py --check-only`); downstream suites on this HEAD: **176 passed**.

### Recommendation — do not auto-merge upstream into this repo directly

Per the runbook: **update the intermediate fork first**, then let the automation bring it here:

1. **Owner step** (requires write on the fork):
   ```bash
   gh repo sync freeforall1932-design/odysseus-fork-but-api --branch dev
   ```
   If `gh repo sync` refuses (“fork has its own commits”), do not `--force` without owner consent; report `ahead_by/behind_by` from `gh api repos/freeforall1932-design/odysseus-fork-but-api/compare/source/dev...dev`.

2. **This repo** (automated): `.github/workflows/upstream-sync.yml` runs daily at 02:17 UTC + on every push to `main` + manual dispatch. It will detect `main` is behind the fork’s `dev`, rebuild `sync/upstream` as `main` + merge of `source/dev`, run `--check-only`, push with `--force-with-lease`, and open/refresh one PR (`chore(sync): …`, label `upstream-sync`, `Part of #<tracking issue>`). Manual fast path is in `UPSTREAM_SYNC.md` §Fast path.

3. **If you need it immediately** (not via fork):
   ```bash
   git fetch upstream --no-tags
   git merge-tree --write-tree --name-only HEAD upstream/dev   # must be 0 conflicts
   git merge --no-ff --no-commit upstream/dev
   # verify: python .github/scripts/upstream_sync.py --check-only
   #         python -m pytest tests/test_auto_router.py tests/test_council.py ...
   git commit -m "Merge upstream fork odysseus-fork-but-api (dev @ <short-sha>) into main …"
   ```

Do **not** push the dry merge we just tested to `main` without the owner’s fork update — it would bypass the owner’s control plane. If you do push a sync, never squash/rebase it (dropping the merge link re-disconnects histories and makes the next sync conflict everywhere; see Appendix A).

### About the committed zip

If the intent is to keep a reference, consider:

- Remove `Odysseus API model team kit.zip` from `main` (it lives canonically in `dionysus` dropins), add `*.zip` to `.gitignore` or add the path to the allow-list in `.github/scripts/upstream_sync.py`’s manifest + `DOWNSTREAM_MANIFEST` table in `UPSTREAM_SYNC.md` so `--check-only` and future PR checks do not flag it as leaked drift.
- For reviewers: document in `SESSION_HANDOFF.md` why the zip was added and that it was built reproducibly (see dionysus `package_dropins.py`).

## 5. New upstream commits not yet in this repo (21 since 9712a540)

```
8877273 Merge pull request #6742 from odysseus-dev/codex/review-7011-email-export-20261015 (2026-10-20)
377070a fix(email): propagate preflight safety failure across all mailbox groups
f06ec5d Merge branch 'upstream/dev' into fix/pr-6742-email-export
057ae92 fix(email): support case-insensitive IMAP atoms and portable browser discovery
75df766 fix(email): harden RFC822.SIZE preflight validation and ignore duplicate IMAP records
c7d1555 fix(email): resolve memory safety, print rendering, and accounting defects
550ac01 fix(email): enforce account ownership and correct partial failure accounting
8eaf742 fix(email): replace html2pdf with Print / save PDF and harden EML export
8363919 Merge pull request #6736 from alteixeira20/docs/maintainer-handbook-governance-v1
ae238b7 Merge pull request #6396 from Gr33ndev/dev
63e18a4 test(css): update snapshots for iOS safe-area layout
268636c Merge pull request #6473 from ShahabAhmed01/fix/scheduler-research-settings-guard-5049
b2613b2 fix(ui): respect iOS safe areas, screen height and landscape layout
c1d90be fix(scheduler): catch OverflowError on non-finite research settings
8946100 Merge current dev into PR #6473
88772b3 fix(tasks): apply the admin-only action policy in manage_tasks (#6358)
55b5b7f docs(maintainers): list website/ in the docs map and align CONTRIBUTING
b97c1ee docs(maintainers): refine handbook and remove code of conduct
6cf676d feat(email): export selected messages as email or PDF
a0137b4 docs(maintainers): publish governance handbook draft and review playbook
35e3b29 fix(scheduler): fall back to defaults for non-numeric research settings
```

All touch email/export, governance docs, iOS/CSS, scheduler guards — no provider/Auto/Council code — so downstream Auto/Council integration risk is low, but the dry merge above still proves it is safe.

## 6. Testing performed for this report

- Full history fetched (unshallowed) and verified graft integrity.
- `git diff 9712a540 f48aa82`, `git diff --stat`, `git log HEAD..upstream/dev`, `git merge-tree`, `git merge --no-commit` + `--abort`.
- `python .github/scripts/upstream_sync.py --check-only`: 27 passed, 0 failed.
- `python -m pytest tests/test_provider_presets.py tests/test_auto_router.py tests/test_council.py tests/test_provider_and_auto_routes.py`: 176 passed.
- Zip unpacked to `/tmp/unpack`, compared to `/tmp/dionysus/Odysseus API model team kit` (`diff -r` → no diff).
- Dated source checks for dionysus via `gh api` and shallow clone of `dionysus` branch `dionysus` at `9b5e0e6`.
