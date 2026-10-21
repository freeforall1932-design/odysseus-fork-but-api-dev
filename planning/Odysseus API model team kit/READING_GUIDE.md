# AI Team Kit — owner reading guide

This guide summarises the sections you actually need to read, in a sensible
order. It also says what you can safely skip until a task needs it.

## Choose your reading path

### If you have about 10 minutes

Read, in order:

1. [`README.md`](README.md) — the status and verdict.
2. [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md), Sections 1–4 — what just
   changed, the current truth, evidence limits, and your next decision.
3. [`reports/CODE_AUDIT_2026-10-17.md`](reports/CODE_AUDIT_2026-10-17.md),
   “Short verdict” and Section 2 — the eight fix-before-trust issues.
4. [`WORKLIST.md`](WORKLIST.md), “Owner gate” and the P0 headings — enough to
   name the next task.

**Decision after this path:** pick one `W-` item, change the order, or park
the project. No agent should infer the next task from “next”.

### If you have about 30–45 minutes

Add:

5. [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — why the kit exists, how it
   fits together, and what the old chat intended next.
6. [`FILE_MAP.md`](FILE_MAP.md), Sections 1–5 — where files went and why the
   zips were deleted.
7. The audit's Sections 3–5 — likely failures, smaller issues, and what is
   implemented versus absent.
8. The full worklist item you are considering.

### If you want the evidence behind the claims

Add:

9. [`reports/KIT_LEARNING_AND_CHAT_MATCH.md`](reports/KIT_LEARNING_AND_CHAT_MATCH.md)
   — how v1 works, claim-by-claim old-chat matching, discrepancies, the one
   self-test, hashes, and full self-test output.
10. [`RESEARCH_AND_OPEN_QUESTIONS.md`](RESEARCH_AND_OPEN_QUESTIONS.md) — old
    findings with the correct evidence label, owner-reported 2026-10-18
    experience, Q1–Q14, and assumptions.
11. [`ODYSSEUS_SOURCE.md`](ODYSSEUS_SOURCE.md) only when Odysseus/room design
    is the topic.

You do **not** need to read raw code or the archived snapshots to choose the
next task. They are preserved for verification and history.

---

## 1. Current top-level documents, section by section

### `README.md` — start here

| Section | What it tells you |
|---|---|
| Status box | The one-screen state: extracted, audited, reorganised, waiting for you to name a task. |
| Start here | The shortest reading order and which file answers which question. |
| Current verdict | v1 is coherent source, but not runtime-proven; the audit's main warnings in plain words. |
| Folder map | The new layout and the fact that no top-level zip remains. |
| Done / not done | Separates delivered v1 from lost or unbuilt v2 work. |
| Tested / not tested | The exact evidence boundary, including the one scout self-test and its LiteLLM skip. |
| Owner's next step | Review/name one worklist item; agents do not merge or auto-pick. |

### `SESSION_HANDOFF.md` — read this to resume safely

| Section | Summary |
|---|---|
| 1. What just changed | Extraction, archive moves, guide deduplication, zip deletion, and “no kit code edited”. |
| 2. Current truth in one screen | Providers/roles in v1, absent v2 pieces, audit verdict, Odysseus pointer status, confirmed MCP/native directions, and the 2026-10-18 quota-pool/online-Colab/adaptive-council destination. |
| 3. Evidence and limits | What was checked here versus everything still unrun; why the self-test must not be ritual-rerun. |
| 4. Exact next gate | Your review/decision comes first; then one named `W-` item. |
| 5. Next-agent checklist | Git sync trap, scope, gate, and PR-update mechanics for a future session. You can skim this. |
| 6. Safety reminders | Secrets, installer downloads, helper code execution, licences, owner-only merging. |

### `WORKLIST.md` — the only actionable queue

| Part | Summary |
|---|---|
| Rules + owner direction + recommended order | One owner-named item at a time; the 2026-10-18 quota-pool/online-Colab/adaptive-council destination; P0 hardening and tests before v2 expansion; guide/repackage last. |
| Done | Baseline, learning report, one self-test, Odysseus pointer, extraction/audit/reorganisation, and the docs-only owner-direction recording. |
| W-001 | Your review gate: choose a slice or park it. |
| W-010…W-015 | P0 fixes: secrets/boundary, installer trust, shell lifecycle, dashboard onboarding/jobs/PR, safe skill installs, scout validation/free rules and pool metadata. |
| W-016 | Recreate lost dashboard/shell/OAT/LiteLLM tests and fixtures. |
| W-020…W-022 | W-020 free-provider research **done 2026-10-18** (core eight verified; Cerebras excluded, GitHub Models retired); W-021 still owes AI Horde/OpenMAIC/online-Colab answers; W-022 is the optional second-wave provider research. |
| W-030…W-032 | Rebuild dynamic scout roles/endpoints (including an online session endpoint only if W-021 permits it), then dynamic shell and dashboard. This is old T1/T3/T7. |
| W-040 | Rebuild reversible MCP for OAT plus commands/UI. Old T4. |
| W-050…W-051 | Design/compare the quota-aware pool and adaptive council first—Odysseus is the intended room centre, OAT the PR executor—then build Odysseus only if that design approves it. Old T5/T10 + Step 3. |
| W-060 | Admin toolchain installer for Qt/CMake/C# etc. Old T6. |
| W-070…W-080 | Update the guide, then generate and verify a new release zip. Old T8/T9. |
| W-090 | Parked ideas that need a fresh owner decision. |
| Cross-reference tables | Exact mapping from old T1–T10 and restart Steps to the new `W-` IDs. |

### `PROJECT_CONTEXT.md` — the stable “why”

| Section | Summary |
|---|---|
| 1. Goal | Free/cloud-only, beginner-friendly AI team for Gifscythe through owner-merged PRs; `dionysus` is the workbench, Gifscythe is the target. |
| 2. What v1 is | Each part's role and the normal install → scout → router/OAT → dashboard → PR flow. |
| 3. Decisions to keep | Free-only, owner merge gate, paced probing, stable roles, MCP yes, Odysseus native if used, pinned pointer, quota-aware pool with Colab while online, adaptive-council default, one-task and evidence rules. |
| 4. Rejected/dropped | llm-keypool, OmniRoute, Claw, wrong installer URL, multi-account limit tricks, Colab as an assumed always-on core API, AI Horde for tool roles, Docker for Odysseus, parallel probing. |
| 5. Old chat's next phase | Creative roles/endpoints, dynamic harness/dashboard, MCP, Odysseus room, toolchains, guide/repackage, optional choices—and why those are now gated behind hardening. |
| 6. Not decided | Final W-050 harness approval, adaptive escalation thresholds, sub-agent detail, AI Horde/OpenMAIC use, exact Colab permission/reliability, extra providers/personas/tools, paying anyone. |
| 7. Evidence hierarchy | Owner instruction > real kit files > dated session reports > Odysseus pointer > archived snapshots > visible old-chat claims. |

### `RESEARCH_AND_OPEN_QUESTIONS.md` — what is known vs merely reported

| Section | Summary |
|---|---|
| 1. Verified in restart | Canonical kit, superset relation, four providers/three roles, one self-test result, static parses, missing lost files, Odysseus pin. |
| 1A. Owner experience/direction | Colab/SillyTavern experience, failed direct multi-key agentic attempt, intended provider pool, adaptive council—clearly labelled as owner report/requirement, not current provider evidence. |
| 2. OAT findings | Old-chat reported installer/CLI/config/state/skills behaviour and one unresolved silent `oat-agent` check. |
| 3. Router/keys | LiteLLM fallback/order findings, loopback/master-key context, and dated OpenRouter/Codespaces numbers that must be refreshed before use. |
| 4. Old test reports | 68 scout, 84 dashboard, fresh-install, and fake end-to-end claims—labelled as old-chat reports except the partial self-test counterpart. |
| 5. Add-on research | Odysseus (with a correction not to repeat “built on OpenCode”), AI Horde, personas/OpenCode/Goose, Qt/C# sandbox result, lost MCP sandbox builds, OpenMAIC search-only status. |
| 6. Missing/blocked | Lost patch/MCP/tests, unwritten toolchains/commands/guide/package, pending answers, unbuilt room/MCP requests. |
| 7. Q1–Q14 | Q1 resolved “MCP yes”; Q5 answered for the core pool by W-020 (perishable; second wave = W-022); Q8 partially read; Q12 narrowed toward the Odysseus adaptive-council design; Q14 is the Colab terms/limits/API gate; the rest remain open with a concrete way to resolve each. |
| 8. Assumptions A1–A11 | A1 confirmed; most others remain unverified or doc-level only. |
| 9. Research rules | Official dated sources, no real secrets for research, separate evidence levels, update this file when facts change. |

### `FILE_MAP.md` — where everything went

| Section | Summary |
|---|---|
| 1. Folder at a glance | The final tree and the role of each top-level file/folder. |
| 2. Which document to open | A question-to-file lookup. |
| 3. Canonical kit | All 16 extracted files with size, mode, purpose, and the guide-deduplication note. |
| 4. Archive | Why snapshots, the old README, and the four `harness.zip` extras were preserved but demoted. |
| 5. Extraction/deletion record | Original zip sizes/hashes/member counts, extraction destinations, and why deleting both zips is auditable. |
| 6. Runtime files | Secret/generated files on an installed machine that must never be committed. |
| 7. Missing files | Lost patch/MCP/tests, unwritten toolchains, deliberate non-copy of Odysseus, and no current release zip. |
| 8. Guide lineage | The guide's old names and the single canonical file to edit later. |

---

## 2. Reports, section by section

### `reports/CODE_AUDIT_2026-10-17.md` — what needs fixing

Read the “Short verdict” first. Then:

| Section | Summary |
|---|---|
| 1. Scope/method | Exact files/hashes reviewed, static checks performed, evidence labels, and the important “self-test not rerun” note. |
| 2. P0 findings A-01…A-08 | The fix-before-trust list: free-status assumptions; unpinned installer; same-user secret boundary; keys file sourced as shell; masked OAT start/stop/merge-queue failures; stale refresh/router; concurrent jobs; skill-install symlinks. |
| 3. P1 findings A-09…A-20 | Health checks, stale PIDs, stale rendered config, weak config validation, role-eligibility soft edges, narrow probe, incomplete dashboard onboarding, hard-coded roles/services, hidden squash+delete-branch merge, skill-name collisions, repo-name mismatch, private OAT-state coupling. |
| 4. P2 findings A-21…A-26 | Changes-view base, HTTP warning-only endpoints, unbounded provider bodies/timestamps, small state/file issues, guide overstatements, minor UI races/launchers. |
| 5. Implemented/partial/absent | A clean separation between real v1 features, half-finished areas, missing v2 work, and external contracts still needing proof. |
| 6. What aligns well | Commands/routes/jobs line up; good key masking, atomic writes, loopback/token/host/CSRF/CSP/escaping controls; no need to rewrite these casually. |
| 7. Recommended order | P0 → tests → fresh research → dynamic v2/MCP/room/toolchains → guide/repackage. |
| 8. Tested/not tested | Static audit only; no installer/runtime/provider/GitHub/platform proof and no code fixes. |

### `reports/KIT_LEARNING_AND_CHAT_MATCH.md` — the deep evidence report

| Section | Summary |
|---|---|
| Short answer | `ai-team-kit.zip` is v1 glue for OAT + LiteLLM + scout + dashboard + skills; later MCP/Odysseus/creative work is absent. |
| 1. Scope/safety/evidence | Scratch extraction method, what was deliberately not run, and old-chat visibility limits. |
| 2. Two zips | Canonical vs superset proof, 16-file inventory, and `FILES.md` comparison including lost sandbox files. |
| 3. How the kit helps | Stable role names, paced probing/ranking, router/state generation, one-command operation, OAT connection with merge queue intended off, dashboard abilities, helper workflow skills, and explicit v1 non-goals. |
| 4. Four extras | Classification of the superseded guide, Gifscythe planning report, Gifscythe source review, and snapshot-generation prompt. |
| 5. Old-chat claim match | Delivery/dashboard, scout counts, keys/harness/OAT/safety, claimed dashboard tests, and research/unfinished claims matched to real files. |
| 6. Discrepancies/watch items | “Daily” refresh caveat, assumed-free providers, Codespaces/terms freshness, installer pinning, and other claims not to overstate. Several became audit findings. |
| 7. One self-test | Isolation/command and why 62 here corresponds to the old 68 claim when LiteLLM is installed. |
| 8. Queue reconciliation | How restart Steps map to T1–T10 and why T1 needs a rebuild/spec rather than a simple continuation. |
| 9. Tested/not tested | Exact boundary for that learning task. |
| Appendix A | Full member SHA-256 hashes for canonical and extra files. |
| Appendix B | Full stdout of the one isolated scout self-test. |

### `reports/FREE_PROVIDER_RESEARCH_2026-10-18.md` — which free offers are real (W-020)

| Section | Summary |
|---|---|
| Method | The owner's `awesome-freellm-apis` fork as discovery list only; every kept claim verified on the provider's own pages; classes: eligible / conditional / paid-risk / unknown. |
| 1. Headline results | One table for all eight: OpenRouter and Groq eligible; Google per-model; NVIDIA trial with unpublished limits; Mistral monthly allowance; Cloudflare small daily budget; Cerebras trial-only (excluded); GitHub Models retired. |
| 2–9. Per provider | Where to get the key, signup requirements (card/phone/region/age), what "free" means and when it can bill, limits, API shape, data-use/training, and suggested anti-rate-limit guard numbers. |
| 10. Rules for W-015 | The exact per-provider evidence rule that replaces `assume_free`, plus starting guard defaults per provider. |
| 11. Rest of the list | The other ~22 list providers grouped as unverified leads, with the list's own errors flagged (stale Cerebras row, duplicated xAI, empty Cline links). Second wave = W-022. |
| 12–13. Consequences + limits | What changes for W-015/W-030/W-050/W-070, and what desk research could not check (logins, live behaviour, support-only limits). |

### `reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md` — what you originally asked for

| Section | Summary |
|---|---|
| Limits | Hidden attachments (including the first plan) cannot be recovered from the shared-chat link; only your typed messages are used. |
| 1. Your requests | Verbatim quotes for the short defining asks (smart selection + skills; beginner step-by-step; Odysseus/MCP/council/toolchains/persona room; "Native and MCP") and a 13-point decomposition of the big Oct 4 message (repo-memory orchestration, paced probing, GUI bar, self-extending helpers, OpenRouter $10 question…). |
| 2. Added after restart | MCP-yes, quota-aware pool, online-Colab membership, adaptive council, anti-combustion rule, provider discovery — clearly separated from old-chat asks. |
| 3. Reconciliation | Every intent mapped to a v1 feature or a `W-` item; nothing contradicts the current worklist. |

### `ODYSSEUS_SOURCE.md` — only for the room/Odysseus topic

| Section | Summary |
|---|---|
| 1. Exact source | Owner repo address, checked pin `951d57db…`, old pin history, repo topology, and the trap that inherited docs point at upstream clone URLs. |
| 2. Why not copied | Size, licence/sync, and separate-repo reasons for a pointer rather than vendoring/submodule. |
| 3. File needs list | Exact files to read for identity/licence/security, native install, Providers/Auto/Council, MCP/shell/skills, install-time-only files, and files deliberately not needed. |
| 4. Facts vs claims | What this session actually read at the pins versus doc/test/runtime claims not reproduced; includes pin-change effects. |
| 5. Future-task use | Clone outside `dionysus` at the pin, change Odysseus in its own repo, install only in a separately approved task. |
| 6. Record | Pointer creation and pin-bump history with tested/not-tested limits. |

---

## 3. The kit guide (`kit/harness/GUIDE.md`), section by section

Do not use this as an instruction to install right now; the audit's P0 items
come first unless you consciously choose otherwise.

| Guide section | Plain summary |
|---|---|
| What you will have at the end | A dashboard, helpers working through PRs, owner-controlled merging, and a picker that refreshes free-model choices. Audit caveat: “free” and refresh wording needs W-015/W-012. |
| How the parts fit together | Scout writes role picks; LiteLLM routes roles; OAT runs helpers; dashboard is the control surface; skills teach workflow. |
| Words used in this guide | Beginner glossary for router, helper, role, PR, token, and related terms. |
| Step 0 — Choose where it runs | Windows+WSL recommended, Mac, Codespace, or Docker. It correctly says no Docker version was built/tested. Codespace numbers are dated claims. |
| Step 1 — Open a Linux terminal | Platform terminal setup, including a recommended separate Linux user. Read with audit A-03: separate user helps, but kit secrets still live with that user. |
| Step 2 — Install basic tools | Git, GitHub CLI, Python 3.11+, and checks. |
| Step 3 — Unzip kit and run installer | Delivered-zip flow. In this repo the zip has been extracted/deleted; a future release zip comes from W-080. Installer pinning is W-011. |
| Step 4 — Get free AI keys | Where keys come from, OpenRouter free-allowance notes, and a warning that free services may use/log submitted data. Terms refreshed by W-020 (2026-10-18); guide text itself updates in W-070. |
| Step 5 — Save keys one at a time | Hidden entry, test-before-save intent, refusal/offline handling, backup and status words. |
| Step 6 — Test the model picker | 6a script self-test, 6b key check, 6c first real probe/ranking run, 6d memory/state behaviour. This session's one baseline covers only 6a's delivered test, with LiteLLM skipped. |
| Step 7 — Sign in to GitHub | Fine-grained token creation and giving it to `gh`/Git. Dashboard parity is W-013. |
| Step 8 — Connect OAT and add project | `connect-oat`, `start`, `add-repo`, more projects, and what to do if an existing OAT config makes connect refuse. Audit A-05 says success must be verified, not assumed. |
| Step 9 — Open the dashboard | Tokenised local link, start/open/stop paths, and restarting later. |
| Using the dashboard | Chat, Tasks, Ask, Files, Changes, PRs, Models, Connections, Skills, Logs. Merge is owner-confirmed; the guide does not disclose default squash + branch deletion (W-013). |
| Step 10 — First test | A small end-to-end exercise. It has not been run with real accounts in this session. |
| Step 11 — Make the team smarter | Project handoff/worklist/log, project-only guardrails, cautious self-extension, and adding skill/design repos. Skill-install hardening is W-014. |
| Your daily routine | Start, give/review work, merge/close, glance at Models. Correctly notes refresh happens on start when stale; see audit refresh bugs. |
| When something goes wrong | Troubleshooting by symptom, including keys, router, OAT, dashboard, GitHub, and platform issues. Treat version/platform specifics as dated until runtime tasks verify them. |
| Quick reference | Command and file-location cheat sheet. |
| Notes: what was wrong in the first plan | Historical design corrections kept at the bottom as requested, including router exposure, wrong commands/URLs, and auto-merge. |
| Notes: how kit files were checked | Old-chat reported checks and explicit not-tested areas. Use the session reports for what was verified here. |

---

## 4. Source files: read only if reviewing code

| File | What to look at |
|---|---|
| `kit/harness/model_scout.py` | Defaults/providers and roles; HTTP `IO`; catalogue/free filters; scoring/probe; selection and LiteLLM output; key helpers; `--check` and main run; the fake-provider self-test. The audit gives line-level findings so you do not need to read all 1,611 lines. |
| `kit/harness/harness_ui.py` | Constants and environment paths; job runner; OAT state/chat; key/GitHub APIs; task/ask; files/git diff; PR actions; models/logs; skill preview/install; token/host/CSRF handler; the single-page HTML/CSS/JS. Start from audit A-07/A-15/A-17/A-20. |
| `kit/harness/harness.sh` | Paths and key loading; router/UI/OAT lifecycle; key prompts; scout wrappers; `connect-oat`; GitHub login; skills; add-repo; start/open/status/ask/doctor; command dispatch. Start from A-04/A-05/A-06/A-09/A-10. |
| `kit/harness/install.sh` | Platform/root checks; required tools; `uv`; harness symlink/PATH; LiteLLM venv; OAT download; skills and Windows shortcuts. Start from A-02. |
| `kit/harness/skills/team-workflow/SKILL.md` | Find/read project memory, choose one unblocked item, work through a PR, update handoff/worklist/log in the same PR, workspace-helper delegation, never merge. |
| `kit/harness/skills/self-extend/SKILL.md` | Name the missing capability, research existing skills/docs/web, check licence/maintenance/scripts and prompt-injection risk, add only through approved paths/PRs, then test/log it. |
| Skill templates | Tiny starting `HANDOFF`, `WORKLIST`, `IMPROVEMENT_LOG`, and worker-prompt note. The template `HANDOFF.md` is not the archived project snapshot. |
| Mac/Windows launchers | Thin wrappers around `harness open`/`harness stop`; no separate logic. Untested on those platforms here. |
| `kit/harness/README.txt` | Short contents/quick-start. Its “every day” picker wording should be read with the start-triggered caveat. |

---

## 5. Archived snapshots: what each section became

Read these only if you want original wording or are checking that the
reassembly lost nothing.

### Archived `HANDOFF.md`

| Original section | Where it lives now |
|---|---|
| Coverage | Research evidence limits; raw file kept for exact old-chat visibility wording. |
| Goal and scope | `PROJECT_CONTEXT.md`, Sections 1–2. |
| In progress at cutoff | `PROJECT_CONTEXT.md`, Section 5; research Sections 5–6. |
| To-do list T1–T10 | `WORKLIST.md` W-021/W-030/W-031/W-040/W-051/W-060/W-032/W-070/W-080/W-090. |
| Constraints and conventions | `PROJECT_CONTEXT.md`, Section 3; session safety rules. |
| Opening message | Superseded by the current README/handoff and W-001 gate; kept as history. |

### Archived `PROVEN.md`

| Original section | Where it lives now |
|---|---|
| Decisions | `PROJECT_CONTEXT.md`, Section 3 (plain names; MCP uncertainty resolved). |
| Rejected or dropped | `PROJECT_CONTEXT.md`, Section 4. |
| Findings: OAT | Research Section 2. |
| Findings: router/keys/passwords | Research Section 3. |
| Findings: tests that passed | Research Section 4, with this session's partial counterpart. |
| Findings: add-on research/builds | Research Section 5. |

### Archived `OPEN.md`

| Original section | Where it lives now |
|---|---|
| Blocked work and what is missing | Research Section 6; worklist rebuild items. |
| Research questions Q1–Q13 | Research Section 7 with current status; Q14 was added there on 2026-10-18 for the online-Colab gate. |
| Assumptions A1–A11 | Research Section 8 with current status. |

### Archived `FILES.md`

| Original section | Where it lives now |
|---|---|
| Files named in the chat | `FILE_MAP.md`, Sections 3, 6, and 7. |
| Flags | Guide lineage and lost-file warnings in `FILE_MAP.md`, Sections 7–8. |

### Archived `2026-10-17-next-session-readme.md`

This was the restart session's former all-in-one entry point. Its project
summary, evidence hierarchy, story, decisions, discrepancies, queue,
checklists, safety rules, and session log were split into the current README,
handoff, context, research, file map, and worklist. Keep it for the detailed
2026-10-17 chronology; do not start a new session from it because paths and
status have moved on.

---

## 6. `harness.zip` extras: read or skip?

| Archived extra | Summary | Read when |
|---|---|---|
| `gifscythe-ai-team-setup-guide.md` | Earlier 16-step terminal-first guide lineage: terminal/tools/helper files/keys/router/picker/OAT/GitHub/test/skills/daily routine/Gifscythe worklist/troubleshooting/notes. | **Skip for kit work.** Use `kit/harness/GUIDE.md`; keep this only to understand guide history. |
| `GIFSCYTHE_PLANNING_REPORT.md` | Gifscythe product plan: finish the EXE track, add a minimal Web/wasm track, choose build-vs-borrow for `gifsicle.wasm`, add crash diagnostics, and leave listed owner decisions open. | Read only for Gifscythe product work, not for choosing kit tasks. |
| `gifscythe-independent-review.md` | Source-only Gifscythe review with one high and several medium/low findings (batch destination changes, stale web result, preview invalidation, argv/comments, double decoding, header/settings escaping, object-URL cleanup), each with evidence and an unexecuted reproduction idea. | Read only for Gifscythe bug work. It does not test this AI-team kit. |
| `draft query that need refinement.txt` | The owner's prompt asking the old chat to write HANDOFF/PROVEN/OPEN/FILES from visible conversation only, mark uncertainty, and not re-test/recreate files. | Read if you want to understand why the snapshots are useful but not fresh proof. Otherwise skip. |

---

## 7. The shortest honest summary

- V1 source is now visible and organised in the repo; the zips are gone
  because their contents are extracted and hashed.
- The old chat was expanding toward creative roles, dynamic endpoints, MCP,
  Odysseus/personas, and toolchains. Those pieces are absent or lost, not
  hidden somewhere in v1.
- Before building that expansion, the worklist puts safety/correctness and
  missing tests first.
- The only runtime-style evidence reproduced in this restart remains one
  fake-provider scout self-test (62 passed; LiteLLM portion skipped).
- Your next action is a decision, not a download: review the PR/audit and name
  one `W-` item.
