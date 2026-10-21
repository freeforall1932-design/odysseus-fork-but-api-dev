# AI Team Kit — next session starts here

> **Archive note (2026-10-17 reorganisation):** this was the former
> all-in-one `README.md`, kept for the detailed restart/learning chronology.
> It is no longer the entry point. Start from `workbench/projects/ai-team-kit/README.md`,
> `workbench/projects/ai-team-kit/SESSION_HANDOFF.md`, and `workbench/projects/ai-team-kit/WORKLIST.md`. File paths below describe the
> layout when this README was current; the canonical kit has since been
> extracted to `workbench/projects/ai-team-kit/kit/harness/`, the snapshots archived, and both zips plus
> the duplicate guide deleted. *(2026-10-18: backticked paths in this
> archived file were prefixed with the folder's new location under
> `workbench/projects/` so links still resolve; the rest of the text is
> unchanged.)*

> **STOP — read this before doing anything.**
>
> Status on **2026-10-17**: **OWNER FILES ARRIVED; DETAILED UNPACK / LEARN
> / OLD-CHAT MATCH DONE — AWAITING THE NEXT OWNER-NAMED TASK.**
>
> The v1 kit (`ai-team-kit.zip`) and the four handoff notes (`HANDOFF.md`,
> `PROVEN.md`, `OPEN.md`, `FILES.md`) did not arrive in the restart chat's
> workspace, but the owner then committed them to this folder on the draft
> PR branch (commit `97a9fcc`, 2026-10-17 13:22 +07), together with
> `AI-Team-Setup-Guide.md` and an extra `harness.zip`. The owner later named
> the unpack/learn/match task: both zips were extracted **only to scratch**,
> the real kit files and the four `harness.zip`-only documents were read,
> the visible old chat was re-read and matched claim by claim, and the
> delivered model-picker self-test was run **once** under an isolated
> scratch `HOME`/`TMPDIR`. The full record is
> [`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md):
> Python 3.11.2, exit 0, **62 checks passed and the 6 LiteLLM Router checks
> skipped** because LiteLLM is not installed in that Python. Nothing was
> installed, no harness/OAT/LiteLLM/dashboard runtime was started, and no
> v2 work was built. Do not install, research, or build v2 until the owner
> names a task, and do not regenerate kit files from memory.
>
> The owner names **one task at a time**. If the owner sends only "next"
> or "continue", ask which numbered task they mean (see the work queue).

This folder is the isolated home of the **AI Team Kit** project inside the
`dionysus` repository. Paths in this README are relative to the repository
root unless they say otherwise.

- Folder created: 2026-10-17 (owner's restart session)
- Repository base commit when this README was written: `cc8aa83`
- Session branch when this README was written: `arena/5bf33a0c-dionysus`
  (once this README is merged, use whatever branch the current session is
  actually on — check with `git branch --show-current`, never assume)

Files currently in this folder (checked 2026-10-17 after owner commit
`97a9fcc`):

| File | What it is |
|---|---|
| `README.md` (this file) | The next-session entry point and record. |
| [`ODYSSEUS_SOURCE.md`](../ODYSSEUS_SOURCE.md) | The pinned address of the owner's Odysseus program repo (pin updated to that repo's 2026-10-17 `main` head), its licence and traps, and exactly which files this project needs from it. The Odysseus program itself is **not** copied here. |
| [`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md) | The 2026-10-17 unpack/learn report: how the delivered kit works, byte-level zip comparison, old-chat claim matching, `harness.zip` extra classification, and the one isolated model-picker self-test (62 passed, 6 LiteLLM checks skipped). Read this before quoting any old “tested” claim. |
| `HANDOFF.md`, `PROVEN.md`, `OPEN.md`, `FILES.md` | The four handoff notes (snapshot dated 2026-10-16). Present and read; treat their claims per Section 4 and the learning report. |
| `ai-team-kit.zip` | The delivered v1 kit per `FILES.md` (83,953 bytes) and the canonical baseline. Extracted only to scratch for reading; canonical zip untouched. Only `model_scout.py --selftest` was run from the extracted copy, once and isolated. |
| `AI-Team-Setup-Guide.md` | The current beginner setup guide per `FILES.md` (41,293 bytes). Read in the learning task and proven byte-identical to `harness/GUIDE.md` inside both zips. |
| `harness.zip` | **Extra — not named in `FILES.md`** (108,680 bytes). Byte-proven superset: the same 16 kit files as `ai-team-kit.zip` plus 4 extra documents (a superseded guide, a Gifscythe planning report, a Gifscythe source review, and the handoff-generation draft prompt). Not the canonical baseline. See discrepancy X9 and the learning report. |

---

## 1. The project in one minute (plain words)

The owner wants an **"AI team"** that is:

- **Free models only, cloud APIs only** — the AI helpers run on free
  internet services; no paid models, no models running on the owner's PC
  as the core plan.
- **Beginner-friendly** — the owner should not have to memorize many
  terminal commands; simple buttons and plain wording are requirements,
  not extras.
- **Working through GitHub pull requests** — the helpers prepare changes
  as pull requests (PRs). **The owner reads and merges them.** Nothing may
  merge itself behind the owner's back.

Version 1 was delivered in the old chat as `ai-team-kit.zip` plus a setup
guide. The uploaded zip was read on 2026-10-17: it contains the glue for
OAT helpers (the workers) and a LiteLLM router (one doorway that can send
requests to several AI services), a model picker (`model_scout.py`) that
finds and tests currently-free-looking models, a browser dashboard, and
install scripts. OAT and LiteLLM themselves are downloaded by the
installer; they are not bundled binaries. Runtime behaviour beyond the
model-picker self-test was not reproduced in that learning task — see
[`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md).

Version 2 (not designed yet, not built yet) is where these open wishes
belong: more model sources, a native "room" with personas for writing and
daily use, an orchestrator with specialist sub-agents, and MCP tools for
the pull-request team as well.

### Small glossary

| Word | Plain meaning here |
|---|---|
| OAT | The helper program reportedly used by the v1 kit to run the pull-request team. Do not guess its commands — read them from the real kit/guide when it arrives. |
| LiteLLM router | A middleman program. The helpers always talk to it using steady job names (for example architect / implementer / reviewer); it forwards each job to whichever free service is currently chosen, and can rotate API keys. |
| Model picker / scout | `model_scout.py` in the kit. It reportedly looks for currently-free models, tests them politely (paced, not all at once), ranks them per job, and rewrites the router's settings. |
| Dashboard | A local web page (buttons instead of commands) reportedly delivered in v1: chat, tasks, files, change counters, pull requests, models, keys, skills, logs. |
| Harness | The program the owner actually sits in front of (for example OAT, Odysseus, OpenCode, Goose). Which harness should do what in v2 is still undecided (Step 3). |
| MCP | A standard way to give an AI outside tools (GitHub, web search, step-by-step thinking, …) through a list file like LM Studio's `mcp.json`. |
| PAT | A GitHub "personal access token" — a password-like key that lets a program act on the owner's GitHub account with only the permissions the owner ticked. |
| Native install | Installed directly in Ubuntu/WSL, not inside Docker. |
| Persona "room" | A chat space where different made-up helpers (writer, editor, game designer, …) each have their own instructions, and the owner swaps the model behind each one. Not built yet. |
| Sandbox | The temporary computer an AI chat works on. A fresh chat starts with an empty one — nothing installed in an old chat exists in a new chat. |

---

## 2. Owner files: needed, received, then unpacked and learned

The files this project needed were committed by the owner to this folder
on the draft PR branch in commit `97a9fcc070879983e8850023a33b295dd61cf094`
("Add files via upload", 2026-10-17 13:22 +07). The first follow-up check
was inventory-only. Later the same day, the owner named the unpack/learn
task: both zips were safely extracted **only to scratch**
(`/tmp/ai-team-kit-learn-20261017/`), all extracted files were inventoried
with byte sizes and SHA-256 hashes, the real kit/guide/extras were read,
and the delivered model-picker self-test was run once under isolated
scratch `HOME`/`TMPDIR`. The canonical zips in this folder were not
modified, nothing was installed, and no harness/OAT/LiteLLM/dashboard
runtime was started. Details:
[`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md).

