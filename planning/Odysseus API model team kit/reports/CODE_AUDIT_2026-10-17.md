# AI Team Kit v1 — code audit (2026-10-17)

## Short verdict

The delivered v1 is a coherent, readable first version: the installer,
`harness` command, model picker, dashboard, skills, and launchers mostly line up
with each other, and this audit found **no empty placeholder function pretending
to be a finished feature**.

It is **not yet runtime-proven in this session**, and a small set of issues
should be fixed before trusting it with real keys, a real GitHub token, or
untrusted skills. The most important themes are:

1. “Free only” is assumed for three of the four model services, not proven.
2. Installer downloads are not pinned and hashed as strongly as the guide
   implies.
3. The agent/secret boundary is mostly instructions and environment cleanup,
   not an operating-system security boundary.
4. A few shell paths can say “started”, “stopped”, or “auto-merge is off” even
   when the underlying OAT command failed.
5. Model/router refresh can stay stale in two ordinary flows.
6. Dashboard jobs can run at the same time and race over the same files and
   processes.
7. Skill installation can copy through symbolic links even though the preview
   tries to make installation safer.

The planned v2 features are mostly **absent**, not half-wired: writer/editor
roles, dynamic services/endpoints, MCP for OAT, Odysseus integration, extra
providers, persona room, Docker, and the toolchain installer are not in the
extracted v1 tree.

> This audit did not fix kit code. Every fix below is a recommendation and is
> mapped to an item in [`workbench/projects/ai-team-kit/WORKLIST.md`](../WORKLIST.md).
>
> **Owner clarification added 2026-10-18.** Finding A-01 does not mean Google
> or NVIDIA lacks a free tier. The owner intends both—as well as OpenRouter,
> other suitable providers, the delivered Mistral source, and an online
> Colab/KoboldCpp session—to form a quota-aware model pool. A-01 remains open
> because the delivered code cannot yet prove which individual catalogue
> models are free-tier eligible, track remaining quota/cooldown, represent a
> Colab session endpoint, or allocate calls across an adaptive council. The
> clarification is recorded in [`workbench/projects/ai-team-kit/PROJECT_CONTEXT.md`](../PROJECT_CONTEXT.md)
> and `workbench/projects/ai-team-kit/RESEARCH_AND_OPEN_QUESTIONS.md`; current official limits/terms are
> still W-020/W-021 work.

---

## 1. Scope and method

### Code reviewed

The canonical extracted v1 now lives in `workbench/projects/ai-team-kit/kit/harness/`:

| File | Lines | SHA-256 of the extracted v1 file |
|---|---:|---|
| `model_scout.py` | 1,611 | `263c9ac8dbdcc19b891a9197b7cb82ec99f4ff35b004923fefb2d222491b5e08` |
| `harness_ui.py` | 1,273 | `c59bce59561f3f792fd8cc11f8bd7e9e89a903c0aebe32d73d154fcd84cacb88` |
| `harness.sh` | 665 | `0d86e563a006693da1606908535de6c36dbf14a6a820439641970fbcc5e49399` |
| `install.sh` | 128 | `8e9038adb7bb9b5387c45df6ee1c7b5542bb903bed32a7047c9ff4570e00cb39` |
| `GUIDE.md` | 911 | `f2d64d7fbca319f9259eadb3e34b776b226291597e72c89ef34bd682c4077ce7` |

Also reviewed: `README.txt`, the Mac and Windows launchers, the two built-in
skills, and the four team-workflow templates.

### Checks performed for this audit

- Read the code and cross-checked names and contracts between files:
  shell commands named in the guide, shell dispatch, dashboard job actions,
  browser `api()` paths, Python route tables, scout flags, and the dashboard's
  uses of `model_scout` functions.
- Parsed both Python files as an abstract syntax tree (AST). Both parse.
- Ran `bash -n` over `harness.sh` and `install.sh`. Both parse.
- Extracted the dashboard's inline JavaScript to scratch and ran Node's syntax
  check. It parses.
- Ran a small static name-use scan. It did not find an obviously unused
  top-level Python function/class. This is only a weak static signal, not a
  coverage result.
- Searched for `TODO`, `FIXME`, `NotImplemented`, and similar markers. No real
  stub was found; the `pass` statements are normal empty exception/log handlers.

