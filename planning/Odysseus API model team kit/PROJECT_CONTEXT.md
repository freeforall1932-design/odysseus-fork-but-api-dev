# AI Team Kit — project context

This file explains **what the project is for, what has been decided, how the
pieces fit, and what the old chat intended to do next**. It is context, not a
task list. The actionable queue is [`WORKLIST.md`](WORKLIST.md); the current
state is [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md).

---

## 1. The goal in plain words

The owner wants a small **AI team** for the GitHub project
`freeforall1932-design/gifscythe`:

- **Free models only.** No paid model use as the plan.
- **Cloud APIs only.** The models run on internet services, not as local
  models on the owner's computer.
- **Beginner-friendly.** Plain words, few commands to remember, and a browser
  dashboard with buttons.
- **Pull-request workflow.** Helpers prepare changes as pull requests. The
  owner reads them and decides whether to merge.
- **Honest evidence.** Every report says what was tested and what could not be
  tested. An old chat saying “tested” is a report, not new proof.

This folder is inside the separate `dionysus` repository because that is the
owner's workbench. **Gifscythe is the target project; `dionysus` is where this
kit project is being organised.** Work for this project stays under
`workbench/projects/ai-team-kit/` unless the owner names a task that says otherwise.

The owner's own requests from the old chat—quoted and decomposed, with the
limits of what the shared-chat link can still show—are preserved in
[`reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md`](reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md),
including a reconciliation table (intent → v1 feature or worklist item). When
this file and that extract disagree, the owner's newest instruction wins.

---

## 2. What v1 is

Version 1 is the **pull-request team kit** now extracted under
[`kit/harness/`](kit/harness/). It contains glue code and instructions; OAT
and LiteLLM themselves are downloaded by the installer rather than bundled.

| Part | Plain role |
|---|---|
| `install.sh` | One-time setup: checks tools, installs `uv`, LiteLLM, and OAT, links the `harness` command, installs built-in skills, and can place Windows shortcuts. |
| `harness.sh` | The owner's one command: keys, check, scout, start/stop, doctor, dashboard, GitHub login, OAT connection, add a repo. |
| `model_scout.py` | The model picker. It reads provider catalogues, paced-tests candidate models, ranks them for stable job names, and writes the LiteLLM router list plus a report/state file. |
| LiteLLM router | One local doorway. Helpers ask for `architect`, `implementer`, or `reviewer`; the router forwards to the currently picked provider/model and can try backups. |
| OAT | The agent-team program. It manages repos, a workspace helper, worker helpers, worktrees, and pull-request work. |
| `harness_ui.py` | A local browser dashboard for chat, tasks, direct model questions, files, changes, PRs, models, connections/keys, skills, and logs. |
| Built-in skills | Instructions that teach helpers to use project handoff/worklist/log files and to research missing capabilities cautiously. |
| Launchers | Double-click Start/Stop helpers for Windows (through WSL) and Mac. |
| `GUIDE.md` | The beginner setup and use guide. The former top-level `AI-Team-Setup-Guide.md` was byte-identical to this file and was removed as a duplicate during the 2026-10-17 reorganisation. |

### The normal v1 flow

1. The owner installs the kit and saves free provider keys.
2. `harness scout` (or a stale-check during `harness start`) writes a router
   list mapping the three stable role names to ranked models.
3. `harness start` starts LiteLLM on loopback port 4000 and then OAT.
4. `harness connect-oat` tells OAT to use the router's role names.
5. `harness add-repo <GitHub URL>` adds a project and intends to disable OAT's
   merge queue.
6. The owner uses the dashboard on loopback port 8765 to chat with the
   workspace helper or start a worker task.
7. Helpers work in their own copies and open pull requests.
8. The owner reviews the changes and chooses Merge or Close.

The static audit found several places where this intended flow needs hardening
before it should be trusted end-to-end. See
[`reports/CODE_AUDIT_2026-10-17.md`](reports/CODE_AUDIT_2026-10-17.md).

---

## 3. Decisions to keep

Decision labels in the archived snapshots overlap (`D1` means different things
in different files), so this file uses plain names instead of reusing those
IDs.

### Product decisions

- **Free tiers and cloud APIs only.** Local model runners and paid credit are
  not part of the plan unless the owner explicitly changes this.
- **The owner is the merge gate.** No auto-merge assumption. OAT's merge queue
  is intended to stay off.
- **Paced model testing.** Test models gently, one at a time per service by
  default, with pauses and request budgets. Show refused/offline/limited
  states instead of silently dropping services.
- **Stable role names.** Helpers should ask for job names rather than hard-code
  a provider model that may disappear.