| # | File | Status after `97a9fcc` and the 2026-10-17 learning task |
|---|---|---|
| 1 | `HANDOFF.md` | ✅ Present (7,237 bytes). Read in full (snapshot 2026-10-16). |
| 2 | `PROVEN.md` | ✅ Present (7,531 bytes). Read in full. |
| 3 | `OPEN.md` | ✅ Present (5,671 bytes). Read in full. |
| 4 | `FILES.md` | ✅ Present (5,473 bytes). Read in full; used for the detailed compare. |
| 5 | `ai-team-kit.zip` (the delivered v1) | ✅ Present (83,953 bytes; SHA-256 `aea5c8df…`). Safely extracted to scratch only: a `harness/` folder with 16 files. Guide/code/skills/launchers read. Model-picker self-test: **1 isolated run**, Python 3.11.2, exit 0, **62 passed + 6 LiteLLM Router checks skipped**. Nothing else from the kit was executed. |
| 6 | `AI-Team-Setup-Guide.md` | ✅ Present as a separate top-level file (41,293 bytes), as `FILES.md` says. Read in the learning task and proven byte-identical by SHA-256 to `harness/GUIDE.md` inside both zips. |
| 7 | `harness.zip` | ⚠️ **Extra, not in `FILES.md`** (108,680 bytes; SHA-256 `d1e0b3b8…`). Byte-proven superset: the same 16 kit entries, SHA-256-identical to `ai-team-kit.zip`, plus 4 classified extras — `GIFSCYTHE_PLANNING_REPORT.md`, the superseded `gifscythe-ai-team-setup-guide.md`, `gifscythe-independent-review.md`, and `draft query that need refinement.txt`. Treat `ai-team-kit.zip`, not this, as the canonical delivered kit (see X9). |

Still **not** present anywhere in this folder or inside either extracted
zip: the patched `model_scout.py`, `mcp/oat_mcp_loader.py`,
`mcp/oat_mcp_apply.py`, `toolchains.sh`, and the dashboard/MCP sandbox test
files — exactly as `FILES.md`/`OPEN.md` describe (never presented; rebuild
from descriptions in their numbered tasks, with guesses said out loud).
The extracted delivered scout also lacks the patched features by code
search: no writer/editor roles, `only_roles`, endpoint presets,
`--list-services`, or `--add-endpoint`.

If local copies of those lost in-progress/test files ever surface outside
these uploads, they would be useful — but plan on "gone": the owner said
so, `FILES.md` says so, and the scratch extraction/search agrees. The
owner has said the expired old-chat file(s) are secured offline; they were
not needed to identify the delivered v1 zip in this task.

No Odysseus files are needed from the owner: the program source is the
owner's own repo recorded in [`ODYSSEUS_SOURCE.md`](../ODYSSEUS_SOURCE.md),
which any session can clone at the pinned commit when a task names it.

**Never commit:** API keys, GitHub tokens/PATs, `keys.env`, passwords, or
any file containing them.

The upload step and the detailed Step 0-style learning task are done. What
the next session needs from the owner now is only **one named task**. The
learning report reconciles this README's Steps with the handoff's T1–T10
(see X10): the owner might choose, for example, **“Do T2”** (answers only),
**“Rebuild the T1 scout patch as a spec”**, or **“Do Step 3”**. Do not infer
a task from “next” or “continue.”

---

## 3. Why this folder does not affect the rest of the repo

This repository is a fork of a Hyprland dotfiles repo. The owner's own
work already lives only under `workbench/` (plus one workflow file that
GitHub requires at the root). The upstream parts are `assets/` and
`dotfiles/`; this project must never touch them.

`workbench/projects/ai-team-kit/` was picked on purpose. The repo's checking
script, `workbench/skills/validate_skills.py`, was **read in this session
on 2026-10-17** and:

- It treats only `skills/`, `projects/`, and `tools/` directories (and
  `research/*.md` pages) as "units" that must appear in `workbench`'s
  index and README tables. A sibling folder named `ai-team-kit/` is none
  of those, so it is not forced into those tables.
- Its markdown link/path checking covers skills, projects, and the
  workbench loader/README files — not this folder — so handoff notes can
  be dropped in without instantly breaking the repo's gate.
- One caveat: the CI workflow (`.github/workflows/skills-gate.yml`) still
  triggers on any change under `workbench/`, and it checks that **every
  `.json` file under `workbench/` parses**. Any JSON this project commits
  here must be valid JSON.

If the project later grows up into a proper workbench "project" or "tool"
unit, that move (plus its index and README entries) is a separate, named
task — not something to do quietly.

---

## 4. Evidence: what was actually read, and what outranks what

Keep these layers separate. Never upgrade a lower layer into proof.

**For what the owner wants (requirements):**

1. The owner's latest explicit message (the 2026-10-17 restart message,
   and anything newer after it).
2. Earlier owner messages, including the ones visible in the old shared
   chat, where they do not conflict with newer ones.

**For what the kit currently does (facts about the code):**

1. The real files inside `ai-team-kit.zip`, at the exact commit they were
   committed — once they exist here.
2. Test/CI output actually run in the current session, on those files.
3. `HANDOFF.md` / `PROVEN.md` / `OPEN.md` / `FILES.md` — useful, dated
   snapshots written from a long chat; the owner warns they **may
   contain errors**. "Tested" in them means "the old chat reported
   testing it in its own (now gone) sandbox".