### Evidence labels used below

- **Confirmed in code** — follows directly from the delivered source.
- **Conditional** — needs a stated situation (bad config, concurrent click,
  stale PID, untrusted skill repo, and so on).
- **External/unverified** — depends on OAT, LiteLLM, a provider, GitHub, or an
  operating system behaving a certain way. This audit does not call it broken.

### What was not run

The earlier owner-named learning task ran the delivered
`model_scout.py --selftest` exactly once: Python 3.11.2, exit 0, 62 passed,
0 failed, LiteLLM Router checks skipped. That evidence is preserved in
[`KIT_LEARNING_AND_CHAT_MATCH.md`](KIT_LEARNING_AND_CHAT_MATCH.md). It was
**not rerun for this audit**.

This audit did not run the installer, LiteLLM, OAT, the dashboard server,
GitHub login/PR actions, a model provider, Windows/WSL, macOS, or Codespaces.

---

## 2. Fix before trusting a real install (P0)

### A-01 — “Free only” is not actually established for NVIDIA, Mistral, or Google

**Status:** confirmed in code. **Worklist:** W-015, W-020.

- OpenRouter candidates are treated as free only when both prompt and
  completion prices are zero (`model_scout.py:302-306`).
- NVIDIA, Mistral, and Google have `"assume_free": True`
  (`model_scout.py:72-81`). For their OpenAI-style catalogs, every listed model
  is created with `free=True` when `assume_free` is set
  (`model_scout.py:313-318`). Google is only name-filtered to IDs containing
  `flash`.
- `static_reason()` then accepts `free is True` (`model_scout.py:360-361`). A
  paid, quota-gated, account-dependent, or no-longer-free model can therefore
  be ranked solely because it appears in the catalog.
- Two deliberate escape hatches also bypass fresh proof:
  - user pins are inserted even if they are not in the current catalog and
    have no fresh probe result (`model_scout.py:558-565`);
  - if no model can currently be selected, previous picks are kept and their
    roles are labelled `ok`, with only a note saying they could not be verified
    (`model_scout.py:1017-1025`).

**Why it matters:** free-only is a core owner requirement. The code proves it
for OpenRouter price data, but only assumes it for the other three services.

**Suggested direction:** check current official provider terms/catalogue fields
in a named research task; encode an explicit per-provider free-evidence rule;
make pins and previous picks visibly “unverified” rather than silently normal.

### A-02 — Installer trust and versions are weaker than “the version is fixed”

**Status:** confirmed in code. **Worklist:** W-011.

- `uv` is installed with the current remote script piped to `sh`
  (`install.sh:60-65`).
- LiteLLM is installed as unpinned `litellm[proxy]` (`install.sh:82-87`). If
  any executable already exists, the installer accepts it without a version or
  compatibility check.
- OAT's installer is downloaded from the moving `main` branch
  (`install.sh:9-10,95-100`). `OAT_VERSION=v0.1.0` is passed to it, but the
  script itself is not pinned to a commit or hash, and after installation the
  code only checks that *an* `oat` command exists—not that the requested
  version is now installed.
- The guide says “the installer now downloads it, and the version is fixed”
  (`GUIDE.md:837`), which overstates what is pinned.

**Why it matters:** a future upstream change can change behaviour or break the
dashboard's assumptions about OAT, and the old chat's own rule was not to run
unread internet installers casually.

**Suggested direction:** pin exact versions, prefer release artifacts or a
commit-pinned installer, verify checksums/signatures where upstream provides
them, and assert the installed `oat` and LiteLLM versions after install.

### A-03 — Helpers and kit secrets share one OS account; env cleanup is not isolation

**Status:** confirmed design risk; OAT's own internal restrictions were not
tested here. **Worklist:** W-010, W-016.

- `start_oat()` removes four provider keys and the router master key from the
  environment given to `oat start` (`harness.sh:145-154`). That is useful, but
  the helpers still run as the same OS user who owns
  `~/.config/gifscythe-harness/keys.env`, `~/.oat/config.toml`, `~/.oat/.env`,
  GitHub CLI credentials, worktrees, and logs.
- `connect-oat` writes the router master key into OAT's config and `.env`
  (`harness.sh:335-377`). OAT needs a router credential, but that means the
  boundary depends on OAT's tool restrictions and helper behaviour, not on the
  kit creating separate identities or a sandbox.
