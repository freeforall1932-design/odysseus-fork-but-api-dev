# Owner intent extracted from the old chat (recorded 2026-10-18)

## Why this file exists

The owner asked whether the original goal could be recovered from the old
shared chat instead of relying only on the old chat's own handoff snapshots.
This file records what the **owner personally asked for**, using the owner's
typed messages in the shared chat, so future sessions can check the worklist
against the owner's intent rather than against an assistant's paraphrase.

Source: `https://claude.ai/share/4b76ad92-cfd8-443a-b686-9fa20f1c23aa`
(shared by the owner; read again on 2026-10-18). The raw chat is **not** copied
into this repository. Only the owner's substantive requests are summarised or
quoted here; the many "continue" messages are omitted.

### Limits — read before trusting this as "the whole original plan"

- The shared chat hides file attachments. The owner's first visible message
  only says: *"Improvise this if any you found any flaw (optional work I just
  wanna review it)"* — the "this" is a hidden attachment. The very first plan
  document therefore **cannot be recovered from the share**. What survives of
  that era is inside the delivered kit's guide and the archived Gifscythe
  planning/review documents under `archive/harness-zip-extras/`.
- The owner also mentions giving the old chat a "session handoff for context"
  as an attachment. That attachment is likewise hidden in the share.
- Assistant replies in the share are old-chat reports, not proof. They are
  already handled with that label in
  [`workbench/projects/ai-team-kit/RESEARCH_AND_OPEN_QUESTIONS.md`](../RESEARCH_AND_OPEN_QUESTIONS.md).

---

## 1. The owner's substantive requests, in order

### 1.1 Oct 2 — smart model selection + skills (verbatim)

> "Continue where you left off and I forgot to give you session handoff for
> context also can you add smart selection since new model drop like every few
> months it's probably brittle to rely on old free tier if there's a new or
> limited time free that's better I also want skill integration do you think I
> need to make a custom harness for that so after all installation I need to
> patch it to be able to use skills and tools that they might not have"

Intent: do not hard-code today's free models. The system must discover and
re-select free models as providers change them, including limited-time free
offers — and helpers must be able to gain skills/tools they do not start with.

### 1.2 Oct 3 — beginner-friendly step-by-step (verbatim)

> "Can you remake the plan v2 into actual planning that streamline the plan so
> I can read it easily step by step installing the entire app and configure it
> and if you wanna add any of note from what's wrong etc etc from v1 put it at
> the very bottom since I don't need to know unless to troubleshoot or ask you
> later also write how to implement and test model scout.py and check whether
> the py file itself already correct lastly make the step by step and other
> that I need to read wording beginner friendly no complex term that's break
> the flow"

Intent: plain wording first, troubleshooting detail last; verify code before
presenting it; explain how to test the model picker.

### 1.3 Oct 4 — precautionary audit (verbatim)

> "Just for precautions review audit the code to find any leftovers missing
> logic misaligned code and error broken code bugs"

### 1.4 Oct 4 — the large requirements message (numbered decomposition)

The longest single owner message. Decomposed into separate asks; short exact
phrases are quoted.

1. **Repository memory must drive the team.** The owner runs projects with
   "session hand off, improvement log, worklist and other kind of md files
   depending on the project" and asked whether the helpers "will know how to
   pick that up and orchestrate it".
2. **Explain the browser/Codespaces option properly** — pros, cons, and
   warnings; whether its install matches the Ubuntu install.
3. **Isolation choices explained** — separate folder vs separate user vs
   Docker vs Codespace, in beginner words.
4. **Passwords** — what happens with an empty or very weak password.
5. **Daily restart on Windows** — how to "boot it back up" without remembering
   command sequences (the owner later accepted a double-click Start file).
6. **API-key behaviour** — keys entered one service at a time; what a skipped,
   failed, or replaced key does; the old key must not be silently lost.
7. **Paced probing to avoid rate limits** — "instead of running multiple model
   at the same time on same provider can it be distributed to 1 provider 1
   model at the time or 2 model at the time but there's a gap between each
   model test so not triggering spam", preferring the biggest or most-used
   weekly model first. The owner also reported that other agentic tools hit
   rate limits ("more prone to lag and rate limit than lmarena").