4. This README — a summary. Where it and the files above disagree, the
   files win and this README must be corrected in the same session.
5. The old shared chat (link below) — history, not proof.
6. Memory or guessing — always labelled as not verified.

**Read in the 2026-10-17 restart session (verified as read, not as true):**

- The owner's restart message (requirements, preferences, file list,
  the words "Native and MCP also" explained as "MCP for the OAT
  pull-request team too").
- The full text the old shared chat exposes:
  https://claude.ai/share/4b76ad92-cfd8-443a-b686-9fa20f1c23aa
  (fetched and read in 4 chunks). Limits of that source: attachments are
  hidden ("Files hidden when shared"), tool runs are collapsed into
  one-liners, and it is a snapshot — it shows what the old chat *said*,
  not what is true today.
- This repository at `cc8aa83`: the `workbench` README and index, the
  agent loader instructions, the gate script named above, and
  `git status` (clean). Skills loaded before editing, per the repo's own
  rules: `universal-agent-context` (its `SKILL.md`, the full v4 guide,
  and the session-protocol reference). The Qt workload skill was checked
  and does **not** apply to this docs task (no Qt/CMake build entry
  point); re-check that decision when real kit code is being worked on.
- Later the same day, for the owner-named Odysseus-pointer task: the
  owner's repo `freeforall1932-design/odysseus-fork-but-api-dev`, first at
  `c35a9256…`, then — after the owner flagged that `main` had moved that
  day — re-checked and compared at `951d57db…` (GitHub metadata plus
  read-only shallow clones in scratch space; selected docs/specs read —
  the exact list, per-pin limits, and findings are in
  [`ODYSSEUS_SOURCE.md`](../ODYSSEUS_SOURCE.md) Section 4). Nothing was
  installed, run, or tested, and no code was copied into this repo.