- The dashboard's `clean_env()` removes only five known secret names from child
  processes (`harness_ui.py:51,66-71`). It does not remove names such as
  `GH_TOKEN`, `GITHUB_TOKEN`, `TAVILY_API_KEY`, `SCOUT_NEW_KEY`, or a future
  custom provider key.
- The built-in skills tell helpers not to read key files or merge PRs. Those
  are instructions, not enforcement.

**Why it matters:** “the owner reviews and merges” and “keys are not available
to helpers” should not be treated as operating-system guarantees from this kit
alone. A separate Linux user protects the owner's personal files, but the kit's
own secrets still live in that helper user's home.

**Suggested direction:** verify OAT's shell/filesystem/tool restrictions from
primary source and with a harmless contract test; keep the GitHub token
repo-scoped and least-privilege; consider branch rules that require owner
review; strip secret-like environment variables dynamically rather than from a
fixed list.

### A-04 — The keys file is loaded by executing it as shell code

**Status:** confirmed in code. **Worklist:** W-010.

`with_keys()` copies `keys.env` to a temporary file and sources it with
`. "$t"` (`harness.sh:38-47`). Router startup repeats the same pattern
(`harness.sh:115-119`). The Python writer writes raw `KEY=value` lines
(`model_scout.py:720-728`), while key normalisation removes whitespace and
quotes but not shell substitutions or separators
(`model_scout.py:695-696`).

A value containing shell syntax—accidental or malicious—can therefore run as
shell code when the scout or router starts. The dashboard is already a
same-user control surface, so this is not by itself a privilege-escalation
claim; it is still the wrong boundary for a data file.

**Suggested direction:** parse the file as data (Python or a strict shell
parser), accept only known variable names and a conservative key character
set, and never source it.

### A-05 — “Auto-merge is off”, “started”, and “stopped” can be reported after failure

**Status:** confirmed in code. **Worklist:** W-012.

Several important shell commands are piped through `tail`, and the script does
not enable `pipefail` or check those commands separately:

- `oat start` (`harness.sh:145-154`);
- `oat config "$name" --mq-enabled=false` and `oat repo use`
  (`harness.sh:428-437`), after which the script says auto-merge is off and the
  project is default;
- `oat stop-all` in both stop paths (`harness.sh:461-472`).

In a pipeline, the visible exit status is normally the last command (`tail`),
so an OAT failure can be masked. `cmd_start()` can still finish with “All
started” (`harness.sh:439-459`).

**Why it matters:** owner-only merging is a core safety promise. The code
intends to disable OAT's merge queue, but the success message is not proof that
the setting was applied.

**Suggested direction:** capture output and exit status separately (or use
`set -o pipefail` carefully), verify the merge-queue setting by reading it
back where OAT supports that, and make start/stop messages reflect each part.

### A-06 — Refresh can look successful while the old router/model list remains in use

**Status:** confirmed in code. **Worklist:** W-012.

Two ordinary flows combine badly:

1. `scout_is_old()` uses the **modification time** of `scout_state.json`
   (`harness.sh:65-67`). But `--check`, setting a key, and removing a key also
   rewrite that state file. Merely checking keys can make an old model list
   look fresh for another 12 hours.
2. `cmd_scout()` restarts a running router when picks change
   (`harness.sh:320-332`), but `cmd_start()` does not. It runs the scout, then
   `start_router()` sees a router already responding and returns without
   reloading the new config (`harness.sh:107-112,439-457`). The dashboard's
   Start button uses `harness start`, so it inherits this behaviour.

**Suggested direction:** read the scout state's own `updated` timestamp for
model freshness, and restart the router whenever a start-time refresh returns
“changed” (exit 10).

### A-07 — No single-flight lock for jobs that mutate the same state

**Status:** confirmed in code. **Worklist:** W-012, W-013.

The dashboard's `start_job()` always launches another harness process and
thread (`harness_ui.py:218-242`). Neither the dashboard nor `harness.sh` takes
a lock around start, stop, scout, check, doctor, add-repo, PID files, logs,
state, or router config. Two clicks—or a dashboard job plus a terminal
command—can race.