8. **No ambiguous status words** — the owner did not understand "EMPTY" and
   asked for clearer states such as "[offline]", plus a plan that details
   "any ambiguous situation while maintaining the simple way to install and
   use".
9. **GitHub permissions** — the owner uses a broader permission set than the
   guide's minimum and wants helpers able to change workflows when needed.
10. **A real GUI, not a terminal** — "I don't need to remember many command
    and name just hover and click"; chat-like work "like in agentic work or
    chat like this"; quality bar named later the same day: Arena.ai agent UI,
    Qwen/LMArena-style workspaces, Replit-style GitHub connection, local
    browser server is fine, simple one-click start "maybe like bat file".
11. **Self-extending helpers** — if a model lacks a skill or cannot do
    something, it should research how, find the plugin/`SKILL.md`, and add it
    itself; it may change workflow files directly when the permissions allow.
12. **Verify the OpenRouter "$10 → 1,000/day" claim**, including whether the
    terms let OpenRouter take the higher limit away later.
13. **Design/skill repositories can be added by the owner** — named example:
    Microsoft's SkillOpt "or other stuff".

### 1.5 Oct 8 — Odysseus, MCP, council, toolchains, personas (verbatim)

> "Does this plan already taking into account using Odysseus harness or other
> type that can accommodate this and including multiple popular source Nvidia
> nim or using Google studio and google colab like
> https://colab.research.google.com/github/lostruins/koboldcpp/blob/concedo/colab.ipynb
> and have mcp plugin and tools like lmstudio with mcp JSON like using my pat
> account to commit work on GitHub repo or make web search sequential thinking
> etc etc how about other repo that cover this kind of council or agent team
> like that one repo about team dev agent so it's like orchestrator and sub
> agent doing the task say game code and programm and front end GUI on
> designer etc etc type of like that and don't forget the environment to
> testing project like qt6 or qt cmake or c# csharp and other difficult task
> on coding and versatile on daily use and other capabilities like writing
> fanfic just by swapping the model the harness provide like a room
> accommodating people with multiple personalities that each have their own
> specialization and needs"

Intent, unpacked:

- one harness/room that can host many model sources (NVIDIA NIM, Google AI
  Studio, Colab/KoboldCpp named with a specific notebook link);
- MCP plug-ins configured LM Studio-style (`mcp.json`), including GitHub via
  the owner's PAT and web-search/sequential-thinking tools;
- a council/agent-team pattern: orchestrator plus specialist sub-agents
  (game code, programming, front-end/GUI, design);
- real test environments for Qt6/CMake and C#;
- the same room should serve daily use and creative writing (fanfic) by
  swapping models — "a room accommodating people with multiple personalities
  that each have their own specialization and needs".

### 1.6 Oct 10 — short decisions (verbatim)

> "Native and MCP also does it support AI horde from community backed models
> that run on kudos"

Later the same period: "what do you think about openmaic repo". Both were
still unanswered when the old chat stopped; they are now W-021/Q2/Q3.

---

## 2. Owner intent added after the restart (2026-10-17 / 2026-10-18)

These are **not** from the old chat; they refine it:

- MCP for the OAT pull-request team: **yes** (2026-10-17).
- Odysseus **native**, not Docker, if used (matches 1.6).
- A **quota-aware provider pool**: Google free tier, NVIDIA free tier,
  OpenRouter free models, other suitable providers, delivered Mistral, plus an
  online Colab/KoboldCpp session as a core pool member with API fallback.
  Colab moves from "asked about, assistant advised against" (old chat) to
  "intended while online, terms still to verify" (2026-10-18).
- An **adaptive council** (simulated personas → small real council → OAT
  execution). The old chat asked for a council/orchestrator and a persona
  room; the *adaptive escalation* is the 2026-10-18 refinement.
- Explicit **anti-rate-limit protection**: the owner reports that directly
  entering several API keys into agentic tools hit rate limits and became
  effectively unusable, and asked whether the worklist prevents a free-tier
  API from "combusting itself on error". Strengthened requirements were added
  to W-015/W-020/W-050 on 2026-10-18.
- **Systematic free-provider discovery** from the owner's
  `awesome-freellm-apis` fork, including where to get each key and each
  provider's signup requirements — folded into W-020 on 2026-10-18 and first
  executed in
  [`FREE_PROVIDER_RESEARCH_2026-10-18.md`](FREE_PROVIDER_RESEARCH_2026-10-18.md).

