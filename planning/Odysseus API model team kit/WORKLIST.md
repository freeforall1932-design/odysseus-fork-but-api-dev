# AI Team Kit — worklist

One queue for everything that still needs doing: the 2026-10-17 code-audit
fixes, the old chat's `T1`–`T10`, and the restart session's Steps. The old IDs
are kept as cross-references so nothing is lost.

## Rules for using this list

- **The owner names one `W-` item at a time.** “Next” or “continue” alone
  means: ask which item.
- No item below is authorised just because it is listed.
- Edit the real extracted files in `kit/harness/` in place; do not regenerate
  them from memory.
- Every code item must add or update a test that can fail, and must say what
  was tested and what could not be tested.
- Do not rerun the model-picker self-test as a ritual. Rerun it only inside a
  named task that changes the scout or its test environment.
- Provider limits/terms must be checked from official sources in the task
  that relies on them.
- Update `SESSION_HANDOFF.md`, this worklist, and any affected context/research
  file in the same session as the work.

## Owner direction recorded on 2026-10-18

| direction | what it means in plain terms | work that must honour it |
|---|---|---|
| Quota-aware team, not “keys pasted everywhere” | A previous non-team attempt to do agentic work through provider keys hit rate limits and became effectively unusable. Provider/model choice must therefore track free-tier eligibility, capability, recent `429`/cooldown state, task budgets, and fallback. | W-015, W-020, W-030, W-032, W-050 |
| Online Colab is part of the pool | An owner-started Google Colab/KoboldCpp endpoint is a core pool member while its session is online. API providers are the fallback when Colab is offline. Current terms/quota/API behaviour are not yet verified. | W-021 first for terms/API evidence; then W-030/W-031 if allowed |
| Adaptive council by default | One model simulates persona viewpoints for light work; two or three real models deliberate for important decisions; separate OAT agents are reserved for repository/PR execution. | W-050 design; W-051 implementation only after owner selection |
| Simpler Odysseus-centred target | Odysseus is the intended room/council surface to design around—less complex than the multi-agent systems the owner benchmarked mentally—but W-050 must still compare it with alternatives and prove which surface owns what. | W-050, then W-051 |

This direction does **not** close audit A-01. Google and NVIDIA having free
tiers does not prove that every model their APIs list is free-tier eligible,
and neither provider's exact current limits have been freshly recorded here.

## Recommended order

```text
Owner review / choose a slice
  -> P0 safety and correctness (W-010…W-015)
  -> Missing test harness and external contracts (W-016)
  -> Fresh provider research and pending answers (W-020, W-021)
  -> Dynamic scout / shell / dashboard (W-030…W-032)
  -> MCP (W-040)
  -> Quota-aware pool + adaptive-council design, then Odysseus only if chosen (W-050, W-051)
  -> Toolchains (W-060)
  -> Guide, then repackage/release checks (W-070, W-080)
```

W-016 can be split: build the smallest fake needed inside each P0 fix, then
consolidate the full harness in W-016.

---

## Done

- [x] **Baseline inventory and evidence read** — repo/folder state, snapshots,
  both zips inventoried and read.
- [x] **Kit learning + old-chat match** —
  [`reports/KIT_LEARNING_AND_CHAT_MATCH.md`](reports/KIT_LEARNING_AND_CHAT_MATCH.md).
- [x] **One isolated scout self-test baseline** — 62 passed, LiteLLM checks
  skipped; do not rerun outside a named scout task.
- [x] **Odysseus source pointer** — separate repo pinned and read at pointer
  level; no install/run.
- [x] **Extraction, reorganisation, and static code audit (2026-10-17)** —
  canonical kit in `kit/harness/`, extras/snapshots archived, zips and the
  duplicate guide removed, findings in
  [`reports/CODE_AUDIT_2026-10-17.md`](reports/CODE_AUDIT_2026-10-17.md).
- [x] **Owner provider/council clarification recorded (2026-10-18)** —
  quota-aware pool, online Colab membership, Odysseus-centred room intent, and
  adaptive-council default recorded in `PROJECT_CONTEXT.md` and reflected in
  W-015/W-020/W-021/W-030–W-032/W-050. This is documentation only; it does not
  supply fresh provider terms/limits or implement the council.
