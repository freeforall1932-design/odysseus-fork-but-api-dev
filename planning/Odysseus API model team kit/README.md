# Odysseus API model team kit

> **Migration update:** this project now lives in the root folder named
> **Odysseus API model team kit** and ships as a fourth portable ZIP. Start with
> [MIGRATION.md](MIGRATION.md). The original workbench path is a compatibility
> symlink. This is a packaging/name change, not a completed Odysseus integration.

> **Status on 2026-10-18: extracted, reorganised, and statically audited;
> intended provider-pool/council direction recorded — waiting for the owner
> to name the next worklist item.**
>
> The canonical v1 kit is now visible as source in `kit/harness/`. Both old
> zip files were deleted only after their contents were extracted and the
> extraction was recorded. No installer, router, OAT agent team, dashboard,
> model provider, or GitHub runtime was started for the audit, and no kit code
> was fixed or changed. Later on 2026-10-18 the owner's old-chat intent was
> extracted, W-015/W-020/W-050 were strengthened against rate-limit
> self-harm, and **W-020 verified the core providers' free offers on official
> pages** — desk research only: no signups, keys, installs, or provider calls.
> This folder then moved under `workbench/projects/` at the owner's request,
> gaining a sibling `workbench/projects/kobold-cli/` for the Colab/KoboldCpp
> arm (whose first report dissects the official Colab notebook). The owner
> subsequently requested a direct test link and a codebase sweep: kobold-cli
> gained a test notebook and one-line Colab link file, and
> `workbench/projects/CODEBASE_SWEEP_AUDIT_2026-10-18.md` records the
> stale/bug/upgrade findings. After the first custom notebook failed in the
> owner's real Colab run, it was rebuilt from the actual official notebook
> (upstream loader retained; coding/API settings changed) and executed
> locally with stubbed download/binary commands. A successful real Colab
> GPU/model/tunnel run is still pending; W-021/Q14 remains open.

This folder contains the AI Team Kit project for the owner's Gifscythe
repository. The kit's aim is a beginner-friendly team of cloud AI helpers that
uses free models only, works through GitHub pull requests, and leaves merging
to the owner.

### Intended next destination (not implemented in v1)

Recorded from the owner's clarification on 2026-10-18:

- a **quota-aware model pool** spanning Google free tier, NVIDIA free tier,
  OpenRouter free models, other suitable providers, and the delivered
  Mistral source;
- an **online Colab/KoboldCpp session as a core pool member** while it is up,
  with API fallback when it is offline (current terms/API behaviour still
  require W-021 research);
- an **adaptive council**: one model simulates persona viewpoints for light
  questions, two or three real models decide important questions, and OAT
  agents are reserved for repository/PR work;
- **Odysseus as the intended simpler room/council surface**, subject to the
  W-050 design comparison and approval.

This matters because the owner's earlier attempt to use several directly
entered API keys for agentic work hit rate limits and became effectively
unusable. The pool therefore needs shared budgets, cooldowns, health, and
fallback—not more uncontrolled agents.

## Start here

| If you want to… | Read |
|---|---|
| Understand what to read and in what order | [`READING_GUIDE.md`](READING_GUIDE.md) |
| Resume the project safely | [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md) |
| Choose or track remaining work | [`WORKLIST.md`](WORKLIST.md) |
| Understand the goal, parts, decisions, and old-chat direction | [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) |
| See what is risky, broken, partial, or missing in code | [`reports/CODE_AUDIT_2026-10-17.md`](reports/CODE_AUDIT_2026-10-17.md) |
| See how delivered v1 works and how old-chat claims matched it | [`reports/KIT_LEARNING_AND_CHAT_MATCH.md`](reports/KIT_LEARNING_AND_CHAT_MATCH.md) |
| See which free providers/models are real, conditional, or gone (W-020) | [`reports/FREE_PROVIDER_RESEARCH_2026-10-18.md`](reports/FREE_PROVIDER_RESEARCH_2026-10-18.md) |
| See the owner's original requests in the old chat | [`reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md`](reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md) |
| Check research findings and still-open questions | [`RESEARCH_AND_OPEN_QUESTIONS.md`](RESEARCH_AND_OPEN_QUESTIONS.md) |
| Find any file or the zip-deletion record | [`FILE_MAP.md`](FILE_MAP.md) |
| Find the separate Odysseus program source | [`ODYSSEUS_SOURCE.md`](ODYSSEUS_SOURCE.md) |

Shortest useful path: this README → handoff Sections 1–4 → audit short
verdict/P0 → worklist W-001 and the item you are considering.

## Current verdict

**V1 is coherent source, not yet a runtime-proven install.**

What lines up: the installer, `harness` command, model picker, local
dashboard, built-in skills, launchers, and guide mostly agree with each other.
Static checks found no syntax failure and no obvious placeholder feature.

What must not be overstated:

- OpenRouter free status is price-checked, but NVIDIA, Mistral, and Google are
  currently `assume_free` in the scout. W-020 (2026-10-18) has now published
  the per-provider evidence rules — Google free is per Flash-class model,
  NVIDIA is a prototyping trial with unpublished limits, Mistral free is a
  monthly allowance — but **the code does not encode them yet** (W-015), and
  v1 still cannot tell how much quota remains.