- Also later the same day, after owner commit `97a9fcc`: `FILES.md`,
  `HANDOFF.md`, `PROVEN.md`, and `OPEN.md` read in full (snapshot dated
  2026-10-16), followed by the owner-named unpack/learn task recorded in
  [`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md): both
  zips safely extracted only to scratch; all 16 canonical kit files and
  the 4 `harness.zip`-only documents inventoried by SHA-256 and read; the
  visible old chat re-read in 4 chunks and matched claim by claim; Python
  AST and shell syntax checks run; and the delivered
  `model_scout.py --selftest` run **once** under isolated scratch
  `HOME`/`TMPDIR` (Python 3.11.2, exit 0, 62 passed, 6 LiteLLM Router
  checks skipped). No installer, harness runtime, OAT, LiteLLM, or
  dashboard server was run.

**NOT run, NOT checked, NOT researched yet:**

- Any full runtime of the delivered kit: installer, LiteLLM download/load,
  OAT daemon/workers, dashboard server/browser behaviour, the claimed 84
  dashboard checks, or `harness.sh` start/stop/doctor/open flows. The kit
  contents have been **read** and static-checked; only the model-picker
  self-test was executed (62 passed, LiteLLM Router checks skipped).
- Real-provider behavior of the picker/dashboard with the owner's keys.
- Line-by-line truth of every external claim in `HANDOFF.md` /
  `PROVEN.md` / `OPEN.md`. The learning report matches their readable kit
  claims to delivered files, but old sandbox outcomes that left no test
  files in the zip remain “old chat reported.”
- Current free-tier limits and terms of any AI service (OpenRouter,
  NVIDIA NIM, Google AI Studio, Mistral, AI Horde, …). These change and
  must be looked up from official sources when the matching task is
  named — never from memory, never from the old chat's numbers.
- OAT, OpenCode, Goose, OpenMAIC, "The Agency", SkillOpt — nothing about
  them was re-checked in this session, beyond what the handoff files
  report. Odysseus is the partial exception: its identity, licence,
  topology, native recipe location, downstream Providers/Auto/Council
  docs, and MCP/skills spec map were read (per-pin reading limits in
  `ODYSSEUS_SOURCE.md`), but it was **not installed, run, or evaluated
  as the Step 3 winner**, and the rest of its tree was not read.
- Google Colab's current terms for the KoboldCpp notebook.

---

## 5. Story so far — as *reported* by the old chat (not re-proven here)

Everything in this section is "the old chat said so on that date". It is
kept so the next session does not redo finished thinking — but any claim
that matters must be re-checked against the real kit files (Step 0) or
against current official pages (later steps).

- **Oct 2 — flaw hunt on the original plan.** The owner asked for a
  review of flaws, then for smart model selection (new free models appear
  every few months, so hard-coding one free list is brittle) and skill
  integration without knowing if a custom harness was needed. The old
  chat reported, among other things: the plan's OAT install link and
  several OAT commands/settings did not exist; the router settings only
  honoured part of the fallback lists, leaving some jobs with no backup
  model; a key-rotating helper rejected `nvidia` and was unnecessary
  because the router itself rotates keys; the router was reachable from
  the whole network without a password; OAT's merge queue could merge
  PRs by itself, which clashes with "owner reviews and merges"; helpers
  run shell commands unattended; OpenRouter free use was 50 requests/day
  (not 200) and extra keys did not raise it; some other services' numbers
  could not be verified; OAT was macOS/Linux only (Windows untested), a
  local background program needing WSL2 or a cloud box; and the token
  steps mixed up token types. It also reported: OAT loads Agent Skills
  (`SKILL.md` folders) natively, so no custom harness was needed for
  skills, and MCP was the only missing piece, with "one small patch
  point" identified.
- **Oct 3 — model picker + plan v2, then a beginner guide.** A first
  `model_scout.py` plus a corrected plan were delivered. The owner then
  asked for a streamlined, step-by-step, beginner-worded install guide
  (old-plan notes moved to the bottom for troubleshooting), instructions
  to implement and test the picker, and a check of the picker file
  itself. The old chat reported finding and fixing real picker bugs
  (dry-run wasting probes, a maintenance page marking good models
  unusable for a week, a crash on a differently-shaped tool reply, both
  bug-finding questions secretly having the same answer, empty results
  saved on network loss, a missing folder crash, half-written config
  reads, long silence) and added a `--check` key test, reporting 34
  self-checks passing on three Python versions. A one-command helper
  (`harness`) was added.
- **Oct 4 — audit request + the big question list.** The owner asked for
  a code audit, and added: will helpers pick up the owner's handoff /
  improvement-log / worklist markdown files and orchestrate themselves?
  Browser-only Codespace pros/cons and warnings; isolated folder vs
  Docker on Ubuntu; do weak passwords (`word`, `1234`, empty) work? Is
  the browser path the same install as Ubuntu? How to restart everything
  on Windows (PowerShell? Ubuntu first? `harness start`?); are keys
  entered one at a time, what happens on skip/failure, what happens to
  the old key; make the picker test **one model at a time per service
  with gaps** (no spam flags), starting from the biggest or the week's
  most-used model; what "EMPTY" even meant (suggested `[offline]`
  wording instead); the GitHub token needed more permissions than the
  guide's three (the owner's wider set was listed in that message —
  re-read it in the real files, do not reconstruct it from here); the
  confusing "`--repo`" instruction; a GUI/dashboard instead of
  remembering commands (chat-like, Arena/Qwen agent-style, with folders,
  files and +/- change counters; Replit's GitHub/MCP connections as
  inspiration; possibly design/skill repos such as Microsoft's
  SkillOpt); helpers that research and add missing skills/workflows
  themselves; and whether paying OpenRouter $10 really raises the free
  limit to 1,000/day and whether that can be taken away later.
- **Oct 5–8 — v1 kit built and delivered (reported).** Picker v3
  (reported: 68 self-checks), improved helper command, a browser
  dashboard (opened by double-clicking "Start AI Team" / `harness
  open`; chat shown as a transcript, not chat bubbles; tasks, files,
  +/- counters, PRs with Merge/Close, models, keys, skills, logs; **no
  MCP plug-ins**), a `team-workflow` skill so helpers know where the
  owner's handoff/worklist/log files live and how to update them (they
  do **not** pick them up by themselves), a `self-extend` skill (research
  → check licence/scripts → add through a PR; ask the owner first for
  third-party skills and workflow changes), paced model testing
  (reported default: one model at a time per service with a 20-second
  rest, adjustable in `scout.yaml`), clearer status words replacing
  "EMPTY" (roles borrow models or say `UNAVAILABLE`; services show
  `[offline]`, `[refused]`, `[limit]`, `[blocked]`, `[skip]`), careful
  key handling (ask per service, Enter skips, test before saving, a
  refused new key keeps the old one, `keys.env.bak` kept), answers on
  passwords (Ubuntu refuses empty, accepts weak ones at your risk;
  router password is generated), isolation (a folder alone does not
  isolate; a separate Linux user or a Codespace does; Docker strongest
  but **not built**), a Codespace section (almost the same install as
  Ubuntu; stops after 30 idle minutes; monthly free allowance figures
  were quoted differently in different messages — re-check the current
  official number when needed), the OpenRouter $10 question (reported:
  buying ≥ $10 credit in total raises free use to 1,000/day and is not
  lost by spending the balance, but the terms allow changes at any time
  and credits may expire; the terms were only read through search
  excerpts — re-check before paying), the `--repo` answer (full project
  name at the end of an `oat` command about a project; `harness
  add-repo` sets a default), and an audit list of found-and-fixed bugs
  (among them: OAT refusing a project without a provider key, refused
  keys retried forever, a privacy setting that would have blacklisted
  every free model for a week, a redirect that could carry a key to
  another site, one odd reply crashing a whole test run, the dashboard's
  Stop button stopping the dashboard itself, chat text shifting on
  non-English characters, messages pointing at guide sections that did
  not exist; reported: 68 picker checks, 84 dashboard checks, and a
  fresh install working with the newest LiteLLM at that time). Reported
  as **not tested**: real accounts, real GitHub steps (token, project
  setup, real PRs), Windows/Mac/Codespace specifics, real helper chat
  output. Delivered as `ai-team-kit.zip` (reported 84 KB, installs
  cleanly into a fresh home) plus `AI-Team-Setup-Guide.md`.
- **Oct 8 — the big v2 question.** The owner asked: does this plan
  already take into account Odysseus or a similar harness; multiple
  popular sources (NVIDIA NIM, Google AI Studio, Google Colab with the
  KoboldCpp notebook at
  https://colab.research.google.com/github/lostruins/koboldcpp/blob/concedo/colab.ipynb
  ); MCP plug-ins/tools like LM Studio's `mcp.json` (GitHub via the
  owner's PAT, web search, sequential thinking, …); other
  "council / dev-team" repos with an orchestrator and specialist
  sub-agents (game code, programming, front-end/GUI, design, …);
  test environments for hard stacks (Qt6, CMake, C#); and daily-use /
  writing (fanfic) versatility by swapping models in a "room" where each
  persona has its own specialization.
- **Oct 10 — a research answer exists in the shared snapshot.** It began
  "Not yet" and reported: the v1 kit has no MCP, no persona rooms, no
  Colab endpoints, no toolchain installer, and Odysseus had only been a
  name in the owner's handoff; Odysseus was then checked (self-hosted AI
  workspace; agent mode reported as built on OpenCode, bringing MCP,
  skills and shell tools; talks to any OpenAI-compatible endpoint, so it
  could use the kit's router; licence reported as AGPL-3.0; runs with
  Docker or natively; powerful shell tools = treat like an admin
  console; it is **not** a PR dev team; one review's claim of persona
  group chats was **not tested**); model sources reported as covered —
  NVIDIA NIM, Google AI Studio (Flash models), OpenRouter, Mistral —
  with Groq, Cerebras and GitHub Models not added and their free limits
  not verified; Colab/KoboldCpp advised against as a core source
  (reported reading of Colab's FAQ: web services / bypassing the
  notebook UI restrictions, runtimes can end without warning) though the
  router could treat it as a custom endpoint; MCP options were OpenCode
  (reported MIT; MCP, sub-agents, skills, web UI, can use the router) or
  Odysseus, since OAT cannot load MCP and patching it is possible but
  fragile (GitHub commits via `gh`/git already work with the PAT);
  orchestration: OAT already has supervisor/workers/reviewers; "The
  Agency" was mentioned as 147+ specialist persona files (personas, not
  a runtime; convertible to skills; licence to check); ChatDev, MetaGPT
  and CrewAI were explicitly **not evaluated**; test environments
  (reported on Ubuntu 24.04: a Qt 6.4 + CMake 3.28 + Ninja project built
  and its QtTest ran headless; a C# SDK installed but the sandbox's
  NuGet block stopped a build; Linux builds only — a Windows `.exe`
  needs Windows or GitHub Actions `windows-latest` plus the Workflows
  permission; the helper user has no sudo, so toolchains are installed
  once by the owner — the kit does not automate this yet); writing roles
  (`writer`/`editor`) would be easy router names, but free models'
  content filters vary and fanfic results cannot be promised; the
  dashboard has no persona room yet. Recommended path (a recommendation,
  not an owner decision): one shared router; OAT + dashboard for the
  GitHub team; Odysseus as the chat/persona/MCP room; add OpenCode only
  if MCP is wanted in a coding terminal; running three harnesses at once
  adds upkeep. It ended with two owner decisions: Docker or native for
  Odysseus? Is MCP in Odysseus/OpenCode enough, or must the OAT team have
  MCP too (a patch the old chat would have to maintain)?
- **After Oct 10 — two short owner messages, then the chat ran out of
  road.** (1) "Native and MCP also does it support AI Horde from
  community backed models that run on kudos" — no answer about AI Horde
  ever appears in the snapshot. The visible tool notes afterwards
  mention writing "the MCP manager: presets, an LM Studio style
  `mcp.json`, and a safe, reversible patch that gives OAT helpers MCP
  tools" — but **no such files were delivered**; the owner confirms the
  MCP loader/apply files are gone. (2) "Continue where you left off
  (also what do you think about openmaic repo)" — no opinion was given.
  Finally the owner had the old chat write `HANDOFF.md`, `PROVEN.md`,
  `OPEN.md`, then `FILES.md` for this restart. Their contents are hidden
  in the shared snapshot.

### The 2026-10-17 restart (this session, verified here)

- Baseline inventory done: this repo at `cc8aa83`, clean tree; none of
  the five expected files present anywhere in the workspace; no
  `model_scout.py` anywhere. **The selftest baseline could not be run —
  0 runs. That is "not run", not "failed", and not "passed".** No other
  script was run as a substitute.
- The shared old chat was fetched and read (Section 4). No other
  research was started and nothing was built, exactly as the owner
  ordered for the first reply.
- The owner answered the MCP multiple-choice question: **YES — give the
  OAT pull-request team MCP too** (see Decisions).
- This README in the new isolated folder is the second named task.
- Third named task: the Odysseus pointer (`ODYSSEUS_SOURCE.md`) plus a
  draft PR so the owner could commit the required files to its branch.
- The owner then committed the seven files in Section 2 (`97a9fcc`) and
  flagged that Odysseus `main` had moved the same day. Fourth task:
  sync/inventory this folder and bump the Odysseus pin after a real
  compare (Section 2 and `ODYSSEUS_SOURCE.md` Sections 1/4/6). At that
  point the selftest was still 0 runs.
- Fifth task (same day): the owner named the unpack/learn/match job. Both
  zips were extracted only to scratch, the real files and extras were
  read, the visible old chat was matched to them, and the delivered
  model-picker self-test was run once in isolation (62 passed, 6 LiteLLM
  checks skipped). The detailed evidence is
  [`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md). No
  installer/harness/OAT/LiteLLM/dashboard runtime, T1 work, or v2 building
  was started.

