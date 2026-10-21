# AI Team Kit — research record and open questions

This file distils the archived `PROVEN.md` and `OPEN.md` snapshots into the
current research record. The raw snapshots remain under
`archive/2026-10-16-handoff-snapshot/`.

> **Read the labels.** “Old chat reported” means the previous chat said it ran,
> read, or found something in its own sandbox. It is useful and should not be
> redone casually, but it is **not** proof in this repository or on the
> owner's computer. Anything involving a current free tier, price, quota, or
> terms must be checked again from official sources when a task relies on it.

Decisions and rejected options from `PROVEN.md` are consolidated in
[`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md), with two later owner updates: MCP
for OAT confirmed on 2026-10-17, and the quota-aware provider-pool/adaptive-
council direction clarified on 2026-10-18.

---

## 1. Verified during the 2026-10-17 restart

These points have direct evidence in this repo/session:

- The canonical delivered kit is `ai-team-kit.zip`: 16 files under `harness/`.
  It is now extracted, unmodified, to `kit/harness/`.
- `harness.zip` was a superset: the same 16 files byte-for-byte plus four
  documents now preserved under `archive/harness-zip-extras/`.
- The delivered scout has four providers—OpenRouter, NVIDIA, Mistral, and
  Google—and three roles: architect, implementer, reviewer.
- The delivered `model_scout.py --selftest` was run once in isolation:
  Python 3.11.2, exit 0, 62 passed, 0 failed, empty stderr, with the LiteLLM
  Router checks explicitly skipped. Full output:
  [`reports/KIT_LEARNING_AND_CHAT_MATCH.md`](reports/KIT_LEARNING_AND_CHAT_MATCH.md),
  Appendix B.
- Static checks in the learning/audit tasks: both Python files parse, both
  shell scripts pass `bash -n`, and the dashboard inline JavaScript passes a
  syntax check.
- The delivered zips do **not** contain the patched scout, MCP loader/apply,
  `toolchains.sh`, or dashboard/MCP test harnesses.
- The Odysseus source pointer was read and pinned to
  `951d57db0e8758eadc3baed4af962860132a5f51` on 2026-10-17. That pin is a
  dated source inspection, not an install/runtime result. Re-check that repo's
  `main` immediately before calling the pin current.
- The owner's substantive old-chat requests were extracted and reconciled on
  2026-10-18: [`reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md`](reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md).
  Hidden attachments (including the first plan) are not recoverable from the
  share.
- **W-020 free-provider research ran on 2026-10-18** from official provider
  pages: [`reports/FREE_PROVIDER_RESEARCH_2026-10-18.md`](reports/FREE_PROVIDER_RESEARCH_2026-10-18.md).
  Headline results: OpenRouter `:free` = 20/min + 50/day (1,000/day after ≥10
  lifetime credits purchased; credits may expire after 365 days); Groq has a
  permanent published free plan; Google's free tier is per-model (Flash-class)
  and unpaid content may be used for training; NVIDIA's catalog is a
  prototyping trial with unpublished rate limits; Mistral Free mode is an
  included monthly allowance (numbers login-only, data may train unless opted
  out, stay off pay-as-you-go); Cloudflare gives 10,000 Neurons/day on the
  Free plan; **Cerebras has no permanent free tier** ($5/30-day trial after a
  payment method); **GitHub Models was retired 2026-07-30**. The owner's
  `awesome-freellm-apis` fork (`fadce14…`, in sync with upstream) was used as
  a discovery list only — it is stale in places (e.g. Cerebras). Remaining
  list providers are triaged leads (W-022), not verified.

---

## 1A. Owner-reported experience and direction, recorded 2026-10-18

These are **owner reports and design requirements**, not freshly verified
provider facts:

- The owner has used Google Colab with KoboldCpp for SillyTavern and reports
  that, in practice, limits felt mainly like available runtime/hardware and
  session time rather than a per-token API meter. That experience has not yet
  been checked against current official Colab terms/quota pages, and it does
  not prove the same pattern is allowed or reliable for an agentic harness.
- The owner previously tried giving tools multiple provider keys and asking
  for agentic work; rate limits made that approach effectively unusable. Any
  council design therefore needs call budgets, cooldowns, and fallback
  instead of multiplying background model calls.
- The intended pool is Google free tier, NVIDIA free tier, OpenRouter/other
  suitable providers, and an owner-started Colab/KoboldCpp endpoint while it
  is online. Mistral remains in the delivered v1 pool and is not removed by
  the clarification.
- The owner wants an Odysseus-based council that is simpler than the
  multi-agent systems they have seen, with an adaptive default: simulated
  personas in one call for light work, two or three real models for important
  decisions, and OAT agents for PR/code execution.

---

## 2. Old-chat reported findings: OAT

From `PROVEN.md` (snapshot dated 2026-10-16). Do not repeat this research
unless a named task needs current OAT source or a runtime proof:

- The real OAT installer is the Root-IO-Labs/open-agent-teams raw GitHub
  script. The old chat reported a clean-home install at v0.1.0.
- There is no `oat task` command or `--role` flag in the version it checked.
- `OAT_MODEL_ENDPOINT` / `OAT_MODEL_API_KEY` were not found in source. A custom
  provider through `~/.oat/config.toml` with `langchain_openai` reportedly
  reached a mock endpoint using an alias model name.
- `oat init` reportedly needs some provider key in the environment or
  `~/.oat/.env`; writing the LiteLLM master key as the OpenAI-style key let it
  proceed to cloning. That is why `harness connect-oat` writes both files.
- `oat init --no-merge-queue`, `oat repo use`, `oat list`, and
  `oat agent tell <agent> <text> --repo` were reported to exist.
- OAT state was reported to live in `~/.oat/state.json`, which is the shape the
  dashboard reads. No schema/contract test is delivered.
- An empty model-profile store reportedly means no model validation; after
  onboarding, model eligibility rules apply. This needs care in any real OAT
  task.
- Agents were reported to start with `--auto-approve`; Windows was described
  by OAT as not tested.
- Skills were reported to load from `~/.agents/skills` and a repo's
  `.agents/skills`, among other locations.
- The daemon started by the harness reportedly had zero AI-key variables in
  its `/proc` environment in the old sandbox. The audit explains why that is
  not, by itself, a complete secret boundary.

Still unresolved from the old chat:

- `oat-agent -n ... -M litellm:implementer` once printed nothing and no request
  reached the mock; the old chat worked around it by calling `create_model`
  directly. Cause unknown.

---

## 3. Old-chat reported findings: router, keys, and passwords

- LiteLLM fallbacks must be separate one-key dictionaries; a single dictionary
  with several role keys reportedly honoured only the first key under
  LiteLLM 1.103.2. The delivered scout writes separate dictionaries.
- The old chat reported that ordered deployments fail over and cool down as
  intended in its LiteLLM tests.
- LiteLLM's own default bind was reported as `0.0.0.0`; the delivered harness
  explicitly starts it on `127.0.0.1` and requires a master key.
- An unauthenticated router request returned HTTP 500 in the old sandbox due
  to a missing module there. Real-install behaviour was not established.
- The old chat tested that Ubuntu `passwd` refused an empty password and
  accepted weak examples. This is context for its setup advice, not a kit
  security proof.
- OpenRouter model fields used by the scout—pricing, supported parameters,
  expiration date, output modalities, created time, and `sort=top-weekly`—
  were reported to match OpenRouter documentation at the time.

### Dated external numbers from the snapshots

Do not quote these as current facts without a fresh official check:

- OpenRouter free-model requests were recorded as 20/minute, 50/day before
  $10 of lifetime purchased credit, and 1,000/day at $10+. Terms excerpts were
  recorded from search results. *(Superseded as evidence on 2026-10-18: W-020
  re-verified these same numbers in OpenRouter's own limits docs, plus the
  365-day credit-expiry reservation in its terms — see Section 1.)*
- Codespaces personal free allowance was recorded as about 120 core-hours/month
  and 15 GB storage, with idle/retention limits and a $0 default spending
  limit. *(Still unverified; only refresh for a Codespaces task — A7.)*
- Free-tier and data-use terms for NVIDIA, Mistral, Google, Groq, Cerebras,
  GitHub Models, and Cloudflare were **freshly checked in W-020
  (2026-10-18)** — including two closures: Cerebras's permanent free tier is
  gone and GitHub Models is retired. AI Horde and Colab remain task-time
  research (W-021/Q3/Q14).

---

## 4. Old-chat reported test results

The snapshot reported all of the following. Only the scout self-test has a
partial counterpart in this session, as noted in Section 1:

- Kit `model_scout.py`: 68 self-test checks passed on Python 3.12, 3.10, and
  3.14, including a local fake provider over real HTTP and LiteLLM Router
  checks. This session's delivered-file run found 62 passes plus the six
  LiteLLM checks skipped, which arithmetically reconciles with 68 when
  LiteLLM is importable.
- Dashboard: 84 checks (63 server + 21 page/DOM) passed. The test files are not
  delivered, so this cannot be rerun from the repo.
- Fresh install from the zip into a new home worked; a fresh LiteLLM install
  (reported 1.104.1) also worked with the self-test.
- `harness open` started router/OAT/dashboard with fakes, stop shut them down,
  and key replace/refuse/backup/remove flows worked against a fake provider.
- The guide and zip were presented to the owner as v1 deliverables.

Not established by those reports: real provider accounts/keys, real GitHub
token and PR flow, a real workspace-helper chat log, Windows/Mac/Codespace
specifics, or Docker.

---

## 5. Old-chat reported add-on research and sandbox builds

### Odysseus

The old chat researched a different/earlier Odysseus source state than the
owner's pinned fork inspected during the restart. It reported AGPL licensing,
a native `pip`/`uvicorn` start on `127.0.0.1:7011`, ChromaDB being unreachable
in that native run, MCP managed through Odysseus routes rather than an
`mcpServers` file, and a group-chat feature in source.

Do **not** repeat the old-chat sentence that Odysseus agent mode is “built on
OpenCode”; the pinned fork inspection in this session did not corroborate it.
For any Odysseus task, start from [`ODYSSEUS_SOURCE.md`](ODYSSEUS_SOURCE.md)
and the pinned repo, not from the snapshot's older source claims.

### AI Horde

The old chat reported an official OpenAI-compatible proxy at
`oai.aihorde.net`, kudos-based priority, lowest priority for anonymous use,
volunteers processing submitted text, and missing tools/functions/seed/
streaming/structured output in the converter. The owner-facing answer and a
live behaviour/terms check are still open.

### Personas and other harnesses

- The Agency (`msitarzewski/agency-agents`) was reported to contain many
  persona Markdown files and a converter to `SKILL.md`; its licence still
  needs reading before any use.
- OpenCode and Goose were identified as existing MCP-capable options from
  search results. No comparison or owner approval followed.

### Toolchains

The old chat reported Ubuntu 24.04 package versions for Qt/CMake, built a
tiny CMake project, and passed a headless QtTest with the offscreen platform.
`.NET SDK 8` installed, but the C# build could not reach NuGet from that
sandbox. No `toolchains.sh` was written.

### MCP for OAT

The old chat reported writing `oat_mcp_loader.py` and `oat_mcp_apply.py`;
loader behaviour with a broken server, idempotent apply, a stand-in model
calling an MCP tool through OAT agent creation (async and sync), and loading a
real fetch MCP server in its sandbox. Those files are absent from both zips.
Treat this as a rebuild specification with unknowns, not as code available to
reuse.

### OpenMAIC

Only search-result level information exists in the snapshot. No opinion was
given to the owner, and its README/licence still need direct reading.

---

## 6. Missing and blocked items carried forward

- Lost/never-presented files: patched `model_scout.py`,
  `mcp/oat_mcp_loader.py`, `mcp/oat_mcp_apply.py`, dashboard/MCP test
  harnesses and fake binaries, and the pre-patch scout backup in `/tmp`.
- Never written: `toolchains.sh`, harness MCP/Odysseus/dynamic-service
  commands, dashboard MCP/dynamic-role changes, guide add-on sections, and a
  v2 package.
- Pending owner answers: AI Horde support and OpenMAIC opinion.
- Requested but not built: persona/room feature and “lazy” MCP connections
  beyond a basic Connections card.
- Runtime areas unreachable or unproven in the old sandbox: real GitHub flow,
  live new-provider endpoints, complete C# build, Windows/Mac/Codespace
  behaviour, and Docker.

---

## 7. Research questions: current status

| ID | Question | Status on 2026-10-18 | How to resolve |
|---|---|---|---|
| Q1 | Did “MCP also” mean MCP for the OAT PR team? | **Resolved: yes.** Owner selected OAT MCP during the restart. | No research needed; build only when W-040 is named. |
| Q2 | What is OpenMAIC and does it fit? | **Open.** Search results only. | Read its primary README, licence, install/runtime model, and maintenance state; answer in plain words (W-021). |
| Q3 | How does AI Horde's OpenAI-compatible route behave live? | **Open.** Base path/model list/context/queue/anonymous use and current terms need direct checks. | Official docs plus a harmless live metadata check only if a named task authorises network use (W-021). |
| Q4 | What is The Agency repo's licence? | **Open.** | Read the repo `LICENSE` at a pinned commit before any persona conversion. |
| Q5 | Current free limits/terms and per-model free eligibility for the intended pool? | **Answered for the core pool on 2026-10-18 (perishable).** W-020 verified OpenRouter/NVIDIA/Mistral/Google/Groq/Cloudflare from official pages and produced the per-provider eligibility rule table for W-015; Cerebras's permanent free tier is gone and GitHub Models is retired. Exact Google/Mistral free numbers are login-only. | Re-verify quarterly and whenever a provider announces changes or error patterns shift. Second-wave providers from the owner's list fork: W-022. Colab remains Q14/W-021. |
| Q6 | What does a real workspace helper's output look like in Chat? | **Open.** Code assumes OAT log paths/format; old chat used a stand-in. | One real, owner-approved OAT run or a faithful captured fixture (W-016 and later runtime task). |
| Q7 | Does a daemon-launched OAT agent load MCP tools, what startup delay do `npx` servers add, and does an OAT upgrade overwrite a patch? | **Open.** Old loader tests did not prove the daemon path. | Rebuild in scratch, test apply/unapply and a daemon-launched harmless tool call (W-040). |
| Q8 | Odysseus programmatic providers/MCP, native ChromaDB, stability, shell risk, group chat/personas? | **Partially read, not run.** The restart inspected the owner's pinned fork docs/specs and downstream Providers/Auto/Council/MCP surfaces; changed spec bodies at the newer pin were not all re-read. No install/browser/runtime test. | Use `ODYSSEUS_SOURCE.md`, re-check pin vs `main`, read the exact routes/tests at task time, then only run if a named task authorises it. |
| Q9 | Does the real GitHub flow work end to end? | **Open.** Needs the owner's token/account and a disposable test PR. | Owner-run or owner-approved runtime task; report exact errors without exposing secrets. |
| Q10 | Does GitHub's remote MCP server accept a PAT for non-Copilot accounts? | **Open.** | Current official GitHub MCP docs at task time; test only with an approved scoped token. |
| Q11 | How should the Windows `.exe` be built/tested? | **Open; Gifscythe-side.** The snapshot suggested GitHub Actions `windows-latest`, with workflow-permission care. | A separate Gifscythe PR/workflow task, not assumed by the kit worklist. |
| Q12 | OpenCode extra harness, dashboard persona presets, or Docker? | **Partly narrowed again on 2026-10-18.** Odysseus is the intended room/council design centre and would be native if used; Docker only if asked. Final harness choice, persona presets, and adaptive escalation thresholds still need W-050 approval. | Quota-aware pool/adaptive-council design first (W-050), then owner decision. |
| Q13 | What happens when the WSL Start window closes? | **Open.** Sources conflicted. | Test on the owner's Windows/WSL setup and then fix guide wording. |
| Q14 | May the owner's Google Colab/KoboldCpp session be used as an online pool endpoint for Odysseus/the harness, and what limits/API behaviour apply? | **Open; owner intends this role while the session is online.** Owner roleplay experience is recorded in Section 1A, but current official terms, free/paid runtime quotas, disconnect/session rules, tunnel exposure, and KoboldCpp/OpenAI-compatible tool behaviour have not been freshly verified. | Official Colab terms/quota docs plus KoboldCpp primary API docs, and a harmless owner-approved endpoint check only if the named task permits it (W-021, then W-030/W-050 for design/implementation). |

---

## 8. Assumptions: current status

| ID | Assumption from `OPEN.md` | Status |
|---|---|---|
| A1 | “MCP also” means MCP for OAT too. | **Confirmed by owner, 2026-10-17.** |
| A2 | Odysseus can use LiteLLM as an OpenAI-compatible provider. | **Unverified runtime.** Pinned docs/source were inspected; no Odysseus run here. |
| A3 | Real free models can pass the scout's tool-calling probe. | **Unverified with real accounts.** Fake-provider logic passed the one baseline run, minus skipped LiteLLM checks. |
| A4 | Unpresented patch base URLs for AI Horde/Groq/Cerebras were correct. | **Partly superseded by W-020 (2026-10-18).** Groq's official OpenAI-compatible base (`api.groq.com/openai/v1`) is confirmed from provider docs; Cerebras is excluded (no permanent free tier) so its preset is moot unless trial use is chosen; AI Horde remains unverified (Q3/W-021). Still re-check every preset against official docs in W-030. |
| A5 | Real services behave like fake-provider tests. | **Unverified.** Provider error shapes and tool formats vary. |
| A6 | WSL keeps running while the Start window stays open. | **Unverified; see Q13.** |
| A7 | Codespaces figures are current. | **Dated claim.** Refresh from GitHub docs only for a Codespaces task. |
| A8 | Agency personas can be converted/installed through the Skills tab. | **Unverified; licence first (Q4).** The audit also requires skill-install hardening. |
| A9 | Chat can read real OAT workspace logs at the assumed path. | **Code assumption confirmed; real log unverified.** |
| A10 | Snapshot's OpenMAIC line is reliable. | **Treat as unconfirmed.** It was based on search wording/titles. |
| A11 | Odysseus group chat/Council can support the owner's quota-aware adaptive council. | **Doc-level only and design-open.** The pinned fork's Council material describes optional personas with a chair, and the owner wants simulated-first/real-council escalation, but neither quota budgeting nor real runtime behaviour has been proven here. W-050 must verify the design. |

---

## 9. Research rules for future tasks

- Use official provider documentation, pricing, terms, and licences for
  current external claims. Search snippets are leads, not final evidence.
- Record the date and exact source/commit for any free-tier or licence claim.
- Do not use the owner's real keys/tokens for a research check unless the
  named task explicitly requires it and the safety path is clear.
- Keep “source code exists”, “docs claim”, “fake test passed”, and “real
  runtime passed” as separate evidence levels.
- If a future result contradicts this file, update this file and the worklist
  in the same session rather than layering a second research record on top.