---

## 3. Reconciliation: intent → where it lives now

| Owner intent (section above) | State today |
|---|---|
| Smart, self-updating free-model selection (1.1) | v1 scout exists (4 providers/3 roles). Free-eligibility proof and rate-limit guard: W-015 + W-020 evidence. Dynamic providers/roles: W-030–W-032. |
| Skills/helpers gain missing tools (1.1, 1.4.11, 1.4.13) | v1 has `team-workflow` + `self-extend` skills and a Skills tab. Safety: W-014. Self-install behaviour is instruction-level only; MCP tools: W-040. |
| Beginner wording, detail last, verify before presenting (1.2, 1.3) | Guide rewrite: W-070. Standing working rule in `PROJECT_CONTEXT.md`. |
| Repo Markdown memory orchestrates work (1.4.1) | v1 `team-workflow` skill points helpers at handoff/worklist/log files; real-helper behaviour unverified (research Q6/A9). |
| Codespaces/isolation/passwords/restart explained (1.4.2–1.4.5) | Partly in v1 guide; accuracy/refresh: W-070. WSL-close behaviour Q13. |
| Key entry/replacement safety (1.4.6) | v1 exists; hardening W-010/W-013. |
| Paced probing, no quota spam (1.4.7) | v1 probes paced by default. Full runtime rate-limit guard: W-015/W-050 (strengthened 2026-10-18). |
| Clear status words, no ambiguity (1.4.8) | v1 uses `[OK]/[offline]/[refused]/[limit]` style states; dashboard pool states incl. cooldown: W-032. |
| Broader GitHub permissions incl. workflows (1.4.9) | Owner's own setup choice; documented requirement only — no agent changes GitHub settings (W-010 notes recommended scopes). |
| Arena/Qwen-class GUI, one-click start (1.4.10) | v1 dashboard + Start files exist (basic, not Arena-class). Room/GUI decision: W-050; dynamic dashboard: W-032. |
| OpenRouter $10 claim verified (1.4.12) | Re-verified from official docs in W-020 research (2026-10-18). |
| Odysseus/other harness, many sources incl. Colab (1.5) | Not in v1. Design: W-050. Colab terms: W-021/Q14. Dynamic endpoints: W-030/W-031. |
| MCP LM Studio-style, GitHub PAT, web search/thinking tools (1.5) | Not in v1 (files lost). Rebuild: W-040. GitHub MCP auth question: Q10. |
| Orchestrator + specialist sub-agents (1.5) | OAT supervisor/workers exist in v1 (old-chat reported config); persona/specialist design: W-050. The Agency licence: Q4. |
| Qt/CMake/C# test environments (1.5) | Not written. W-060. |
| Daily use + fanfic via model swap; persona room (1.5) | Writer/editor roles: W-030. Room/personas: W-050/W-051. |
| Native + MCP; AI Horde? OpenMAIC? (1.6) | Native recorded; MCP yes (W-040). AI Horde/OpenMAIC answers: W-021. |
| Quota-aware pool + adaptive council (2026-10-18) | Direction recorded; design W-050; metadata W-015; evidence W-020. |
| Provider discovery + signup requirements (2026-10-18) | W-020 first pass done 2026-10-18 for the core eight; remaining list providers are triaged leads in the W-020 report, not verified. |

Nothing in the old-chat requests contradicts the current worklist. The two
places where today's direction goes **beyond** the old chat are the adaptive
council escalation and Colab's promotion to intended online pool member; both
are owner decisions recorded on 2026-10-18, not old-chat claims.

---

## 4. Tested / not tested for this extract

- **Read:** all four chunks of the shared chat on 2026-10-18; owner messages
  only were used for intent. The kit files and snapshots were **not** re-read
  for this extract beyond the already-committed reports.
- **Not recoverable from the share:** hidden attachments (including the
  original plan and the context handoff the owner gave the old chat), file
  contents the old chat produced, and anything the share page truncates.
- **Not verified here:** any old-chat assistant claim, and whether the share
  link will remain available. If the owner still has the original plan file,
  adding it to `archive/` would close the "initial goal" gap for good.