---

## 6. Owner's standing instructions and preferences (keep these)

1. **One task at a time**, named by the owner. "Next" / "continue" alone
   means: ask which task.
2. **Beginner wording** in anything the owner must read: plain words,
   step-by-step, no unexplained jargon breaking the flow. Troubleshooting
   and "what was wrong with v1" details go at the bottom of guides.
3. **Downloadable files**: deliver results as files the owner can save,
   not only as chat text.
4. **Say what you tested and what you couldn't**, every time. Never turn
   "the old chat reported it" into "verified".
5. **Read the real kit files before changing anything; edit them in
   place** instead of regenerating them. Do not repeat research that
   `PROVEN.md` already covers — after actually reading `PROVEN.md`.
6. **Lost files** (patched `model_scout.py`, MCP loader/apply, dashboard
   tests) get rebuilt from their descriptions, with guesses said out
   loud.
7. **Free-tier limits and terms must be looked up fresh** from official
   sources at task time. Old numbers in any document (including this
   one) are dated claims, not facts.
8. **The owner reviews and merges all pull requests.** No auto-merge, no
   publishing, no spending money, no licence-risky copying without the
   owner deciding first.
9. Work stays inside `workbench/projects/ai-team-kit/` unless a named task says
   otherwise. Upstream `assets/` and `dotfiles/` are never touched.

---

## 7. Decisions and non-decisions

### Decided by the owner

| ID | Decision | When / source | Meaning |
|---|---|---|---|
| D1 | The room side (Odysseus or similar) runs **native**, not Docker | Owner: "Native and MCP also" (old chat), carried into the 2026-10-17 restart | Install directly in the same Ubuntu/WSL. Exact host and steps are a Step 3 design detail. This decision was about Odysseus; it does not ban Docker as an *isolation* idea elsewhere, but do not build Docker anything unless re-named as a task. |
| D2 | **MCP for the OAT pull-request team too: YES** | Owner picked YES in the 2026-10-17 multiple-choice question | Queued only — nothing built. Means: rebuild a small, undoable patch/loader plus an owner-controlled `mcp.json`-style list so OAT workers/reviewers can call approved MCP tools (examples the owner named: GitHub via PAT, sequential thinking, web search) during PR work. Known cost accepted by the owner: OAT has no native MCP, so this is custom work that must be tested and may need care after OAT updates. Tools must be allowed one by one; read-only where possible. |
| D3 | Work lives in an isolated folder in this repo that does not affect the rest of it | Owner's restart message; owner then asked for this README in "the separate folder", 2026-10-17 | The exact path `workbench/projects/ai-team-kit/` is this session's working choice (picked for the gate reasons in Section 3), not a path the owner dictated. Reversible: it can be renamed, moved, or promoted later as a named task. |
| D4 | The Odysseus program source is the owner's repo `freeforall1932-design/odysseus-fork-but-api-dev` | Owner pointed at that repo "for the Odysseus aka the program file", 2026-10-17 | Source-of-program decision only: whenever Odysseus code is needed, clone **that** repo at the commit pinned in `ODYSSEUS_SOURCE.md` (never the upstream clone URL in its inherited docs, never a floating "latest"). It does **not** decide that Odysseus wins Step 3, and it authorizes no install. The program is pointed at, not copied into `dionysus` (size/licence/sync reasons in the pointer file); a vendored copy or submodule would be a separate named decision. |

### Explicitly NOT decided yet (do not build on these)

- Which harness is the persona room (Odysseus vs OpenCode vs Goose vs …)
  and which should do what — that is the Step 3 comparison. The old
  chat's "recommended path" was its own suggestion, never approved.
  D4 only fixes *where Odysseus comes from if it is used*; it does not
  pick it.
- Orchestrator/sub-agent role design (game code, programming,
  front-end/GUI, design) and the writing/daily-use personas.
- Whether the KoboldCpp Colab endpoint is used at all (Step 1b), and
  whether AI Horde is supported/added (Step 1c).
- Any opinion on, or use of, OpenMAIC (Step 1d).
- Extra model sources beyond NVIDIA NIM + Google AI Studio (Groq,
  Cerebras, GitHub Models were only mentioned by the old chat).