Atomic file replacement reduces torn writes, but it does not prevent lost
updates or one process stopping what another is starting.

**Suggested direction:** one mutating job at a time, an on-disk lock shared by
CLI and dashboard, visible “already running” state, and a cancellation path
for dashboard jobs.

### A-08 — Skill installation can copy through symlinks and bypass its size check

**Status:** confirmed in code; exploitation needs an untrusted/malicious skill
repo. **Worklist:** W-014.

- Preview size sums only non-symlink files (`harness_ui.py:783-787`).
- Install uses `shutil.copytree(..., symlinks=False)`
  (`harness_ui.py:810-821`), which dereferences symlinks and copies their
  targets. The later loop that unlinks symlinks cannot undo that, because the
  copies are already regular files.
- A symlink to a large or sensitive local file can therefore bypass the size
  calculation and place target content inside the installed skill.
- “Has scripts” detection checks only a small extension list. Extensionless
  executables, binaries, and other script types are not flagged.

**Suggested direction:** walk the preview tree without following symlinks;
reject symlinks, FIFOs, devices, and other special files; enforce file-count
and byte limits during the walk; copy only an explicit allow-list of regular
files; show all executable-looking files.

---

## 3. Likely user-facing failures and logic gaps (P1)

### A-09 — Shell health checks count any HTTP answer as “up”

**Confirmed in code; W-012.** `router_up()` and `ui_up()` use `curl -s`
without `--fail` (`harness.sh:62-63`). Curl returns success for an HTTP 404 or
500 response. Another program on the port, or a starting service returning an
error page, can be mistaken for the router/dashboard. The dashboard's own
`http_ok()` correctly checks the status range (`harness_ui.py:111-116`).

### A-10 — Stale PID files are trusted without checking process identity

**Conditional; W-012.** `stop_router()` and `stop_ui()` kill whatever PID is in
the PID file without verifying that it is still LiteLLM/Python for this kit
(`harness.sh:129-142,181-187`). The router also falls back to a broad `pgrep`
pattern. PID reuse could stop an unrelated same-user process. Verify command
line and start time, or supervise a process group.

### A-11 — Router config can remain stale even when scout settings change

**Confirmed in code; W-015.** `changed` is true only when selected model keys
change or the output file is missing (`model_scout.py:1033-1036`). If the user
changes a provider base URL, LiteLLM prefix, fallback, timeout, retries, or
cooldown while picks stay the same, the rendered config is not rewritten. The
run also writes state and report before the router config
(`model_scout.py:1071-1082`), so a failure in between can leave them
inconsistent. Compare a hash of the rendered output instead.

### A-12 — Configuration validation is too narrow for the planned dynamic features

**Confirmed in code; W-015.** `validate()` checks pins, but not provider field
types/presence, role weights, regex validity, numeric ranges, fallback role
names, URL shape, or probe budgets (`model_scout.py:653-663`). The rest of the
program indexes config fields directly. A hand-edited `scout.yaml` can produce
a traceback or a misleading “offline” result rather than a beginner-friendly
settings error.

Related: the dashboard's `scout_cfg()` silently falls back to defaults if the
config cannot be loaded (`harness_ui.py:184-188`), while the CLI scout reports
an error. The dashboard and CLI can therefore disagree about services/keys.

### A-13 — Role eligibility has several soft edges

**Confirmed design choices; W-015.**

- A model with unknown context (`ctx=0`) passes `min_context`, because the
  check is skipped when context is falsy (`model_scout.py:510-518`). An
  architect/reviewer pick can therefore be smaller than the stated minimum.
- `enrich()` borrows context/date/popularity from another provider's model
  with the same normalised base name (`model_scout.py:322-348`). Name
  collisions can borrow the wrong metadata.
- Borrowed role picks are copied from other roles without rechecking the
  borrowing role's minimum context (`model_scout.py:573-589`).
- `max_per_provider` is a preference, not a hard cap: `pick()` backfills from
  skipped same-provider rows to reach `top_n` (`model_scout.py:537-551`).
- Independent-reviewer handling only swaps within the already-selected top N;
  it does not consider the next ranked different model.

These may be acceptable resilience choices, but the guide/report should call
them preferences and show when a requirement was relaxed.

### A-14 — The probe proves a narrow tool-call shape, not general agent compatibility