- **Errors must calm the system down, never make it retry harder.** A `429`,
  timeout, or provider failure triggers bounded, visibly-counted behaviour:
  honour `Retry-After`, capped retries with backoff and jitter, per-provider
  cooldowns/circuit breakers, one request in flight per provider by default,
  and a graceful stop when quota is exhausted. No hidden background retry
  loops and no multi-account tricks to evade limits. The detailed, testable
  version of this rule lives in W-015 (scout/config) and W-050 (runtime
  design); provider limits come from W-020 evidence.

### Owner-confirmed direction after the restart

- **MCP for the OAT pull-request team: yes.** The archived snapshot was unsure
  whether “MCP also” meant OAT; on 2026-10-17 the owner selected yes. This is
  a direction for a future named build, not something present in v1.
- **Odysseus native, not Docker — if Odysseus is used.** “Native” means a
  direct Ubuntu/WSL install. This does not by itself choose Odysseus as the
  winning room harness.
- **Odysseus source address if needed:** the owner's
  `freeforall1932-design/odysseus-fork-but-api-dev`, used only at the commit
  pinned in [`ODYSSEUS_SOURCE.md`](ODYSSEUS_SOURCE.md). It is pointed to, not
  copied into `dionysus`.

### Owner clarification recorded on 2026-10-18: provider pool + adaptive council

This clarification corrects and sharpens the intended target. It is a design
direction, not a claim that any of it is implemented yet.

- **Why a team/council is needed:** the owner has already tried pasting API
  keys into tools and asking for agentic work; the result ran into rate limits
  and was effectively unusable. A useful system must therefore treat quota as
  a shared budget, not as something each agent can spend freely.
- **Intended model pool:** Google free tier, NVIDIA free tier, OpenRouter
  free models, other suitable free providers, and an owner-started Google
  Colab/KoboldCpp endpoint **when that Colab session is online**. The existing
  v1 Mistral entry is not removed by this clarification.
- **Colab's intended status:** a core pool member while online, with
  automatic fallback to provider APIs when the runtime/session is offline.
  The owner reports using Colab/KoboldCpp for SillyTavern as a practical
  high-token source whose practical constraints are rented runtime and
  hardware rather than per-token API billing. That is owner experience, not
  yet a verified statement about current Colab terms, quotas, endpoint
  stability, or agentic use; W-020/W-021 and Q14 must check those before the
  design relies on them.
- **Odysseus is the intended simpler council/room surface to design around**,
  in the spirit of multi-persona council systems the owner has seen, but using
  API/cloud endpoints instead of local models. This still needs W-050's
  primary-source design check before it becomes an approved build choice; OAT
  remains the pull-request execution team in the current architecture.
- **Default council style is adaptive:**
  1. use one model to simulate several persona viewpoints and then chair the
     synthesis for light questions and drafts;
  2. use a small real council of two or three models/providers for important
     or contested decisions;
  3. reserve separate OAT agents and tool-heavy provider calls for actual
     repository/PR execution, normally in an architect → implementer →
     reviewer sequence rather than many parallel workers.
- **What this means for audit A-01:** the issue is not “Google/NVIDIA have no
  free tier”. It is that v1 cannot yet distinguish free-tier-eligible models
  and remaining quota from every model merely listed by an endpoint, and it
  has no Colab/custom-endpoint or council budget layer at all. W-015 plus the
  provider-pool work in W-020/W-030/W-050 must encode eligible models,
  capability, health/cooldown, task budgets, and fallback.

### Working rules

- The owner names **one task at a time**. “Next” or “continue” alone means ask
  which task.
- Read the real files before changing them; edit in place rather than
  regenerating from memory.
- Do not repeat research already recorded unless a task needs fresh official
  terms/limits. Provider free tiers are dated claims and must be rechecked at
  the time they are relied on.
- Deliver downloadable files and beginner-friendly wording.
- Never commit keys, tokens, passwords, runtime state, or private chat logs.
- Keep upstream `assets/` and `dotfiles/` untouched.

---

## 4. What was rejected or dropped in the old chat

These are recorded so a future session does not redo the same loop. They are
old-chat findings, not fresh 2026-10-17 re-tests:

- **llm-keypool:** dropped; the old chat reported a CLI flag mismatch and that
  LiteLLM already covered rotation/failover needs.
- **OmniRoute:** not needed once LiteLLM was chosen.
- **Claw Orchestrator:** dropped as overlapping OAT and oriented around paid
  coding CLIs.
- **The first v1 OAT installer URL:** rejected as belonging to another project;
  the kit uses Root-IO-Labs/open-agent-teams.
- **Multiple OpenRouter accounts/keys to raise free limits:** dropped based on
  the old chat's reading of OpenRouter docs.