- [x] **Owner intent extracted from the old chat (2026-10-18)** —
  [`reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md`](reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md):
  the owner's substantive old-chat requests quoted/decomposed and reconciled
  against v1 + this worklist. Hidden attachments (including the very first
  plan) are not recoverable from the share and are recorded as such.
- [x] **Rate-limit/error-protection + provider-discovery strengthening
  (2026-10-18)** — W-015 now requires calming failure behaviour (`Retry-After`,
  bounded counted retries, circuit breaker, token caps, quota ledger, chaos
  tests); W-020 gained the `awesome-freellm-apis` discovery method and a full
  signup-requirements checklist; W-050 must design the runtime policy and a
  worked `429` example. Documentation only.
- [x] **W-020 free-provider research, first pass (2026-10-18)** —
  [`reports/FREE_PROVIDER_RESEARCH_2026-10-18.md`](reports/FREE_PROVIDER_RESEARCH_2026-10-18.md):
  core eight checked on official pages; per-provider eligibility rules and
  guard defaults recorded for W-015; Cerebras excluded, GitHub Models
  removed; remaining list providers triaged as leads under new item W-022.
  No signups, keys, or provider calls.

---

## Owner gate

### [ ] W-001 — Review this reorganisation/PR and name the next slice

**Owner action.** Read [`READING_GUIDE.md`](READING_GUIDE.md) or at least the
README + audit summary + this P0 section. Then either:

- name one `W-` item below; or
- ask for a change to the order/scope; or
- decide what to do with draft PR #3 (it must not be merged by an agent).

**Done when:** the owner names exactly one next task or explicitly parks the
project.

---

## P0 — Fix before trusting a real install

### [ ] W-010 — Secret handling and helper boundary

**Audit:** A-03, A-04, A-24. **Main files:** `kit/harness/harness.sh`,
`kit/harness/model_scout.py`, `kit/harness/harness_ui.py`, guide notes.

- Stop sourcing `keys.env` as shell code; parse it as data with known variable
  names and a conservative value policy.
- Add a regression test showing a value containing shell substitution is not
  executed.
- Replace fixed secret-name stripping with a defined scrub policy for current
  and future provider keys, GitHub/Tavily/test-key variables, and other
  secret-like names the owner approves.
- Recheck state/token/chat file permissions and atomic-write permissions.
- Verify from OAT primary source what shell/filesystem restrictions helpers
  actually have; document the residual same-user risk in beginner words.
- Record the recommended GitHub token scope and branch-rule setup; do not
  change GitHub settings without a separate owner instruction.

**Done when:** key loading has no shell execution path, tests cover a hostile
value and permissions, and the guide no longer implies a stronger isolation
boundary than exists.

### [ ] W-011 — Reproducible, verifiable installer

**Audit:** A-02. **Main files:** `kit/harness/install.sh`, `kit/harness/GUIDE.md`.

- Choose exact LiteLLM and `uv` versions; use upstream release artifacts and
  checksums/signatures where available.
- Pin the OAT installer to a reviewed commit or release artifact; do not fetch
  moving `main` silently. Verify the final `oat version` equals the intended
  version.
- Detect an existing but wrong LiteLLM/OAT version and tell the owner exactly
  what will happen.
- Keep the no-sudo design. Any download-and-run step must be readable,
  versioned, and explained before it runs.
- Add installer tests with stubbed downloaders/commands for fresh, repeat,
  wrong-version, and failure paths. A real fresh install is a separate
  authorised runtime check, not part of merely editing the script.

**Done when:** a reviewer can tell exactly what code/versions the installer
will fetch and the script fails closed on a mismatch.

### [ ] W-012 — Harness lifecycle correctness

**Audit:** A-05, A-06, A-09, A-10. **Main files:** `kit/harness/harness.sh`,
dashboard job layer if the lock is shared there.

- Make HTTP health checks require a successful status and, where practical,
  an expected body/identity.
- Base model freshness on the scout state's `updated` time, not state-file
  modification time.
- Restart the router after a start-time refresh that changes picks.
- Stop masking OAT failures through pipelines. `add-repo` must prove the
  merge queue is disabled before saying so; start/stop must report each part
  truthfully.