**Confirmed test-scope gap; W-015, W-016.** A candidate must make one correct
`get_weather` call, then answer two trace, two bug-line, and one JSON-format
question (`model_scout.py:447-506`). It does not test tool-result
continuation, parallel calls, larger schemas, streaming, long contexts, or
multi-turn agent behaviour through LiteLLM/OAT. Also, the low-level chat code
may retry once after removing `temperature` (`model_scout.py:210-231`), while
the probe budget counts logical calls (`model_scout.py:949-978`). Actual HTTP
attempts can exceed the displayed budget.

### A-15 — Dashboard onboarding does not yet cover every CLI setup step

**Confirmed in code; W-013.**

- Saving a provider key in the dashboard does not create the LiteLLM master
  key. The CLI setup flow does (`harness.sh:275-289`); the dashboard calls
  `ms.set_key()` only (`harness_ui.py:376-385`). A later Start can fail with
  “router password is empty”.
- The setup checklist does not include `connect-oat`, built-in skill
  installation, or whether OAT is installed/configured
  (`harness_ui.py:280-296`).
- Dashboard GitHub login does not run `gh auth setup-git`, unlike the CLI flow
  (`harness_ui.py:399-407`; `harness.sh:379-401`). `gh` itself can work while
  plain Git operations used by other tools lack the credential helper.
- Checklist “keys OK” accepts `warn` (catalogue loaded but no usable free
  model), `blocked` (account setting blocks models), and `limit` as ready.
  “Models OK” accepts any pick for any role.

### A-16 — Roles and services are hard-coded in several places

**Confirmed missing v2 wiring; W-030, W-031, W-032.**

Even if `scout.yaml` gained roles or providers, these parts would not follow:

- shell `SERVICES`, `env_name()`, `nice_name()`, `valid_service()`
  (`harness.sh:24,51-60`);
- `connect-oat`'s fixed model list (`harness.sh:347-356`);
- fixed secret-stripping lists in shell and dashboard;
- dashboard `ROLES` (`harness_ui.py:52`) and hard-coded role options/labels in
  the page (`harness_ui.py:1088,1097,1151-1155`).

This exactly matches the unfinished T1/T3/T7 work from the old chat. It is not
a v1 regression, but dynamic roles/services cannot be added by changing the
scout alone.

### A-17 — Dashboard merge always squashes and deletes the branch, without saying so

**Confirmed in code; W-013.** The API defaults to `squash` and always passes
`--delete-branch` (`harness_ui.py:678-683`). The page sends no method and its
confirmation does not mention squash or branch deletion
(`harness_ui.py:1222`). The API supports merge/rebase, but the UI does not
expose them. The owner still confirms the merge; the surprise is the merge
style and cleanup.

### A-18 — Skill preview can install a different folder when names collide

**Confirmed in code; W-014.** Preview stores installable items in a dict keyed
only by skill name (`harness_ui.py:790-792`). If two folders declare the same
front-matter name, both are displayed but only the last one remains in the
install map. Licence handling detects only a root filename and does not check
compatibility or copy the licence into the installed skill. This is weaker
than the self-extend skill's own instruction to record source, commit, and
licence.

### A-19 — Repository naming is inconsistent between CLI and dashboard

**Confirmed in code; W-013.**

- The dashboard validates GitHub URLs strictly (`harness_ui.py:55,501-507`).
  The shell accepts any `https://github.com/*/*` prefix and takes the last
  path segment as the project name (`harness.sh:419-437`). A trailing slash
  makes the name empty; an extra path segment makes it wrong.
- `status`, `doctor`, and `github-login` default to
  `freeforall1932-design/gifscythe` (`harness.sh:13-14`), while `add-repo` and
  the dashboard are multi-project. That is correct if Gifscythe is the only
  intended target, but misleading for a generic kit or a second project.

### A-20 — The dashboard is tightly coupled to OAT's private state shape

**External/unverified; W-016.** The dashboard reads `~/.oat/state.json` fields
such as `repos`, `current_repo`, `agents`, `worktree_path`, `task_history`,
`pr_number`, and `total_tokens` directly (`harness_ui.py:140-150,305-345`). It
also assumes log paths under `~/.oat/output/...` (`harness_ui.py:267-276`).
An OAT schema change can return empty data or a 500—for example, sorting agents
assumes every `created_at` value is mutually comparable. The old chat reported
source-level checks against OAT v0.1.0, but no delivered contract test or fake
OAT state fixture exists in v1.