- **Colab/KoboldCpp as an assumed always-available core API:** dropped in the
  old chat because it read Colab's terms as disallowing the intended
  remote-service pattern. The owner's 2026-10-18 clarification reopens it as
  an intended **owner-started pool endpoint while online**, but current
  terms, quota/session behaviour, and API compatibility remain unverified and
  must be checked before any design or use relies on it.
- **AI Horde for tool-using coding roles:** rejected for those roles because
  its OpenAI-compatible route was reported to lack tools/functions and other
  agent features. Text-only creative use remains a research/design question.
- **Docker for Odysseus:** not chosen; native was chosen.
- **Parallel model probing:** replaced by paced probing.
- **A role with no model shown as “EMPTY”:** replaced by borrowing from other
  roles or `unavailable`.

---

## 5. What the old chat was going to do when it stopped

The old chat had already delivered v1. Its next phase was an expansion, not a
repair of a missing v1 core:

1. **Creative roles and more model sources.** Add writer/editor roles that can
   use text-only models, plus endpoint presets/custom endpoints for sources
   such as AI Horde, Groq, and Cerebras. A scout patch was reportedly written
   in the old sandbox but never presented and is not in either zip.
2. **Make the harness dynamic.** Replace the shell's fixed service list with
   scout-provided `--list-services`, and add `harness add-endpoint`.
3. **Add MCP to OAT.** The old chat reportedly wrote and sandbox-tested a
   loader and an apply/unapply manager, then planned `harness mcp ...`
   commands and a dashboard Connections card. Those files were never presented
   and are absent here; they must be rebuilt if the owner names that task.
4. **Add Odysseus as the native “room”.** Planned harness commands for a
   pinned native install/start/stop/open and a dashboard link, with personas
   for writing/daily use. The separate source pointer now exists, but no kit
   integration does.
5. **Add build toolchains.** A planned admin-run `toolchains.sh` for Qt6,
   CMake, Ninja, g++, Xvfb, .NET 8, clangd, and Node so helpers can build and
   test Gifscythe work. It was never written.
6. **Update the dashboard for dynamic roles/services** and recreate its lost
   tests.
7. **Update the guide, repackage, and run the full/fresh-install tests.**
8. **Optional later choices:** persona presets, OpenCode as another harness,
   or a Docker version only if asked.

### How that maps to the current worklist

The new [`WORKLIST.md`](WORKLIST.md) keeps the old `T1`–`T10` references but
adds a safety/test stage first, because the static audit found issues in
exactly the areas the expansion would touch: secrets, installer trust,
process lifecycle, dynamic config, skill installation, and missing tests.

---

## 6. What is not decided yet

Do not build on these as if they were approvals:

- Final approval of Odysseus as the room/council after W-050 checks it against
  OpenCode, Goose, and OAT; the owner's intended design centre is Odysseus,
  but responsibilities and safety still need the design task.
- The detailed orchestrator/sub-agent design (game code, programming,
  front-end/GUI, design, writing/daily-use personas) and the exact adaptive
  council thresholds for switching from simulated to real multi-model work.
- Whether AI Horde should be added after a fresh live/terms check.
- Whether the owner's KoboldCpp Colab endpoint may be used for this workflow
  under current terms, and how its session/API limits behave in practice.
  Intended use is now clear; permission and reliability are not yet proven.
- Any use or opinion of OpenMAIC beyond “needs reading”.
- Extra providers beyond the delivered four (Groq, Cerebras, GitHub Models,
  Cloudflare, custom endpoints) until their current free terms and API shapes
  are checked.
- “The Agency” persona conversion, SkillOpt, ChatDev, MetaGPT, or CrewAI.
- Paying any provider.
- Promoting this folder into the wider workbench index/project tables.

---

## 7. Evidence hierarchy

When documents disagree, use this order:

1. **Owner's latest explicit instruction** — for what to do now.
2. **Real extracted kit files** — for what v1 code actually does.
3. **This session's dated reports** — the kit learning report and code audit,
   within their stated tested/not-tested scope.
4. **[`ODYSSEUS_SOURCE.md`](ODYSSEUS_SOURCE.md)** — for the Odysseus repo
   address/pin and what was read there; re-check `main` before calling a pin
   current.
5. **Archived 2026-10-16 snapshots** — useful route/research notes, but they
   may contain errors and report old sandbox work that is not present here.
6. **Visible old-chat text** — a source of claims and intent, not proof that a
   file or runtime result exists in this repo.

The raw snapshots are preserved under
`archive/2026-10-16-handoff-snapshot/`; their content is distilled in
[`RESEARCH_AND_OPEN_QUESTIONS.md`](RESEARCH_AND_OPEN_QUESTIONS.md) and the
worklist.