- "The Agency" personas, SkillOpt, ChatDev/MetaGPT/CrewAI — mentions, not
  approvals. Licence checks come before any use.
- Paying OpenRouter (or anyone) anything.

---

## 8. Discrepancies — do not "fix" these by guessing

| # | Discrepancy | What to do |
|---|---|---|
| X1 | Owner said 5 files were attached; none arrived in the restart sandbox, and the shared chat hides its attachments. | **Resolved 2026-10-17:** the owner committed the files to this folder on the draft PR branch (`97a9fcc`), and the later owner-named learning task unpacked/matched them (see `KIT_LEARNING_AND_CHAT_MATCH.md`). Kept here as the record of why the first baseline attempt could not run. |
| X2 | Old chat (Oct 10) said NVIDIA NIM and Google AI Studio were already covered; the restart message says the handoff leaves them out and missing pieces should be added. | **Resolved at delivered-config level 2026-10-17:** `model_scout.py` defaults contain OpenRouter, NVIDIA, Mistral, and Google (Google filtered to `flash`). Current free status/terms were not re-researched and NVIDIA/Mistral/Google use `assume_free: true`; any Step 2/T-task must look those up fresh before adding/changing sources. |
| X3 | Owner lists Odysseus-coverage and Colab-usability as "replies I never got", yet the shared snapshot contains an Oct 10 answer covering both. | Odysseus coverage is now answered at file level: **not in delivered v1**. Colab usability/terms remain open (Step 1b/T2-style research with current official sources). Do not treat the Oct 10 snapshot answer as a fresh terms check. |
| X4 | Self-check counts in the old chat grew as the code grew (23 → 33/34 → 68 for the picker; 84 for the dashboard). | **Picker count reconciled 2026-10-17:** delivered `selftest()` has 64 `check_` call sites; two inside a 3-role LiteLLM loop make 68 logical checks when LiteLLM is installed. This session's one run: **62 passed + skip** (no LiteLLM). Dashboard **84 remains unverified** because its test harnesses are not in either zip. Never quote an old count as a current result. |
| X5 | Codespace free allowance was quoted in two different shapes ("about 60 hours a month" vs "about 120 core-hours"). | Look up the current official figure only when a Codespace task is named. |
| X6 | Odysseus persona group chats rest on "one review" and were never tested, even by the old chat. | Superseded in part on 2026-10-17: the fork's own downstream Council doc describes optional personas with a separate chair (see `ODYSSEUS_SOURCE.md`). Still a doc claim — do not claim the owner's "persona room" exists until Step 3 tests what Council actually does. |
| X7 | Old chat: Odysseus "agent mode is built on OpenCode". Fork docs/specs read at the 2026-10-17 pin show OpenCode only as a model-provider shape, plus a scoped `/api/codex/*` surface for Codex/Claude. | Do not repeat the old sentence. Step 3 settles what the agent runtime actually is, from primary source in the pinned repo. |
| X8 | The word "fork" misleads twice: GitHub marks `odysseus-fork-but-api-dev` as not-a-fork (ZIP-seeded, histories linked by merge on 2026-10-14), and its README/setup clone commands point at upstream, not at itself. | Always clone the address and pin in `ODYSSEUS_SOURCE.md`; treat upstream URLs inside that repo's docs as inherited examples. |
| X9 | `harness.zip` was uploaded alongside the kit but is not named anywhere in `FILES.md`. | **Classified 2026-10-17:** byte-proven superset — all 16 canonical entries SHA-256-identical to `ai-team-kit.zip`, plus a superseded earlier guide, a Gifscythe planning report, a Gifscythe independent source review, and the handoff-generation draft prompt. The baseline remains `ai-team-kit.zip` only; do not treat the superseded guide as current or the two Gifscythe documents as kit evidence. Details: `KIT_LEARNING_AND_CHAT_MATCH.md` Section 4. |
| X10 | Two numbering systems compete: this README's Steps 0–5 vs the handoff's T1–T10 (`HANDOFF.md` says "Exact next action: T1" and its opening message says compare files first, then wait for a T-number). | **Reconciled 2026-10-17 in `KIT_LEARNING_AND_CHAT_MATCH.md` Section 8.** The Step 0-style compare/read/self-test is done. T1 cannot proceed as written until a named rebuild/spec task recreates the lost scout patch on top of the delivered file; T2 is answers-only with fresh sources; Step 3 remains design/comparison. The owner still names exactly one next task. |

---

## 9. Work queue (order proposed on 2026-10-17)