---

## 4. Robustness and documentation issues (P2)

### A-21 — Changes view can compare against a surprising base

The merge-base helper tries the configured target, then silently falls back to
other common branches if that fails (`harness_ui.py:579-584`). It never
fetches, so `origin/<branch>` can be stale. Porcelain parsing is also limited
for quoted/renamed paths. The view is useful, but it should name the ref it
actually used and warn when it falls back.

### A-22 — A non-loopback HTTP provider URL is warned about but still used

`insecure_urls()` produces notes, and the run continues to send the key over
plain HTTP (`model_scout.py:666-674,861-909`). For a future “add endpoint”
feature this should be blocked by default or require an explicit unsafe
confirmation.

### A-23 — Provider responses and timestamps are trusted more than necessary

- Catalog/chat bodies are read fully into memory without a byte limit
  (`model_scout.py:205-244`).
- `recency()` does not clamp future timestamps, so a millisecond or future
  `created` value can score above 1.0 (`model_scout.py:386-389`).
- Provider context/date/popularity enrichment is heuristic, as noted in A-13.

These are robustness issues, not evidence that the four built-in providers
currently send such data.

### A-24 — Small state and file-integrity gaps

- `atomic_write()` uses a deterministic per-process temporary name and relies
  on creation mode; a pre-existing temp file is truncated without re-chmoding
  (`model_scout.py:624-631`). Normal operation uses fresh names, but the key
  writer deserves a stricter implementation.
- Dead/probe state stores a truncated unsalted SHA-256 fingerprint of refused
  API keys (`model_scout.py:282-283,740-746`). High-entropy keys make this a
  low practical risk, but it is still a verifier for a guessed key.
- `scout_plain()` is commented as running “without your keys”, but it does not
  actually clear inherited provider-key variables (`harness.sh:76-82`). Its
  current modes mostly do not need ambient keys; the comment is stronger than
  the implementation.
- `doctor`'s embedded state check can print a Python traceback on corrupt
  JSON and does not increment its problem count (`harness.sh:616-628`).

### A-25 — Guide wording is ahead of the mechanism in a few places

- There is no scheduler. “Checks every day” means: refresh on `start`/`open`
  if the state looks older than 12 hours, or when the owner runs `scout`, as
  the later daily-routine section more accurately says.
- `README.txt` says the picker picks models “every day”; the mechanism is
  start-triggered.
- “Free only”, “version is fixed”, and the merge behaviour need the caveats in
  A-01, A-02, and A-17.
- The guide portrays keys as kept away from helpers; A-03 explains the limit of
  that statement.

### A-26 — Minor UI races and edge cases

- `renderRight()` does not discard an older async response after the user
  switches tab/project, so a slow response can overwrite a newer pane.
- Job history pruning can remove a still-running older job once more than 12
  jobs exist, after which its watcher gets “unknown job”.
- User task/chat text beginning with `-` is passed positionally to OAT without
  a `--` separator (`harness_ui.py:421,466`). Whether that misparses depends
  on OAT's CLI parser.
- The Mac/Windows launchers are simple and plausible, but untested here; the
  Windows batch builds WSL arguments without quoting a distro/user containing
  spaces.

---

## 5. What is implemented, partial, or absent

### Implemented in delivered v1 (code present)

- No-sudo-oriented installer for `uv`, LiteLLM, OAT, the `harness` symlink,
  skills, and optional Windows shortcuts.
- Key setup/test/save/remove flows, with backup and masked display.
- Four provider definitions: OpenRouter, NVIDIA, Mistral, Google.
- Paced probing, ranking, state/report generation, and LiteLLM config writing.
- Router/OAT/dashboard start-stop-status-log commands.
- OAT connection file generation and `add-repo` with merge queue intended off.
- Local dashboard: Chat, Tasks, Ask, Files, Changes, PRs, Models,
  Connections, Skills, Logs.
- Built-in `team-workflow` and `self-extend` skills plus templates.
- Windows and Mac launchers.

### Partially implemented

- Dashboard-first onboarding (missing master-key creation, `connect-oat`, and
  some Git setup; see A-15).