- Installer downloads/versions are not pinned and verified strongly enough.
- Helpers and kit secrets share one OS account; environment cleanup and skill
  instructions are not a complete security boundary.
- Some shell flows can report started/stopped/auto-merge-off after an OAT
  command failed.
- Model refresh can remain stale when key checks update state or when an
  already-running router is not restarted.
- Dashboard mutating jobs have no single-flight lock.
- Third-party skill installation can copy through symlinks.
- Dynamic roles/services, MCP, Odysseus/personas, extra providers, Docker,
  toolchains, and the lost test harnesses are absent from v1.

The full findings, evidence, and suggested fix order are in
[`reports/CODE_AUDIT_2026-10-17.md`](reports/CODE_AUDIT_2026-10-17.md). The
corresponding tasks are W-010…W-016 in [`WORKLIST.md`](WORKLIST.md).

## Folder map

```text
workbench/projects/ai-team-kit/
├─ README.md                         This index
├─ SESSION_HANDOFF.md                Current state + next-session gate
├─ WORKLIST.md                       Single actionable queue
├─ PROJECT_CONTEXT.md                Goal, architecture, decisions, old-chat intent
├─ RESEARCH_AND_OPEN_QUESTIONS.md    Findings and Q/A status
├─ READING_GUIDE.md                  Section-by-section summaries for the owner
├─ FILE_MAP.md                       File locations + extraction record
├─ ODYSSEUS_SOURCE.md                Pointer to the separate Odysseus repo/pin
├─ kit/harness/                      Canonical extracted v1 source
├─ reports/                          Learning report, code audit, owner-intent + provider research
└─ archive/                          Original snapshots, former README, zip extras
```

There is no top-level zip anymore. The former duplicate
`AI-Team-Setup-Guide.md` was also removed; the only guide to edit in a future
guide task is `kit/harness/GUIDE.md`. A new distributable zip should be made
only in worklist item W-080, after the code and guide it contains are ready.

## Done / not done

### Done as delivered v1 source

- Installer and one `harness` command.
- Model scout for OpenRouter, NVIDIA, Mistral, and Google.
- Three stable roles: architect, implementer, reviewer.
- LiteLLM router-list generation and OAT connection helpers.
- Local dashboard for chat, tasks, files/changes, PRs, models, keys, skills,
  and logs.
- Two built-in skills with project-memory templates.
- Windows/Mac launchers and a beginner guide.

### Not done or not present

- Any audit fix (the audit was read-only for kit code).
- Writer/editor roles, dynamic endpoints/services, `add-endpoint`.
- MCP loader/apply, `harness mcp`, and dashboard MCP controls.
- Odysseus integration, persona room, or adaptive-council implementation;
  only a source pointer and a design requirement exist.
- A quota-aware multi-provider pool in code; Groq/Cloudflare presets, AI
  Horde, and online-Colab session support. (W-020 verified the offers on
  paper only; Cerebras has no permanent free tier and GitHub Models is
  retired, so neither is coming.)
- `toolchains.sh`, Docker packaging, and a harness-comparison verdict.
- Delivered dashboard/MCP test harnesses claimed in the old chat.
- A real install/runtime proof with the owner's keys, GitHub account, and
  target platforms.

## Tested / not tested

### Tested or verified in this restart

- Both zips were inventoried and compared byte-for-byte; extraction into
  `kit/harness/` and `archive/harness-zip-extras/` preserved their contents
  and modes.
- The delivered scout self-test was run **once** in an earlier owner-named
  task: Python 3.11.2, exit 0, **62 passed, 0 failed**, empty stderr, with the
  LiteLLM Router checks skipped. It was **not rerun** for the audit.
- Python AST parsing, `bash -n`, inline-JavaScript syntax checking, and
  command/route/action cross-checks all passed as static checks.
- The Odysseus pointer repo was inspected/read at a dated pin; it was not
  installed or run.
- W-020 (2026-10-18): official pricing/limits/terms for OpenRouter, NVIDIA,
  Mistral, Google, Groq, Cerebras, GitHub Models (retirement), and Cloudflare
  were read and dated. That verifies what the providers *publish*, not how
  their APIs behave with a real key.

### Not tested here

Installer execution; LiteLLM; OAT; dashboard runtime; real provider accounts,
models, or keys (including every login-only limits page and all Colab
behaviour); real GitHub login/PR/merge/close; Windows/WSL; macOS;
Codespaces; Odysseus; MCP; Docker. Old-chat “tested” statements remain
old-chat reports unless the learning/audit report explicitly reproduced them.

## Owner's next step

1. Review draft PR #3 and, if desired, use
   [`READING_GUIDE.md`](READING_GUIDE.md) for the short path.
2. Name **one** item from [`WORKLIST.md`](WORKLIST.md). The recommended order
   starts with P0 hardening and the missing tests, then fresh provider
   research, then the old v2 expansion slices.
3. If the reply is only “next” or “continue”, the agent must ask which `W-`
   item rather than guessing.

Standing rules: free/cloud models only; owner reviews and merges PRs;
beginner wording; downloadable results; read real files before editing; look
up current free-tier terms from official sources; never commit secrets or
runtime state.