This numbering is the restart session's proposal so the owner can name
tasks — the owner has not locked the order. `HANDOFF.md` / `OPEN.md` have
now been read and their T1–T10 queue is reconciled with these Steps in
[`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md)
Section 8. Do not start a Step or a T-task unless the owner names it.

### Step 0 — Unblock + baseline (DONE 2026-10-17 as the unpack/learn task)

Done: owner files arrived (`97a9fcc`); both zips were safely extracted
only to scratch without modifying the delivered files; every extracted
file was listed with sizes/SHA-256 and compared with `FILES.md`; the real
guide/code/skills/launchers and the four `harness.zip` extras were read;
the visible old chat was re-read and matched claim by claim; the delivered
`model_scout.py --selftest` was run **once** under isolated scratch
`HOME`/`TMPDIR` (Python 3.11.2, exit 0, 62 passed, 6 LiteLLM Router checks
skipped, full output in the learning report); actual delivered provider
config was reported (OpenRouter, NVIDIA, Mistral, Google Flash); and Steps
↔ T1–T10 were reconciled. No installer or full runtime was started.
Evidence: [`KIT_LEARNING_AND_CHAT_MATCH.md`](../reports/KIT_LEARNING_AND_CHAT_MATCH.md).

### Step 1 — Quick answers the owner never got (answers only)

Current official sources and licences checked at task time; short,
beginner-worded answers; no building.

- **1a.** Does the plan already cover Odysseus or similar harnesses?
  (**Answered at delivered-file level by the learning report: no —
  Odysseus/similar room integration is absent from v1.** Any fresh
  recommendation belongs to Step 3.)
- **1b.** Is the owner's KoboldCpp Colab link usable for this project
  under Colab's current terms?
- **1c.** AI Horde (community models, kudos): does the kit/router support
  it today; if not, could it, and what would it cost in upkeep? Check
  what kind of API it actually offers before answering.
- **1d.** OpenMAIC repo: read its README **and licence**, then give an
  opinion — useful here, reference only, or avoid, and why.

### Step 2 — Model sources: NVIDIA NIM + Google AI Studio

Step 0 finding: NVIDIA and Google are already in the delivered scout
defaults (Google limited to IDs matching `flash`; both use
`assume_free: true`), alongside OpenRouter and Mistral. Look up the
services' **current** free limits and terms from official pages before
changing anything. Add only what is actually missing, editing the real
files in place. This overlaps handoff T1/T3 where the lost scout patch and
dynamic service list are involved; do not begin without the owner naming
the exact scope. Test what can be tested without the owner's keys (for
example against a fake local service) and say plainly what still needs the
owner's real keys to prove.

### Step 3 — Compare harnesses + design v2 (design only, owner approves)

Compare **OAT, Odysseus, OpenCode, Goose** from primary sources (docs,
source, licence, releases): who runs the PR team, who is the native
persona room for writing/daily use, who carries MCP where, orchestrator
+ specialist sub-agents (game code, programming, front-end/GUI, design),
and how test toolchains (Qt6/CMake, C#, …) fit. For Odysseus, "primary
source" now has an address: the owner's repo at the commit pinned in
`ODYSSEUS_SOURCE.md`, read per its Section 3 lists (including that
repo's pending audit worklist before any install idea). Deliver a
beginner-friendly design naming who does what and why — and stop for the
owner's approval before any installation.

### Step 4 — Rebuild the lost files (say what you guessed)

Rebuild, from their descriptions in the handoff files: the patched
`model_scout.py` changes, the dashboard test files, and the MCP
loader/apply files for OAT (see decision D2; design settled in Step 3).
Every guess gets labelled in the file and in the report. Each rebuilt
piece needs a test that can fail, run for real.

### Step 5 — Build v2, one approved slice at a time

Native room, orchestrator/sub-agent roles, MCP for the OAT team, new
model sources wired in. Each slice: small diff, real tests at the level
the claim needs, honest "tested / couldn't test" report, downloadable
result, owner merges the PR.

### Parked (not authorized until the owner names them)

Groq / Cerebras / GitHub Models · SkillOpt integration · "The Agency"
persona conversion · ChatDev / MetaGPT / CrewAI · any Docker build ·
promoting this folder into the workbench index/README tables · paying
for any credit.

---

## 10. Next-session checklist

### For the owner (2 minutes)

1. (Done 2026-10-17: the Section 2 files were committed to this folder
   on the draft PR branch; the guide was separate *and* inside the zip.
   No keys/tokens were included in the top-level file list checked.)
2. Name **one** task. The Step 0-style unpack/learn/self-test baseline is
   done; possible next names are **“Do T2”**, **“Rebuild the T1 scout
   patch as a spec”**, or **“Do Step 3”** — see
   `KIT_LEARNING_AND_CHAT_MATCH.md` Section 8. Nothing else is needed
   from the owner until that named task reports back.

### For the next agent

1. You are in the `dionysus` repo: obey `workbench/AGENTS.md` first —
   load the `universal-agent-context` skill (SKILL.md → v4 guide →
   session-protocol) and say what you loaded. Load a workload skill only
   if the repo's real build entry point matches it.
2. Read this README, then `KIT_LEARNING_AND_CHAT_MATCH.md` (what the real
   delivered kit does and what was actually tested), `FILES.md`
   (inventory), `HANDOFF.md` (route), `PROVEN.md` (do not redo its
   research), and `OPEN.md` (its own work list). Real kit files outrank
   all summaries for "what the code does"; the owner's latest message
   outranks everything for "what to do".
3. Record the baseline before edits: branch, base commit, `git status`
   (explain any dirt), and sync/fetch the branch the owner named.
4. Treat the uploaded zips as canonical and read scripts before running
   anything — never blind-run installers or self-modifying "apply" steps.
5. Do **not** rerun the picker's selftest as a ritual. The Step 0 baseline
   is recorded in `KIT_LEARNING_AND_CHAT_MATCH.md` (Python 3.11.2, exit 0,
   62 passed + LiteLLM checks skipped). Rerun only when a named code task
   changes the scout or its environment, and report *that* run exactly.
6. Do the one named task only. Keep diffs small; prove claims at the
   level they need (a syntax check is not a test; a test pass here is
   not proof on Windows/Mac/Codespace).
7. Before finishing: if anything under `workbench/` changed, run
   `python3 skills/validate_skills.py` from inside `workbench/` and make
   it pass; commit; update this README's status, decisions,
   discrepancies, and session log **in the same session** (correct it,
   don't layer a second handoff on top); end with what changed, what was
   verified, and a "Not verifiable here" line.

---

## 11. Safety rules (plain words)

- **Secrets stay out of git and out of chat logs**: API keys and PATs
  live only in the kit's local key file on the owner's machine.
- **Least power for the PAT**: only the permissions the guide/owner
  agree on. (Reported detail to re-verify in the real guide: "Actions"
  is not "Workflows" — editing `.github/workflows` needs the Workflows
  permission.)
- **Helpers run commands unattended**: isolation matters. A plain folder
  does not isolate them; the kit's reported answers were a separate
  Linux user or a Codespace. Re-read the real guide before advising.
- **The router must not be open to the network without its password**
  (the original plan's flaw). Delivered code was read in Step 0: the
  generated list references `LITELLM_MASTER_KEY` from the environment and
  `harness` starts LiteLLM with `--host 127.0.0.1`. That is a code-level
  check only; no router runtime was started here.
- **MCP tools are power tools**: allow-list one by one, read-only first,
  and remember the OAT patch (D2) is custom work to re-check after OAT
  updates.
- **Terms before use**: Colab, AI Horde, and every free tier get a fresh
  official-terms check in the step that touches them. "Free today" is a
  dated claim.
- **Licences before copying**: no third-party skill/persona/code is
  copied in until its licence is read and compatible. (Odysseus update,
  2026-10-17: its `LICENSE` and repo metadata at the pinned commit say
  AGPL-3.0-or-later — verified by reading; what that allows for a
  specific reuse is still a Step 3 reading task, and its pending audit
  worklist in `ODYSSEUS_SOURCE.md` Section 3.1 must be read before any
  install is exposed beyond loopback.)

---

## 12. Session log for this folder

### 2026-10-17 — restart + this README (Arena session)

- Changed: created `workbench/projects/ai-team-kit/README.md` (this file). First
  reply of the session was inventory-only and changed nothing.
- Partial: Step 0 cannot start — the five files in Section 2 are still
  missing, so there is still **no selftest baseline** (0 runs).
- Left (on purpose): all research and all v2 building; every numbered
  step awaits the owner naming it.
- Verified in this session: repo/branch/base commit and clean tree by
  `git status`; absence of the five files and of any `model_scout.py` by
  searching the workspace; the gate script's scope by reading it; the
  old chat's visible text by fetching the shared link; and, after this
  README was written, the repo gate — `python3 skills/validate_skills.py`
  run from inside `workbench/` — passed (exit 0) on 2026-10-17, as did
  the pushed commit's GitHub `skills-gate` run. Those passes prove the
  repo's existing checks still passed with this folder present; they
  prove nothing about the missing kit. Re-run the gate rather than
  trusting these dated results.
- Not verifiable here: everything inside the missing zip and handoff
  files; every "tested" claim from the old chat; current free-tier
  limits/terms of any service; Windows/Mac/Codespace behaviour; real
  GitHub/PR flows with the owner's accounts.
- Docs touched: only this README.

### 2026-10-17 — Odysseus pointer + visibility PR (same Arena session)

- Changed: added `ODYSSEUS_SOURCE.md` beside this README (owner's fork
  pinned at `c35a9256…`, licence, topology, clone trap, and the exact
  read/install/do-not-need file lists), updated this README (folder
  file table, decision D4, discrepancies X6–X8, Step 3 source address,
  licence line, this entry), and opened a **draft** pull request from
  the session branch to the repo's default branch `dionysus` so the
  owner can see the branch/folder on GitHub and commit the Section 2
  files to the PR's branch. The PR number/URL live on GitHub and in that
  day's chat report — GitHub, not this file, is the source of truth for
  PR state. **Draft means: do not merge yet** — the kit files are still
  missing and Step 0 has not run.
- Partial: Step 0 remains blocked on the same five missing files; the
  Odysseus pointer unblocks nothing by itself.
- Left (on purpose): no Odysseus code copied into this repo, no
  submodule, no Odysseus install/run/test, no harness verdict, no
  research beyond reading the pinned repo's own docs/specs listed in
  `ODYSSEUS_SOURCE.md` Section 4.
- Verified in this session: fork metadata and branch tips via `gh`;
  shallow clone at the pin read in scratch space; every file path in
  `ODYSSEUS_SOURCE.md` Section 3 checked to exist; then the workbench
  gate and the pushed commit's CI (exact results in that day's chat
  report — re-run rather than trusting a quoted number later).
- Not verifiable here: Odysseus installing/running at the pin; its docs'
  behavioural and test-count claims; whether its pending audit items
  still apply line-by-line; everything in the previous entry's list.
- Docs touched: `ODYSSEUS_SOURCE.md` (new) and this README.

### 2026-10-17 — folder re-check + Odysseus pin bump (same Arena session)

- Changed: no kit files were touched. Records only: `ODYSSEUS_SOURCE.md`
  pin bumped `c35a9256…` → `951d57db…` after the owner flagged that
  Odysseus `main` had moved that day (PR #15 merged minutes after the
  first inspection); this README's status, Section 2, evidence,
  discrepancies (X1 resolved; X9–X10 added), Step 0 entry conditions,
  owner checklist, and this entry updated to match the checked folder.
  The draft PR's title/body were also refreshed on GitHub to say the
  owner files have arrived (GitHub remains the source of truth there).
- Partial: the folder check is inventory-level only. There is still
  **no selftest baseline (0 runs)**, no detailed `FILES.md` compare, and
  no reading of any file inside either zip. That is Step 0, awaiting the
  owner naming it.
- Left (on purpose): extracting/running/installing anything from the
  zips; reading the 4 `harness.zip`-only documents; adopting the
  handoff's T1–T10 over this README's Steps (or vice versa) — see X10;
  all research and v2 building.
- Verified in this session: fetched the PR branch and fast-forwarded to
  owner commit `97a9fcc` (+7 files); folder inventory (9 top-level
  files with sizes and SHA-256); both zips have valid zip signatures;
  `ai-team-kit.zip` lists 16 `harness/` files; `harness.zip` lists the
  same 16 names with identical sizes/CRCs plus 4 extras; top-level
  guide size/CRC32 matches the in-zip `GUIDE.md` directory entry;
  `FILES.md`/`HANDOFF.md`/`PROVEN.md`/`OPEN.md` read in full; PR checks
  on the owner commit passed; Odysseus compare and re-clone as recorded
  in `ODYSSEUS_SOURCE.md`; then the workbench gate for this docs change
  (exact result in that day's chat report — re-run rather than trusting
  a quoted number later).
- Not verifiable here: any kit behaviour or selftest result; the truth
  of handoff "tested" claims; what `harness.zip` is *for*; current
  free-tier limits/terms; Windows/Mac/Codespace behaviour; real GitHub
  PR flows with the owner's accounts; Odysseus runtime at either pin.
- Docs touched: `ODYSSEUS_SOURCE.md` and this README (owner-uploaded
  files untouched).

### 2026-10-17 — unpack, learn, and match the old chat (same Arena session)

- Changed: added `KIT_LEARNING_AND_CHAT_MATCH.md` and updated this README
  (status, file table, Sections 1–2, evidence, restart story,
  discrepancies X2/X4/X9/X10, Step 0/queue, checklists, safety note, and
  this entry). **No kit code, guide, handoff note, zip, or Odysseus
  pointer was edited.** Scratch extraction lived only under
  `/tmp/ai-team-kit-learn-20261017/` and is not committed.
- Learned: `ai-team-kit.zip` is the canonical v1 PR-team glue kit
  (installer, `harness`, model picker, local dashboard, two skills,
  templates, launchers, guide). `harness.zip` is a byte-identical copy of
  those 16 files plus four extra documents, now classified in the report.
  Delivered provider config is OpenRouter, NVIDIA, Mistral, and Google
  Flash. The later patched scout, MCP loader/apply, Odysseus commands,
  extra provider presets, persona room, and toolchain installer are
  absent from both zips.
- Verified in this session: safe scratch extraction; full SHA-256
  inventory; 16/16 common zip members byte-identical; top-level guide =
  in-zip guide; kit/guide/skills/extras read; visible old chat re-read in
  four chunks and matched claim by claim; Python AST parse for both
  Python files; `bash -n` for both shell scripts; and exactly one
  isolated delivered `model_scout.py --selftest` run (Python 3.11.2,
  exit 0, stderr empty, **62 ok / 0 FAIL**, with
  `skip LiteLLM checks (litellm is not installed in this Python)`; full
  output in the learning report). The workbench gate result for this docs
  change belongs in the session's final chat report — re-run rather than
  trusting a quoted number later.
- Partial / not reproduced: the six LiteLLM Router checks inside the
  scout self-test (skipped, not passed here); all dashboard/`harness.sh`
  runtime claims and the claimed 84 dashboard checks; fresh install;
  real OAT/LiteLLM behaviour; real provider/GitHub flows. Current
  free-tier limits and terms remain unresearched for a future named task.
- Left (on purpose): no installer or runtime started; no T1/T2/Step 3 or
  v2 work begun; draft PR remains unmerged for owner review.
- Docs touched: `KIT_LEARNING_AND_CHAT_MATCH.md` (new) and this README.