- Dynamic scout configuration (the data model is flexible, validation and the
  shell/UI are not; see A-12 and A-16).
- Safe third-party skill installation (preview exists; symlink/licence/name
  handling is incomplete; see A-08 and A-18).
- PR merge controls (merge exists; method choice and branch-deletion
  disclosure do not; see A-17).
- “Free model” classification (real price evidence only for OpenRouter; see
  A-01).

### Not implemented in either delivered zip

Confirmed by inventory and code search in the learning report:

- writer/editor or other creative roles;
- `--list-services`, `--add-endpoint`, endpoint presets, `harness add-endpoint`;
- Groq, Cerebras, GitHub Models, Cloudflare, AI Horde, or Colab support;
- MCP loader/apply files, `harness mcp ...`, dashboard MCP management;
- Odysseus commands, dashboard link, persona room, or Council integration;
- OpenCode/Goose harness integration or a harness-comparison result;
- `toolchains.sh` for Qt/CMake/C# and related tools;
- Docker packaging;
- dashboard/MCP test harnesses (`run_tests.py`, DOM tests, fake OAT/GitHub
  binaries) that the old chat reported using in its sandbox;
- the patched `model_scout.py` described by the handoff snapshot.

### External contracts that still need proof at the right task

- OAT v0.1.0 CLI syntax, daemon lifecycle, state schema, workspace-agent log
  format, model onboarding, merge-queue settings, and tool sandboxing.
- LiteLLM proxy startup with the generated YAML/JSON, `order` behaviour under
  `simple-shuffle`, fallbacks/cooldowns, and the `x-litellm-model-id` header
  used to label Ask answers.
- Real provider catalogues, model IDs, tool calling, rate limits, free-tier
  terms, data-use policies, and error shapes.
- Real GitHub fine-grained token flow, `oat init` clone/push/PR creation, and
  dashboard Merge/Close against a real repository.
- Windows/WSL window-close behaviour, macOS launchers, and Codespaces
  forwarding/allowance.

---

## 6. What aligns well

These parts were checked and should not be rewritten casually:

- Every `harness ...` command named in the guide exists in shell dispatch.
- Dashboard job actions map to existing harness commands: start, stop-team,
  scout, check, doctor, install-skills, add-repo.
- Browser API paths align with the Python GET/POST route tables.
- The dashboard imports and reuses the scout's key/config/state functions
  instead of duplicating their formats.
- The scout uses same-host redirects, atomic writes, paced budgets, probe TTLs,
  separate one-key fallback dictionaries, and explicit service states.
- Key display is masked; key/state files are intended to be owner-only; old
  keys are kept when a replacement is refused.
- The dashboard binds to loopback, uses a per-install token with constant-time
  comparison, host checks, a CSRF header/content-type check, a restrictive
  content-security policy, output escaping in the page, and path containment
  for project file reads.
- Chat/Tasks/PR actions call external programs with argument lists rather than
  shell strings. The only `shell=True` in the scout is the explicitly
  user-supplied `--on-change` command, which `harness.sh` does not use.

---

## 7. Recommended order

Do not start these automatically; the owner names one task at a time.

1. **Safety/correctness first:** W-010 to W-015, with tests that can fail.
2. **Rebuild the missing test harness:** W-016, especially fake OAT state/CLI,
   shell lifecycle tests, dashboard API/DOM tests, and a LiteLLM config test
   in an environment where LiteLLM is actually installed.
3. **Fresh provider research:** W-020/W-021 before adding or trusting sources.
4. **Only then rebuild v2 slices:** dynamic scout/services/dashboard
   (W-030 to W-032), MCP (W-040), harness/room design (W-050/W-051), and
   toolchains (W-060).
5. **Guide and repackage last:** W-070/W-080, after the code they describe
   exists and has evidence.

---

## 8. Tested / not tested for this audit

**Tested or checked here:** source reading; cross-file command/route/flag
alignment; Python AST parse; `bash -n`; inline-JavaScript syntax check; zip
extraction hashes recorded in the file map.

**Not tested here:** installer execution; LiteLLM/OAT/dashboard runtime; real
models or keys; GitHub; Windows/macOS/Codespaces; Odysseus; MCP; any audit fix
(no kit code was changed).