- Verify PID identity before killing; narrow or remove the broad process
  fallback.
- Add a shared lock/single-flight rule for mutating harness operations.
- Test with fake `curl`, `oat`, `litellm`, and PID files, including a failing
  merge-queue command and an already-running router with changed picks.

**Done when:** start, stop, scout, and add-repo messages match verified state,
and stale routers are reloaded after model changes.

### [ ] W-013 — Dashboard jobs, onboarding, and PR controls

**Audit:** A-07 (dashboard side), A-15, A-17, A-19, A-26. **Main file:**
`kit/harness/harness_ui.py` (plus shell helpers if shared).

- Allow only one mutating job at a time; show the running job and support a
  safe cancel/stop story.
- Ensure the first dashboard key save also creates/keeps the LiteLLM master
  key, or add an explicit checklist step that does it.
- Add checklist visibility for OAT installed/configured, `connect-oat`, and
  built-in skills. Do not mark `warn`/`blocked` as ready.
- Make dashboard GitHub login run the same Git credential setup as the CLI, or
  explain and link the missing step.
- Share one GitHub URL/repo-name validator between CLI and dashboard,
  including trailing slash/`.git` handling.
- Make PR merge style and branch deletion explicit in the confirmation; offer
  method choice only if the owner wants it.
- Guard stale async pane responses after tab/project switches.

**Done when:** a beginner can follow the dashboard checklist to the same state
as the CLI guide, and double-clicking actions cannot launch competing jobs.

### [ ] W-014 — Safe third-party skill installation

**Audit:** A-08, A-18. **Main file:** `kit/harness/harness_ui.py`.

- Reject symlinks, special files, path escapes, excessive file counts/bytes,
  and clone bombs during preview and install.
- Never dereference a symlink while copying.
- Key preview items by stable folder identity, not only by display name;
  handle duplicate names explicitly.
- Inventory all executable/script-like files, not only a short extension list.
- Show the licence text/name, source URL, and commit when available; write a
  `SOURCE.md` into installed third-party skills or block/warn according to the
  owner's chosen policy.
- Add fixture tests for a symlink to an outside file, a duplicate skill name,
  an oversized tree, a nested skill, and a harmless normal skill.

**Done when:** the dangerous fixtures cannot copy outside content or bypass
limits, and the owner sees provenance before install.

### [ ] W-015 — Scout validation, free eligibility, and config integrity

**Audit:** A-01, A-11, A-12, A-13, A-14, A-22, A-23. **Main file:**
`kit/harness/model_scout.py`.

- Add beginner-friendly schema validation for providers, roles, weights,
  regexes, URLs, numeric ranges, fallbacks, and budgets. CLI and dashboard
  must report the same config state.
- Replace blanket `assume_free` with provider-specific free-evidence rules
  from W-020. Until then, label those services “assumed, not proven” wherever
  picks are shown. The owner confirmed Google/NVIDIA free tiers are intended
  pool sources; that does not make every catalogue entry free-tier eligible.
- Define the pool metadata the adaptive council will later need: endpoint kind
  (provider API or owner-started session), live availability, tool/reasoning
  capability, free-evidence state, recent `429`/failure cooldown, shared task
  budget, and fallback order. Do not invent a council implementation here;
  W-050 owns that design.
- Render W-020's verified limits into per-provider/per-model guard settings
  the router can enforce: requests/tokens per minute and per day, one request
  in flight per provider by default, cooldown length, and which errors are
  retryable. Persist a small quota ledger (attempts, last `429`, cooldown-until)
  so a restart does not immediately re-hammer an exhausted provider.
- Decide and encode policies for unknown context, borrowed roles, provider
  cap relaxation, pins, and previous picks. The report must say when a rule was
  relaxed or a pick is unverified.
- Rewrite the router config when the rendered output hash changes, not only
  when pick names change; make state/report/config updates as consistent as
  practical.
- Block non-loopback HTTP provider URLs by default or require an explicit
  unsafe opt-in.
- Count actual HTTP attempts (including the temperature retry) against probe
  budgets, cap provider response sizes, and clamp future timestamps.
- Make failure handling *calming*, never amplifying (owner requirement,
  2026-10-18):
  - honour a provider's `Retry-After` header when present;
  - retry only `429`, timeouts, and transient `5xx`, with a small fixed cap,
    exponential backoff and jitter — every retry counts against the same
    budget and is shown in the report;
  - never retry `400`/`401`/`402`/`403` (bad request, refused key, payment, or
    policy errors); mark the service state and stop;
  - after repeated failures, open a per-provider circuit breaker: no calls
    until the cooldown expires, then allow exactly one trial call before
    resuming;
  - cap input/output tokens per probe/call so one runaway generation cannot
    drain a day's quota;
  - de-duplicate identical probes within a run and prefer cached results
    inside their TTL;
  - when every pool member is cooling down or exhausted, stop with a plain
    "all free services are resting until <time>" message instead of looping.
- Broaden fake-provider tests for malformed configs and eligibility cases,
  plus chaos cases: `429` with `Retry-After`, a `5xx` storm, a hanging
  endpoint (timeout), a refused key, and an exhausted daily quota. Each test
  must prove the total attempt count stays within budget.
  Rerunning the scout self-test is authorised only as part of this named code
  task; report the exact environment and any LiteLLM skip.

**Done when:** invalid settings fail with a clear message, no model is called
free without the agreed evidence rule, generated router settings cannot
silently go stale, and the chaos tests prove a failing provider can only make
the system slower and quieter — never busier.

---

## Test and contract rebuilding

### [ ] W-016 — Recreate the missing test harness and pin external contracts

**Audit:** A-14, A-20 and the audit's “external contracts” list.

Build small, committed fixtures/tests for:

- shell lifecycle using stub `oat`, `gh`, `curl`, and LiteLLM commands;
- dashboard API routes using fake OAT state, fake worktrees/logs, and stub
  external binaries;
- dashboard page behaviour (DOM-level) for tabs, jobs, keys, skills, and PR
  confirmations;
- OAT state-schema variants, including missing fields and mixed/missing
  `created_at` values;
- generated LiteLLM config in an environment where LiteLLM is actually
  installed, if that task authorises creating such an environment;
- the workspace-helper chat log format, using a captured harmless fixture if
  a real one becomes available.

**Done when:** the old “84 dashboard checks” claim is replaced by a current,
rerunnable result with exact counts/environment, and OAT/LiteLLM assumptions
are either fixture-tested or explicitly listed as runtime-unproven.

---

## Research and pending answers

### [x] W-020 — Verify current free tiers, terms, and provider API shapes — **done 2026-10-18**

**Research only; no code.** Use official docs/pricing/terms, dated and linked,
for:

- delivered and still intended: OpenRouter, NVIDIA, Mistral, and Google AI
  Studio/Gemini (or the provider's current equivalent name);
- candidates: Groq, Cerebras, GitHub Models, Cloudflare, and any custom
  endpoint shape considered for W-030;
- data-use/training/logging, tool calling, rate/request/token limits, account
  or credit thresholds, and whether “listed in catalogue” means free;
- enough per-model eligibility evidence for the quota-aware pool to separate
  “free-tier eligible”, “free only under conditions”, “metered/paid risk”,
  and “unknown”. A provider merely having a free tier is not sufficient.

**Discovery method (owner request, 2026-10-18).** Use the owner's
`freeforall1932-design/awesome-freellm-apis` fork as the *discovery list*:
record its exact commit/date and upstream sync state, mine it for candidate
providers, signup/key URLs, and claimed limits — then treat every claim in it
as a **lead, not evidence**, because its data is synced from a third-party
site, not from the providers. Shortlist by: usable without a credit card,
OpenAI-compatible endpoint, tool calling, limits large enough for paced agent
work, and no obvious region/identity blocker. Providers not verified stay
listed as triaged leads; never present them as checked.

For every verified provider record, in beginner words:

- where to sign up and the exact page where the owner creates the API key;
- signup requirements: email/social login, phone verification, credit card,
  region/age/organisation restrictions, waitlist, or paid-plan prerequisites;
- what "free" concretely means: permanent tier vs trial/renewable credits,
  expiry, what happens when free quota runs out (hard stop vs silent billing);
- limits per relevant model: requests/tokens per minute and day, context and
  max output, concurrency;
- API shape: base URL, auth method, OpenAI-compatibility, tool calling,
  streaming/structured output if officially stated;
- data-use/training/retention and any rule about automated/agentic use;
- whether the limits suggest safe guard settings for W-015 (in-flight cap,
  cooldown, daily budget) — the numbers W-015/W-050 will encode.

**Done when:** W-015 has an evidence table it can encode, and
`RESEARCH_AND_OPEN_QUESTIONS.md` replaces dated snapshot numbers with dated
official findings.

**Completed 2026-10-18:**
[`reports/FREE_PROVIDER_RESEARCH_2026-10-18.md`](reports/FREE_PROVIDER_RESEARCH_2026-10-18.md).
The owner's `awesome-freellm-apis` fork (`fadce14…`, in sync with upstream)
was used as the discovery list; all kept claims were verified on official
provider pages read the same day. Results: OpenRouter and Groq are the
best-evidenced free sources; Google is free per Flash-class model (unpaid
content may train Google's models); NVIDIA is a prototyping trial with
unpublished limits; Mistral Free mode is a monthly allowance (keep
pay-as-you-go off); Cloudflare's 10,000 Neurons/day suits light work;
**Cerebras is excluded** (no permanent free tier) and **GitHub Models is
removed** (retired 2026-07-30). Exact Google/Mistral free limit numbers are
login-only and were not invented. Free tiers are perishable: re-verify
quarterly. Nothing was signed up for, no key was created, and no provider was
called.

### [ ] W-022 — Second-wave free providers from the discovery list (research only)

**Depends on:** nothing; run only if the owner wants a bigger pool after
W-050 shows the core pool is too small.

Take **at most four** leads from the triage table in the W-020 report
(recommended first: Hugging Face Inference Providers, Cohere, ModelScope,
OVHcloud AI Endpoints) and apply the same official-source checklist as W-020:
signup/key URL, card/phone/region/identity requirements, what "free" means
and when it expires or bills, per-model limits, tool calling,
OpenAI-compatibility, data-use/retention, and the W-015 eligibility rule +
guard defaults. Update the W-020 report's format (new dated report) and Q5.

**Done when:** each shortlisted provider is classified
eligible/conditional/paid-risk/unknown from dated official sources, or the
owner decides the core pool is enough and this item is parked.

### [ ] W-021 — Answer the old chat's pending questions

**Old ID:** T2 / restart Step 1 (answers only; no building).

- **AI Horde:** can the router/scout support it today (no in v1), what its
  OpenAI-compatible route really offers, what text-only use would mean, queue
  and privacy/volunteer implications, current terms.
- **OpenMAIC:** read primary README/licence and give a fit/no-fit opinion for
  a persona classroom/room.
- **Colab/KoboldCpp:** fresh official-terms answer for the owner's intended
  online-pool use; do not rely on the snapshot or on roleplay experience alone.
  Include the current free/paid runtime and session limits, whether exposing
  an interactive endpoint to the owner's other tools is allowed, which
  KoboldCpp/OpenAI-compatible API a harness can call, tool-calling capability,
  and what happens when the runtime disconnects. Notebook mechanics are now
  known — the official Colab notebook was dissected on 2026-10-18 in
  `workbench/projects/kobold-cli/COLAB_NOTEBOOK_DISSECTION_2026-10-18.md`
  (includes the keep-alive cell this terms check must judge). Later that day
  the owner explicitly requested a direct test link, so an owner-directed
  test notebook was added at `workbench/projects/kobold-cli/kobold-cli.ipynb`
  with a one-line link in `workbench/projects/kobold-cli/COLAB_LINK.txt`.
  The first custom version then failed in the owner's real Colab run
  (`FileNotFoundError: /content/kobold-cli`) and was replaced the same day
  by an adaptation of the actual official notebook: upstream's
  download/load/launch cell is retained, with coding/API presets/defaults
  changed and the silent-audio keep-alive cell omitted. The replacement
  passed local Jupyter execution with stubbed download/binary commands,
  but a successful real Colab GPU/model/tunnel run is still pending. That
  exception does **not** close this item: terms/limits/runtime evidence
  remains open before the endpoint is relied on. The same session's
  broader stale/bug sweep is
  `workbench/projects/CODEBASE_SWEEP_AUDIT_2026-10-18.md`.
- **Odysseus coverage:** already answered at file level—absent from v1. Any
  recommendation about its Council/personas and the adaptive design belongs
  to W-050.

**Done when:** the owner receives short, sourced, beginner-worded answers and
Q2/Q3/Q14 are updated. No provider is added by this item.

---

## Dynamic roles, services, and dashboard (old T1/T3/T7)

### [ ] W-030 — Rebuild the lost creative-roles/dynamic-endpoint scout patch

**Old ID:** T1. **Depends on:** W-015 design choices; W-020 for real provider
presets; W-021's fresh Colab terms/API answer before any Colab preset is
implemented.

First write a small spec from the archived descriptions and label every guess
(the original patch is lost). Only after owner approval of that spec, implement
in the delivered scout:

- writer/editor or other approved text roles with separate eligibility rules
  for models that cannot call tools;
- `only_roles` or an equivalent role-capability rule;
- endpoint/provider presets and safe `add_endpoint`/`--add-endpoint` handling;
- an owner-started session endpoint kind suitable for Colab/KoboldCpp
  **only if W-021 permits it**: online/offline health, a short-lived/changing
  URL, session expiry, capability limits, free-evidence class, and API
  fallback when offline;
- `--list-services` output the shell/dashboard can consume, including
  availability/cooldown and cost/free-evidence state needed by the adaptive
  council;
- probe tasks appropriate to writing/editing, plus explicit free-evidence and
  shared task-budget rules;
- updated fake answers/fixtures and self-test cases, including the old
  expected break where a no-tools model is no longer globally excluded and an
  offline session endpoint that must fall back rather than hang or spend API
  quota unexpectedly.

**Done when:** the rebuilt behaviour is spec-backed, guesses are marked, and
the updated self-test result is reported exactly (including any LiteLLM skip).

### [ ] W-031 — Make `harness.sh` use dynamic services

**Old ID:** T3. **Depends on:** W-030's service-list contract.

- Replace fixed `SERVICES`, `env_name`, `nice_name`, and `valid_service` data
  with scout-provided service metadata.
- Add `harness add-endpoint` only with the validation/HTTP rules from W-015.
- Make secret stripping, key prompts, status, and doctor dynamic and safe for
  unknown service metadata. Status/doctor must distinguish “configured but
  session offline” from “broken” for an owner-started Colab endpoint.
- Generate the OAT model list in `connect-oat` from enabled roles rather than
  a fixed trio, while keeping tool-incompatible/text-only pool members out of
  OAT tool roles.

**Done when:** adding a valid service/role in scout settings does not require
editing shell lists, and invalid metadata fails safely.

### [ ] W-032 — Make the dashboard dynamic for roles and services

**Old ID:** T7. **Depends on:** W-030/W-031 contracts; W-013/W-016 test base.

- Read role names/labels from scout state/config for Ask, Tasks, and Models.
- Show writer/editor or future roles without hard-coded page lists.
- Build Connections key cards from enabled services and their key-env metadata,
  without exposing secret values. Show pool state in beginner words: free
  evidence, online/offline, cooling down after `429`, capability, and which
  endpoint would be used next/fallback.
- Update API validation to use the dynamic role/service sets.
- Extend the recreated dashboard tests for an added role/service and a removed
  one.

**Done when:** no role/service list in the dashboard needs a code edit for a
valid scout configuration change.

---

## MCP for OAT (old T4)

### [ ] W-040 — Rebuild a reversible, allow-listed OAT MCP patch and UI

**Owner direction:** MCP for OAT is wanted. **Depends on:** W-010/W-016;
dynamic services are not required.

- Start with a design/spec from the archived descriptions; label guesses
  because both original MCP files are lost.
- Recreate a loader that reads an owner-controlled `mcp.json`-style list and
  skips a broken server without taking down the whole agent.
- Recreate an apply/unapply manager with backup, version/schema checks,
  idempotence, status, and a refusal path when OAT internals do not match.
- Add `harness mcp` list/add/remove/apply/unapply/test/status/edit only to the
  extent the owner approves; dashboard presets only, no arbitrary custom
  command from the web page.
- Allow-list tools one by one, read-only first. Keep secrets out of logs and
  out of the repo.
- Test beyond agent construction: a daemon-launched harmless agent/tool call,
  startup delay, broken server, unapply, and an OAT-upgrade mismatch.

**Done when:** MCP can be applied and fully unapplied on the pinned OAT
version, with evidence from a daemon-level test or an explicit statement of
what still needs the owner's machine.

---

## Harness comparison and native room (old T5/T10, restart Step 3)

### [ ] W-050 — Design the quota-aware pool and adaptive council (design only)

**Depends on:** W-021 evidence for Colab claims (W-020 provider evidence is
done — see `reports/FREE_PROVIDER_RESEARCH_2026-10-18.md`, including its
guard-default numbers). It may use clearly labelled assumptions before W-021
only if the owner explicitly accepts an earlier rough draft.

Compare OAT, Odysseus (owner's pinned repo), OpenCode, and Goose from primary
docs/source/licences. Design around the owner's intended split—Odysseus as
the simpler room/council and OAT as the PR execution team—but do not assume
that split wins. Answer:

- who runs the PR team and who, if anyone, is the native persona room for
  writing/daily use;
- how the **adaptive council** works end to end:
  1. one selected model simulates several persona viewpoints and chairs the
     synthesis for light tasks;
  2. exactly two or three real models/providers deliberate for important or
     contested decisions, with explicit agreement/disagreement and one chair;
  3. separate OAT agents are used only for repository/PR execution, normally
     sequentially rather than as many parallel tool loops;
- when the system escalates between those modes, who chooses, and how the
  owner can override it;
- how Google/NVIDIA/OpenRouter/other APIs and an online Colab/KoboldCpp
  session become one pool: free eligibility, capability, health/cooldown,
  shared budget, fallback, and graceful stop when quota is exhausted;
- the runtime "do not combust on error" policy, end to end (owner requirement,
  2026-10-18): where enforcement lives (LiteLLM router settings, scout state,
  Odysseus, or OAT) given each tool's real capabilities; a queue with one
  request in flight per provider by default instead of parallel hammering;
  `Retry-After` handling; bounded retries with backoff/jitter that count
  visibly against the task budget; circuit breaker with a single trial call
  after cooldown; non-retryable error classes (refused key, payment required,
  bad request, content/policy); per-task call/token ceilings and a reserve so
  one task cannot drain the day; no fallback that repeats a tool action with
  side effects; a clear owner-facing stop/pause and a plain status line
  ("resting until 14:32 — daily free limit reached") rather than silent
  spinning;
- orchestrator and specialist sub-agent design (game code, programming,
  front-end/GUI, design, writing/daily use) without letting each persona make
  unbounded hidden calls;
- where MCP belongs and what patch/maintenance cost it creates;
- how the LiteLLM role router is shared without leaking provider keys;
- security exposure, especially shell/filesystem tools, a public/changing
  Colab tunnel, and first-run auth;
- how Qt/CMake/C# toolchains fit.

For Odysseus, re-check the pointer pin against current `main` before reading,
and read that repo's own audit/worklist first. Inspect its actual Council and
provider routing from primary source; do not assume it already implements the
owner's quota-aware adaptive design.

**Done when:** the owner receives a beginner-friendly design—with call-count
examples for a light question, a hard decision, and a PR task, plus one
worked failure example (a provider returning `429` mid-task) showing exactly
what the system does minute by minute—and approves, rejects, or changes it.
This item installs nothing.

### [ ] W-051 — Native Odysseus integration (only if W-050 chooses it)

**Old ID:** T5. **Depends on:** W-050 approval and a refreshed Odysseus pin.

- Add pinned native install/start/stop/status/info/open commands on loopback
  (planned port 7011), with provider keys kept out of Odysseus's environment
  except for the router credential it actually needs.
- Decide how first-run admin creation, ChromaDB/memory, providers, MCP, and
  personas/Council are configured—programmatically only if primary source
  supports it safely.
- Configure the approved adaptive-council modes and pool budget/cooldown
  controls from W-050. If W-021 permits Colab and W-050 includes it, support
  the owner-entered/rotating Colab endpoint as an online pool member with API
  fallback; never pretend it is always-on.
- Add a dashboard link/status without weakening either dashboard's auth.
- Test loopback exposure and auth before any forwarded/public use, including
  what credentials or tunnel exposure a Colab endpoint requires.

**Done when:** the chosen native flow is installed/run in an authorised test
environment, or the exact owner-machine steps and untested parts are reported.

---

## Toolchains, guide, and release

### [ ] W-060 — Write `toolchains.sh` for the admin user

**Old ID:** T6.

- Target the packages from the old plan: Qt6, CMake, Ninja, g++, Xvfb,
  `dotnet-sdk-8.0`, clangd, and Node, adjusted to current Ubuntu packages.
- The helper user must not gain sudo through this script. Make the admin step
  explicit, idempotent, and version-reporting.
- Include tiny smoke checks (compile/test) that do not require Gifscythe
  secrets. The old C# result was blocked only by NuGet reachability.

**Done when:** package/smoke-test behaviour is proven in an authorised Linux
environment or the exact unrun parts are listed for the owner's machine.

### [ ] W-070 — Update the beginner guide

**Old ID:** T8. **Depends on:** whichever of W-010…W-060 the owner actually
completes.

Edit only `kit/harness/GUIDE.md` as the canonical guide. Cover corrected
refresh/free/pinning wording, any new MCP/Odysseus/endpoints/creative roles/
toolchains, real merge behaviour, current terms warnings, and updated
tested/not-tested notes at the bottom. Keep step-by-step beginner wording and
put “what was wrong before” notes at the end.

**Done when:** every command/button in the guide exists in the current code
and every current user-facing feature is documented once.

### [ ] W-080 — Repackage and release-verify v2

**Old ID:** T9. **Depends on:** completed code/guide items.

- Generate a new zip deterministically from `kit/harness/`; record member
  hashes, zip hash, versions, and build date.
- Keep the guide available under the owner's preferred download name.
- Rerun the scout/dashboard/shell suites in their proper environments and a
  fresh-install test only if authorised for that environment.
- Verify no secrets/runtime files are inside the package.

**Done when:** the owner receives downloadable guide + zip and an exact
tested/not-tested release note.

---

## Parked owner choices

### [ ] W-090 — Optional later ideas (do not start without a new owner decision)

- Persona presets in the dashboard (after W-050).
- OpenCode as an extra harness (after W-050).
- Docker packaging (only if explicitly asked; Odysseus direction is native).
- The Agency persona conversion (licence first, Q4).
- SkillOpt, ChatDev, MetaGPT, CrewAI.
- Groq/Cerebras/GitHub Models/Cloudflare beyond any W-020/W-030 approved
  presets.
- Promoting `workbench/projects/ai-team-kit/` into a wider workbench project/tool
  index.

---

## Cross-reference: old IDs

| Old handoff ID | Current worklist home |
|---|---|
| T1 creative-roles scout patch | W-030 (with W-015/W-016 foundations) |
| T2 AI Horde + OpenMAIC answers | W-021 |
| T3 dynamic harness services + add-endpoint | W-031 |
| T4 MCP commands/dashboard | W-040 |
| T5 Odysseus native commands/link | W-051, gated by W-050 |
| T6 toolchains | W-060 |
| T7 dashboard dynamic roles/services/tests | W-032 + W-016 |
| T8 guide add-ons | W-070 |
| T9 repackage + full tests | W-080 + W-016 |
| T10 persona/OpenCode/Docker choices | W-050 + W-090 |

| Restart Step | Current worklist home |
|---|---|
| Step 0 baseline | Done |
| Step 1 quick answers | W-021 |
| Step 2 model sources | W-020, W-030, W-031 |
| Step 3 harness comparison/design | W-050 |
| Step 4 rebuild lost files | W-016, W-030, W-040 |
| Step 5 build v2 in slices | W-031, W-032, W-040, W-051, W-060 |
