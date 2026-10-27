# AI Team Kit — what the delivered zip does, and how the old chat matches it

Snapshot: **2026-10-17** (Asia/Jakarta)

> **Reorganisation note (later on 2026-10-17):** this report's findings were
> used to extract the canonical kit to `workbench/projects/ai-team-kit/kit/harness/`, the four
> `harness.zip`-only documents to `workbench/projects/ai-team-kit/archive/harness-zip-extras/`, and the
> four snapshot files to `workbench/projects/ai-team-kit/archive/2026-10-16-handoff-snapshot/`. Both zip
> files and the duplicate top-level guide were then deleted. References below
> to the zips or former top-level paths describe the state **when this report
> was written**. Current navigation is in `workbench/projects/ai-team-kit/README.md` and
> `workbench/projects/ai-team-kit/FILE_MAP.md`.

## Short answer

`ai-team-kit.zip` is the delivered **v1 coding-team kit**. It does not contain
the OAT program or the LiteLLM router as finished binaries. Instead, it
contains the glue that installs and operates them:

1. an installer;
2. one `harness` command;
3. `model_scout.py`, which finds apparently free models, quick-tests them,
   ranks them for three coding roles, and writes the router's model list;
4. a local browser dashboard for chat, tasks, files, changes, pull requests,
   models, keys, skills, and logs;
5. two skills that teach helpers to use project handoff/worklist files and to
   research missing abilities cautiously; and
6. Windows/Mac double-click launchers and the beginner guide.

The intended end-to-end flow is the one in the guide
(`harness/GUIDE.md:21-39`):

```text
Owner <-> Dashboard <-> OAT helpers -> LiteLLM router -> free AI services
                                      ^
                        model_scout.py keeps the model list fresh
```

The helpers are supposed to work in their own copies of a GitHub project and
open pull requests. The owner remains the person who merges. In this
repository the kit is stored as a project artifact under
`workbench/projects/ai-team-kit/`; it is **not integrated into the Dionysus dotfiles**
and it does not change `assets/` or `dotfiles/`.

The old shared chat broadly matches the delivered v1 kit. The most important
correction is about the picker check count: the delivered code can print 68
logical checks when LiteLLM is installed in the Python running it, but the
one isolated run in this session printed **62 `ok` lines and skipped the six
LiteLLM Router checks because LiteLLM is not installed in this sandbox's
Python**. It exited `0` and printed `selftest passed`.

The later v2 work discussed near the end of the old chat is **not inside the
delivered zip**: no writer/editor roles, no dynamic endpoint presets, no MCP
loader/apply patch, no Odysseus commands, no AI Horde/Groq/Cerebras presets,
no persona room, and no Qt/CMake/C# toolchain installer.

---

## 1. Scope, safety, and evidence rules

### What was done for this report

- Re-synced this repository on `arena/5bf33a0c-dionysus`; local, remote, and
  draft PR #3 head were `9f7caea54176a31770fc63c38db0c47092162ddb` before
  this report was written.
- Extracted both uploaded zips **only into scratch space**:
  `/tmp/ai-team-kit-learn-20261017/kit/` and
  `/tmp/ai-team-kit-learn-20261017/harness/`.
- The extractor rejected absolute paths, `..` traversal, and symlinks. It
  preserved executable bits and wrote a scratch manifest with byte sizes,
  SHA-256 hashes, and CRC32 values.
- Read the delivered guide, installer, shell command, dashboard, model
  picker, both skills, templates, and launchers.
- Read and classified the four documents that exist only in `harness.zip`.
- Re-read all four visible chunks of the old shared chat:
  https://claude.ai/share/4b76ad92-cfd8-443a-b686-9fa20f1c23aa
- Performed static syntax checks: Python AST parsing for the two Python
  files and `bash -n` for the two shell scripts.
- Ran the delivered model-picker self-test **exactly once**, after reading
  its code, with `HOME` and `TMPDIR` isolated under scratch. Details and the
  full output are in Section 7 and Appendix B.

### What was not done

- The canonical zips were not modified.
- `install.sh` was not run.
- `harness start`, `harness open`, OAT, LiteLLM, and the dashboard server
  were not started.
- No real AI-provider API, GitHub login, repository clone, pull request,
  merge, or close operation was performed through the kit.
- No current provider free-tier limits or terms were re-researched in this
  learning task. Numbers quoted by the guide/old chat remain dated claims.
- Odysseus was not re-inspected for this report; `ODYSSEUS_SOURCE.md`
  remains the separate source pointer.

### Old-chat visibility limit

The shared chat exposes conversation text and collapsed tool summaries, but
attachments are hidden and many tool results were cleared. Therefore this
report uses the following labels:

- **Verified in delivered files** — the code/text is present in the uploaded
  zip and was read here.
- **Verified by this session's run** — only the model-picker self-test and
  the static syntax checks.
- **Code present, runtime not reproduced** — the mechanism exists, but this
  session did not start the full system.
- **Old-chat report only** — the old chat said it happened in its sandbox;
  the delivered files do not let this session reproduce it.
- **Missing from delivered zip** — searched for and not found.

The expired/hidden old-chat attachments were not needed to identify the
delivered v1 kit because the owner later uploaded the zip itself. Anything
that existed only as an old sandbox file remains unverifiable from the
shared chat.

---

## 2. The two zips: canonical kit and extra superset

| Archive | Bytes | SHA-256 | Entries | Status |
|---|---:|---|---:|---|
| `ai-team-kit.zip` | 83,953 | `aea5c8df14ecf11e47fd4ca85f16f6b5a64e5d029c8d6e093dfdd68d15adf73e` | 16 | **Canonical delivered v1** named by `FILES.md` |
| `harness.zip` | 108,680 | `d1e0b3b83bd6b95c3eb761825e0c06a443f051d8fb383ca259e8ae526203b1cd` | 20 | Extra superset; not named as a delivered outer file in `FILES.md` |

Byte-for-byte result after extraction:

- All 16 files common to both archives have identical SHA-256 hashes.
- `harness.zip` therefore contains the same delivered kit **plus four extra
  documents**. It is not a different code version.
- The separate top-level `AI-Team-Setup-Guide.md` and the in-zip
  `harness/GUIDE.md` are byte-identical: 41,293 bytes, SHA-256
  `f2d64d7fbca319f9259eadb3e34b776b226291597e72c89ef34bd682c4077ce7`.

### Canonical 16-file inventory

| Zip member | Bytes | Purpose |
|---|---:|---|
| `harness/GUIDE.md` | 41,293 | Current beginner setup/use guide; same bytes as top-level guide |
| `harness/README.txt` | 981 | Short folder map and command sequence |
| `harness/harness.sh` | 28,164 | Main `harness` command |
| `harness/harness_ui.py` | 77,152 | Local dashboard server and embedded web page |
| `harness/install.sh` | 7,060 | One-time installer for prerequisites managed by the kit |
| `harness/model_scout.py` | 83,687 | Model discovery, probing, ranking, keys, router-list writer, self-test |
| `harness/mac/Start AI Team.command` | 190 | Mac launcher for `harness open` |
| `harness/mac/Stop AI Team.command` | 138 | Mac launcher for `harness stop` |
| `harness/skills/self-extend/SKILL.md` | 3,076 | Cautious research/add-missing-ability workflow |
| `harness/skills/team-workflow/SKILL.md` | 3,587 | Handoff/worklist/log workflow |
| `harness/skills/team-workflow/templates/HANDOFF.md` | 307 | Small handoff template |
| `harness/skills/team-workflow/templates/IMPROVEMENT_LOG.md` | 125 | Append-only log template |
| `harness/skills/team-workflow/templates/WORKLIST.md` | 338 | P0/P1/P2 and `[human]` worklist template |
| `harness/skills/team-workflow/templates/worker-prompt-extension.md` | 655 | Per-worker project-memory reminder |
| `harness/windows/Start AI Team.bat` | 776 | WSL launcher for `harness open` |
| `harness/windows/Stop AI Team.bat` | 452 | WSL launcher for `harness stop` |

Full SHA-256 values for every member are in Appendix A.

### Comparison with `FILES.md`

`FILES.md:7-8` names `ai-team-kit.zip` as the final delivered kit and
`AI-Team-Setup-Guide.md` as the current separate guide. The delivered member
names match that description.

Still absent from the repository folder and from both zips, exactly as
`FILES.md:12,18-20,32` and `OPEN.md:5-11` warn:

- patched `model_scout.py` with creative roles/endpoints;
- `mcp/oat_mcp_loader.py`;
- `mcp/oat_mcp_apply.py`;
- `toolchains.sh` (planned, not written);
- dashboard/MCP sandbox test files such as `run_tests.py`, `dom_test.js`,
  fake-provider helpers, and stub commands.

Runtime/secret files listed in `FILES.md:27-31` are also absent, which is
correct: they must not be uploaded.

---

## 3. How the kit helps the project

### 3.1 It turns changing free models into stable job names

The project does not hard-code one model per helper. The picker writes
LiteLLM groups named `architect`, `implementer`, and `reviewer`
(`model_scout.py:94-98,592-615`). OAT and the dashboard then request those
steady names. When a free model disappears or a better one appears, a later
picker run can replace the model behind the same job name.

Default providers in the delivered code are
(`model_scout.py:72-82`):

| Provider | Key variable | Catalog style | Router prefix | Important limit in code |
|---|---|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | OpenRouter | `openrouter` | Free only when prompt/completion pricing are both zero; 12-request probe budget |
| NVIDIA | `NVIDIA_API_KEY` | OpenAI-style | `nvidia_nim` | `assume_free: true` because `/models` gives no price |
| Mistral | `MISTRAL_API_KEY` | OpenAI-style | `mistral` | `assume_free: true` |
| Google | `GEMINI_API_KEY` | OpenAI-style | `gemini` | `assume_free: true`; only model IDs matching `flash` are included |

This settles the old README discrepancy about NVIDIA/Google coverage at the
**delivered-config level**: both are present. It does not prove that a model
is actually free on the owner's account today. For NVIDIA, Mistral, and
Google the code explicitly assumes free status from the endpoint/account
rather than pricing data.

### 3.2 It quick-tests models gently instead of trusting names only

The probe asks each candidate to:

1. call a `get_weather` tool correctly for Paris;
2. trace two tiny Python programs;
3. identify the one buggy line in two tiny functions; and
4. return one strict JSON object with exactly three steps
   (`model_scout.py:127-149,447-507`).

A model that fails the tool-call stage is not ranked for any role
(`model_scout.py:489-490,510-518`). The role score combines probe results,
weak name/size priors, recency, context size, latency penalty, stealth
penalty, and incumbent stickiness (`model_scout.py:99-124,510-534`). A role
keeps up to three picks, normally at most two from one provider, and the
reviewer's first pick is made independent from the implementer's first pick
when possible (`model_scout.py:537-589`).

Default pacing is one model at a time **per provider**, a 20-second pause
between models of the same provider, at most six candidates per provider in
a run, 24 reserved requests per provider by default, and 12 for OpenRouter
(`model_scout.py:110-120,940-983`). Different providers may be probed side
by side (default `services_at_a_time: 4`).

Results are cached for three days; dead models are set aside for seven days,
or about one day for short-dead cases such as 402/403
(`model_scout.py:110-113,470,984-991`).

### 3.3 It writes a safer router list and explains service states

The picker generates LiteLLM entries with `order` equal to rank, provider
keys referenced as `os.environ/...`, a master key referenced as
`os.environ/LITELLM_MASTER_KEY`, retries/cooldown settings, and fallback
rules as separate one-key dictionaries (`model_scout.py:592-615`). Writes
are atomic (`model_scout.py:624-631`).

Service states are `ok`, `skip`, `refused`, `offline`, `limit`, `blocked`,
and internal `warn` where applicable (`model_scout.py:24-28,749-776`). A
role with no passing model can borrow another role's picks or be marked
`unavailable`; the user-facing report says “using picks from other roles” or
`UNAVAILABLE` (`model_scout.py:573-589,1043-1047`).

Exit codes are `0` for no change, `10` for a changed list, and `1` for a
problem (`model_scout.py:27,1026-1032,1068-1085`). `harness scout` treats
`10` as success and restarts the router if it is running
(`harness.sh:320-333`).

### 3.4 It makes first setup and daily operation mostly one command

`README.txt:14-23` gives the intended sequence:

```text
bash ~/harness/install.sh
harness setup-keys
harness github-login
harness connect-oat
harness start
harness add-repo https://github.com/OWNER/NAME
harness open
```

The installer (`install.sh:21-128`):

- refuses root unless `HARNESS_ALLOW_ROOT=1`;
- requires `git`, `curl`, Python 3.11+, `gh`, and Python `venv`;
- installs `uv` if missing;
- links `harness.sh` to `~/.local/bin/harness`;
- installs `litellm[proxy]` into `~/litellm-env`;
- downloads and runs OAT's installer with `OAT_VERSION=v0.1.0` by default;
- installs the built-in skills; and
- on WSL, attempts to place Start/Stop shortcuts on the Windows desktop.

`harness start` refreshes the scout list if the state is older than 12 hours,
starts LiteLLM on `127.0.0.1:4000`, then starts OAT
(`harness.sh:65-67,107-154,439-459`). `harness open` also starts the
dashboard and opens its token URL (`harness.sh:482-497`). AI keys are loaded
only for scout/router processes that need them; OAT and the UI are started
with those variables removed (`harness.sh:38-47,145-154,165-179`).

Important nuance: there is no cron job or background scheduler in the zip.
“Checks every day/twice a day” happens only when `harness start`, `open`, or
`scout` runs and the saved state is stale.

### 3.5 It connects OAT with auto-merge off

`harness connect-oat` writes an OAT provider block for the three router role
names using `langchain_openai:ChatOpenAI`, plus an OAT `.env` entry using the
router password as `OPENAI_API_KEY` so OAT's startup provider check can pass
(`harness.sh:335-377`). It refuses to overwrite an existing hand-written OAT
config that lacks the harness marker.

`harness add-repo` calls `oat init ... --no-merge-queue
--model=litellm:architect`, sets `--mq-enabled=false`, and makes the repo the
default (`harness.sh:419-437`). That matches the project rule that the owner
reviews and merges pull requests.

These mechanisms are present in code. Their behavior against a real OAT
0.1.0 installation was **not reproduced in this session**.

### 3.6 It gives the owner a local dashboard instead of many commands

`harness_ui.py` is a standard-library Python server bound to
`127.0.0.1:8765` by default (`harness_ui.py:36-56,1255-1273`). Its routes
cover state, keys, GitHub login, chat, task creation, direct model questions,
harness jobs, repository selection, files, diffs, pull requests, models,
logs, and skills (`harness_ui.py:836-846`).

The embedded page has:

- centre tabs: Chat, Tasks, Ask the models;
- right tabs: Files, Changes, Pull requests, Models, Connections, Skills,
  Logs (`harness_ui.py:1040-1041`).

Chat sends text with `oat agent tell <agent> <text> --repo <repo>` and reads
the workspace agent's log as a transcript (`harness_ui.py:267-276,411-456`).
Tasks call `oat worker create ... --model litellm:<role> --repo <repo>`
(`harness_ui.py:459-469`). Pull-request list/diff/merge/close use `gh`
(`harness_ui.py:634-688`). The Merge and Close actions ask the browser user
to confirm first (`harness_ui.py:1222-1223`).

Dashboard security mechanisms visible in code include a random token file,
host allow-listing, token comparison with `hmac.compare_digest`, POST
content-type/custom-header checks, content-security-policy headers, path
containment checks, name validation, secret-environment stripping for child
processes, and loopback binding (`harness_ui.py:66-108,169-181,850-950`).
Codespaces hostnames are additionally allowed when `CODESPACES=true`, so the
token and GitHub's forwarded-port controls matter there
(`harness_ui.py:850-857`).

The dashboard's **Stop** job maps to `harness stop-team`, which stops OAT
and the router but deliberately leaves the dashboard running
(`harness_ui.py:208-215`; `harness.sh:468-472`). That static mapping matches
the old chat's “Stop button fixed” claim, although the button was not run
here.

### 3.7 It teaches helpers the owner's project-memory workflow

`team-workflow/SKILL.md:10-58` tells a helper to find handoff, worklist,
planning, decisions, and improvement-log files; read them before work; take
one item per pull request with its ID; avoid human-only items; run/report
tests honestly; and update worklist/log/handoff in the same PR. The
workspace helper may split independent items with `oat worker create`, at
most three helpers at once, and must never merge.

`self-extend/SKILL.md:14-52` tells a helper to research installed skills,
project docs, then the web; check licence/maintenance/scripts; refuse
download-and-run, `sudo`, secret-reading, and unknown exfiltration patterns;
add safe items only through PRs; and ask first for third-party skills,
workflow changes, project dependencies, or anything outside the project.

This is directly relevant to the owner's Gifscythe workflow. The guide's
optional `gifscythe-guardrails` example names OD-16, OD-18, the wasm A/B
choice, the 1.0.0 bump, release re-cut, and W-18/W-19 as owner/human areas
(`GUIDE.md:655-680`). Those are target-project rules, not kit features.

### 3.8 What it does not do in v1

The delivered kit does **not** provide:

- MCP loading for OAT; the dashboard explicitly says the team does not load
  MCP servers directly (`harness_ui.py:1165`; `GUIDE.md:619,702`);
- writer/editor creative roles (the only `editor` hit is the Codespace web
  editor in the guide);
- `--list-services`, `--add-endpoint`, `only_roles`, or endpoint presets;
- AI Horde, Groq, Cerebras, GitHub Models, or Colab presets;
- Odysseus installation/commands or a persona room;
- sequential-thinking tooling;
- Qt/CMake/C#/Node toolchain installation;
- a Docker build (the guide says it was not built, `GUIDE.md:91-95,909`);
- a built-in scheduler that runs while the computer/team is stopped.

A technically knowledgeable user can add another OpenAI-style provider in
`scout.yaml` using the comment at `model_scout.py:69-72`, but `harness.sh`
still has a static four-service list (`harness.sh:24,51-60`) and there is no
beginner endpoint-adding flow. That is an extension point, not out-of-box
support.

---

## 4. The four `harness.zip`-only documents

| Extra file | Classification | Relation to the kit/project |
|---|---|---|
| `harness/gifscythe-ai-team-setup-guide.md` (32,799 B) | **Superseded earlier guide** | A 16-step, terminal-centred guide for the earlier standalone `model_scout.py` + `harness.sh` phase. It says the picker had 34 checks (lines 870-876) and predates the dashboard/installer flow. Keep only as history; do not use for setup. |
| `harness/GIFSCYTHE_PLANNING_REPORT.md` (9,480 B) | **Target-project planning document** | Plans Gifscythe itself: keep C++17/Qt6 for the EXE track, treat client-side wasm as an unproven additive track, compare building `gifsicle.wasm` vs adopting a prebuilt package, and leave OD-16/OD-18/version decisions to the owner. It explains why Qt/CMake/Windows/toolchain questions matter to a future helper team, but it is not kit code and does not prove the kit can build Qt. |
| `harness/gifscythe-independent-review.md` (13,631 B) | **Target-project source review** | A read-only review of Gifscythe at commit `7a0a8b8883e35e3233944095e1ca9544cd10f500`, with eight candidate findings explicitly not runtime-executed. It could become candidate work for a future team on the Gifscythe repo; it is unrelated to whether this kit works. |
| `harness/draft query that need refinement.txt` (1,961 B) | **Handoff-generation prompt** | The owner's draft instruction that produced `HANDOFF.md`, `PROVEN.md`, `OPEN.md`, and `FILES.md` as conversation snapshots. It explicitly says not to re-test or recreate files and to mark uncertainty. This helps explain why the handoff notes are useful snapshots rather than fresh proof. |

None of the four should silently become part of the canonical v1 baseline.
The planning report and independent review belong conceptually with the
Gifscythe target project; the old guide is superseded; the draft query is
meta-history.

---

## 5. Old-chat claims matched to delivered files

### 5.1 Delivery and dashboard claims

| Old-chat/readable claim | Delivered evidence | Verdict |
|---|---|---|
| Oct 7: “kit zip is 84 KB”; Oct 8: dashboard + installer delivered in `ai-team-kit.zip`, guide separate | Uploaded canonical zip is 83,953 bytes with 16 `harness/` files; separate guide is byte-identical to in-zip guide | **Verified in delivered files** for existence/size; “installs cleanly into a brand-new home” remains old-chat report only |
| Dashboard opened by Start AI Team / `harness open`; chat, tasks, files, +/- counters, PRs with Merge/Close, models, keys, skills, logs | Launchers call `harness open/stop`; `harness open` starts team/UI; routes and page tabs/actions exist | **Code present, runtime not reproduced** |
| Chat is a transcript of helper terminal output, not polished bubbles | Chat API sends via `oat agent tell`, stores offsets, and reads `~/.oat/output/<repo>/<agent>.log`; page polls every 2 seconds | **Verified as mechanism**; real OAT log shape not reproduced |
| MCP plug-ins are not supported by the agent team in v1 | UI card and guide say exactly that; searches find no MCP loader/config implementation | **Verified in delivered files** |
| Skill/design repositories can be used through Skills tab; SkillOpt itself not integrated | Skills preview clones a GitHub repo to temp, lists `SKILL.md` folders, flags scripts, reports licence filename, installs selected folders; no SkillOpt code | **Code present, runtime not reproduced**; it does not validate licence text or scan scripts for safety |

### 5.2 Model-picker claims

| Old-chat/readable claim | Delivered evidence | Verdict |
|---|---|---|
| Smart selection finds currently free models, probes them, ranks per role, rewrites router list behind stable names | `fetch_catalog`, static filtering, `probe_candidate`, `rank_role`, `select`, `build_litellm`, state/report writing | **Verified in delivered files**; real-provider behavior not reproduced |
| Self-test evolution: 23 checks, then 33/34, then 68 | Earlier standalone scout versions are not in the zip; delivered `selftest()` has 64 `check_` call sites, including two inside a 3-role LiteLLM loop | **Counts reconciled**; old version counts are history, not current results |
| 68 checks pass on final picker | With LiteLLM installed, 62 non-loop checks + 2 checks × 3 roles = 68 logical `ok` lines. This session: 62 `ok`, one skip line, exit 0 | **Mostly verified by this session's run**; six LiteLLM Router checks were skipped, not passed here |
| Real network code tested against a fake AI service on same computer | `_FakeProvider` binds two local HTTP servers; self-test calls real `IO()` for catalog/chat/check/run/keys cases | **Verified by this session's run** |
| Generated config loads in real LiteLLM / Router order and fallbacks resolve | Conditional code at `model_scout.py:1517-1527`; fallback dict shape also checked without LiteLLM | **Not reproduced here** because `litellm` is absent; old sandbox may have had it installed |
| Paced testing: one model at a time per service, 20-second rest, weekly-most-used/biggest first | Defaults and `order_for_testing`; self-test FakeIO records per-service peak 1, sleeps, and order | **Verified by code + this session's self-test** |
| `EMPTY` replaced by borrowed roles or `UNAVAILABLE`; service status words clarified | `select()` returns `ok/borrowed/unavailable`; self-test checks borrowed and no-model cases | **Verified by code + this session's self-test** |
| Dry-run no longer spends probes/writes | `run()` branches around dry-run; self-test checks no requests/files | **Verified by this session's self-test** |
| Maintenance/garbage reply pauses service instead of marking model dead for a week | Probe error classification and local fake-provider garbage case | **Verified by this session's self-test** |
| 403 sets a model aside about one day, not seven | `ModelDead(short=...)` for 402/403; local HTTP self-test checks remaining TTL | **Verified by this session's self-test** |
| Two bug questions no longer share same answer | Delivered expected lines are `6` and `5` (`model_scout.py:138-143`) | **Verified in delivered files** |
| Thinking text / content-parts answers handled | `clean()` strips `<think>...`; `as_text()` joins list parts; corresponding self-test lines passed | **Verified by this session's self-test** |
| Missing `~/.litellm`, half-written files, no-internet empty save handled | `atomic_write` creates parent and replaces; offline case in self-test preserves router list/picks | **Verified for tested paths** |
| Refused key remembered and not retried forever | SHA-256 key fingerprint in `bad_keys`; self-test checks refused/replaced behavior with FakeIO | **Verified by this session's self-test** |
| OpenRouter privacy/data-policy would not blacklist every model | 404 + `data policy` becomes service-level `blocked`; self-test checks no dead marking and fix message | **Verified by this session's self-test** |
| Cross-host redirect cannot carry a key | `_SameHostRedirect`; local two-server redirect check | **Verified by this session's self-test** |
| One odd reply does not crash a whole run | Per-candidate exception handling appends a skip note (`model_scout.py:966-969`) | **Code present**; not every possible odd reply is proven |

### 5.3 Keys, harness, OAT, and safety claims

| Old-chat/readable claim | Delivered evidence | Verdict |
|---|---|---|
| Keys are asked one service at a time; Enter skips/keeps; each new key tested before save | `prompt_one_key`, `cmd_setup_keys`, `cmd_set_key` in `harness.sh:234-311`; `set_key()` tests first | **Code present**; shell prompts not run here |
| Refused new key keeps old key; replacement keeps `keys.env.bak`; saved refused key later shows `[refused]` | `write_keys` backups + `0600`; `record_status`/`bad_keys`; local fake-provider self-test covers Python functions | **Python key logic verified by this session's self-test**; interactive shell path not run |
| Keys table never shows a full key | `mask_key`, `keys_table`, self-test serializes table and checks full fake key absent | **Verified by this session's self-test** |
| Router password is generated | `ensure_master()` uses `secrets.token_hex(16)` with `sk-` prefix; self-test checks create-once behavior | **Verified by this session's self-test** |
| Ubuntu refuses empty password and accepts `1234`/`word` | Guide repeats “I tried” (`GUIDE.md:121-126`); no password test code in kit | **Old-chat/guide report only**; not retested here and weak passwords remain risky |
| Router listens only locally with generated password | LiteLLM config references env master key; `harness start_router` passes `--host 127.0.0.1` (`harness.sh:107-127`) | **Code present, runtime not reproduced** |
| OAT gets no AI keys in its environment | `start_oat` and `start_ui` remove provider/master vars; UI `clean_env` does same for children | **Static mechanism verified**; `/proc` runtime claim from old sandbox not reproduced |
| `connect-oat` fixed OAT refusing projects without a provider key | Writes router password/base URL into `~/.oat/.env` specifically for that check | **Workaround code present**; real `oat init` not reproduced |
| Auto-merge helper off | `--no-merge-queue`, `--mq-enabled=false` in `cmd_add_repo` | **Code present, OAT runtime not reproduced** |
| `--repo` goes at end with full project name; default repo set by add-repo | Commands use `--repo` in worker/chat calls; `oat repo use` called on add | **Code matches explanation** |
| Fresh install worked with newest LiteLLM | Installer installs unpinned `litellm[proxy]`; no lockfile/version record in zip | **Old-chat report only**; not reproducible as a pinned claim from delivered files |

### 5.4 Dashboard test claims

The guide says `harness_ui.py` has 84 checks: 63 server checks and 21 page
checks in a test browser engine (`GUIDE.md:897`). The delivered zip contains
**none of the test harness files**, and `FILES.md:32` says those files were
sandbox-only and never delivered.

What this session can say:

- `harness_ui.py` parses as valid Python syntax (AST parse only).
- The routes/security mechanisms described in Section 3.6 are present.
- The specific “Stop stops only team/router” fix is visible statically.
- The 84-check outcome, browser/DOM behavior, non-English chat-offset fix,
  connection-body handling, and every-route behavior remain **old-chat
  report only** until a future named task rebuilds/runs dashboard tests.

Likewise, the guide's `harness.sh` test list (`GUIDE.md:895`) matches real
functions, and `bash -n` passes, but this session did not execute
`start/stop/status/ask/doctor/open/add-repo/connect-oat`.

### 5.5 Research, scope, and unfinished-work claims

| Old-chat/readable claim | Delivered evidence | Verdict |
|---|---|---|
| Original plan had wrong OAT URL/commands/settings; LiteLLM fallback dict issue; keypool unnecessary; router exposure; auto-merge risk | Current guide records the corrections (`GUIDE.md:807-860`); delivered code has separate fallback dicts, loopback router, OAT config block, auto-merge off, no keypool | **Delivered design reflects the corrections**; the old sandbox experiments themselves are not reproduced |
| OAT loads Agent Skills natively, so no custom harness is needed for skills | Kit ships/installs `SKILL.md` folders; UI lists user/project skills | **Kit-side mechanism present**; actual OAT loading not reproduced here |
| Oct 10 answer began “Not yet”: no MCP, persona rooms, Colab endpoints, toolchain installer; Odysseus not yet integrated | Delivered zip searches and inventory agree | **Verified as v1 scope** |
| Covered sources: NVIDIA NIM, Google AI Studio Flash, OpenRouter, Mistral; Groq/Cerebras/GitHub Models not added | Default provider table has exactly those four; no hits for the other names | **Verified in delivered config**; current free limits not checked |
| Qt 6.4/CMake/Ninja test built headless; C# SDK installed but NuGet blocked | No toolchain script, build logs, or artifacts in either zip | **Old sandbox report only** |
| Odysseus agent mode “built on OpenCode” | Not a claim about the delivered kit; separate Odysseus inspection did not corroborate that sentence | **Do not repeat**; settle from Odysseus primary source in its own task |
| After “Native and MCP also”, old chat began an MCP manager | No `mcp/` folder, presets, loader, or apply file in either zip; `HANDOFF.md:19-24` itself says those were sandbox-only/never presented | **Missing from delivered zip** |
| Creative-roles scout patch was applied in old sandbox | Delivered scout has no writer/editor probe skills/roles, no `only_roles`, no endpoint presets/list/add commands; defaults still budget 24/12 and max 6 candidates | **Missing from delivered zip**; delivered zip is the pre-patch v1 scout |
| AI Horde and OpenMAIC questions were still pending | No Horde support/opinion artifacts; `HANDOFF.md:23,29` queues them as T2 | **Still open**; this report only proves they are absent from v1 |
| Handoff snapshot files were created at the end | `HANDOFF.md`, `PROVEN.md`, `OPEN.md`, `FILES.md` are now in the repo folder; the draft prompt is in `harness.zip` extras | **Verified present as snapshots**, not verified as truth |

---

## 6. Discrepancies and watch items found while learning

1. **Self-test count needs an environment qualifier.** “68 checks” is the
   count when LiteLLM is importable by the Python running the scout. Without
   LiteLLM the same delivered file prints 62 checks and an explicit skip.
   Future reports must state the Python environment, not just “68 passed”.

2. **No scheduler is included.** Guide wording such as “checks every day”
   and the old chat's “twice a day” can mislead. The code refreshes during
   `harness start/open` if the state file is at least 12 hours old; it does
   not wake itself up.

3. **Installer supply-chain pinning is incomplete.** `install.sh` installs
   `uv` with `curl ... | sh`, installs the latest available
   `litellm[proxy]`, and downloads OAT's installer from the `main` branch
   before running it with `OAT_VERSION` (default `v0.1.0`)
   (`install.sh:60-65,80-101`). Downloading to a temp file is better than a
   direct pipe for OAT, but neither the OAT installer script nor LiteLLM is
   hash/version-pinned in the delivered kit. Do not run the installer as a
   future task without first reviewing current upstream install inputs.

4. **Free status is partly assumed.** OpenRouter candidates must have zero
   pricing in its catalog. NVIDIA/Mistral/Google are `assume_free: true`, so
   account/plan/terms still decide. A model can also cost quota, log prompts,
   or be trial-only even if the endpoint answers.

5. **Skills installation is a trust decision, not a safety proof.** The
   dashboard previews names/descriptions, flags script files, checks size
   and skill-name shape, reports whether a licence-like filename exists, and
   removes copied symlinks (`harness_ui.py:764-822`). It does not read the
   licence for compatibility or prove scripts safe. The stricter rules are
   instructions in `self-extend`, not an automated scanner.

6. **The keys file is shell-sourced by `harness.sh`.** Provider keys are
   whitespace/quote-normalized by the scout and the file is written `0600`,
   but `write_keys` writes unquoted `NAME=value` lines and `with_keys`
   sources the file (`model_scout.py:695-728`; `harness.sh:38-47`). Treat a
   keys file as trusted local configuration/code: never import one from an
   untrusted source. This was observed statically; no fix was attempted in
   this learning task.

7. **Default target remains Gifscythe.** `harness.sh:13-14` defaults to
   `freeforall1932-design/gifscythe` (overridable by environment) and the
   guide examples/guardrails are Gifscythe-specific. Using the kit for
   another repo still needs the right token scope, `add-repo`, and project
   selection.

8. **Codespaces numbers are guide claims, not rechecked here.** The earlier
   “about 60 hours” and guide “about 120 core-hours (60 hours on 2-core)”
   can describe the same quota shape, but current official terms were not
   looked up in this task.

---

## 7. The one self-test run in this session

### Isolation and command

Python reported by the sandbox:

```text
Python 3.11.2
/usr/bin/python3
```

The delivered script was invoked exactly once as:

```bash
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/tmp/ai-team-kit-learn-20261017/selftest-run-20261017/home \
  TMPDIR=/tmp/ai-team-kit-learn-20261017/selftest-run-20261017/tmp \
  PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/python3 \
  /tmp/ai-team-kit-learn-20261017/kit/harness/model_scout.py --selftest
```

Result:

- exit code: **0**;
- stderr: **empty**;
- stdout: **62 lines beginning `  ok  `**, **0 `FAIL` lines**;
- one explicit skip: `skip LiteLLM checks (litellm is not installed in this
  Python)`;
- final line: `selftest passed`;
- isolated `HOME` and `TMPDIR` contained no leftover files after the run
  (the script removes its own temporary directory).

### Why 62 here can correspond to 68 in the old chat

Static AST counting found **64 `check_` call sites** inside `selftest()`.
Two of those call sites are inside:

```python
for role in cfg["roles"]:
    check_(... first choice ...)
    check_(... fallback ...)
```

There are three roles, so when LiteLLM imports successfully those two call
sites execute six times. The arithmetic is:

```text
62 checks outside the LiteLLM loop
+ 2 checks × 3 roles inside the LiteLLM loop
= 68 logical checks
```

In this session the loop did not run because `import litellm` failed and the
script printed its designed skip line. Therefore the honest current result
is **62 passed, 6 LiteLLM Router checks skipped**, not “68 passed here.”

The self-test did exercise the real `IO` HTTP code against two fake
providers bound to ephemeral `127.0.0.1` ports. It set only fake keys inside
its own process. It did not contact OpenRouter, NVIDIA, Mistral, Google, or
GitHub.

Full stdout is preserved in Appendix B.

---

## 8. Step 0 completion and reconciled queue

This owner-named unpack/learn/match task completes the substantive work
that the folder README called **Step 0**:

- detailed comparison against `FILES.md`: **done**;
- canonical zip inventory with sizes/hashes: **done**;
- real kit guide/code read: **done**;
- actual provider config reported: **done** (OpenRouter, NVIDIA, Mistral,
  Google Flash; current free terms still not researched);
- self-test run once with exact command/Python/exit/output: **done**;
- `harness.zip` classified: **done** (same code + four extra documents);
- Steps ↔ T-numbers reconciled: **below**.

It does **not** authorize installation, T1 implementation, MCP rebuilding,
Odysseus integration, provider research, or v2 building. The owner still
names one next task.

| Handoff task | Relationship to README Steps | State after learning the delivered zip |
|---|---|---|
| **T1** Finish scout upgrade/self-test for creative roles | Parts of Step 2 + Step 4 | Cannot proceed as originally written because the patched scout is lost. First a named rebuild/spec task must re-apply the patch from `HANDOFF.md`/`OPEN.md` descriptions to the delivered scout, with guesses labelled; then update/rerun self-tests. |
| **T2** Answer AI Horde + OpenMAIC | Step 1c + Step 1d | This report answers only “not in v1.” Current official API/terms/licence/opinion still need a named research task. Step 1a is answered at file level (Odysseus not in v1); Step 1b Colab terms remain separate. |
| **T3** Dynamic harness services + `add-endpoint` | Step 2 / Step 5 slice | Blocked by rebuilt T1 interfaces (`--list-services`, `--add-endpoint`). Delivered `harness.sh` is static four-service. |
| **T4** OAT MCP commands/UI | Step 4 + Step 5 | Owner has since confirmed MCP for OAT = YES, but loader/apply files are lost and must be rebuilt/tested as a named task. Delivered UI explicitly has no MCP. |
| **T5** Odysseus native commands/UI link | Step 3 design, then Step 5 | Delivered kit has zero Odysseus code. The separate Odysseus source pin exists, but harness-choice/design/install work is not authorized by this learning task. |
| **T6** `toolchains.sh` | Step 5 support slice | Independent in dependency terms, but still needs owner naming and admin-user safety design. Nothing exists in v1. |
| **T7** Dashboard dynamic roles/services + tests | Step 5 slice | Depends on T1/T3 and on rebuilding missing dashboard test harnesses. Delivered UI roles are fixed to the three coding roles. |
| **T8** Guide add-ons | After T1-T7 | Current guide accurately describes v1 scope in most places; add-on sections should wait until features exist. |
| **T9** Repackage + fresh-install/all tests | Final Step 5 packaging | Cannot be claimed until rebuilt pieces and test suites exist and are actually run. |
| **T10** Later choices: personas/OpenCode/Docker | Step 3/parked | Native Odysseus and OAT-MCP decisions are recorded, but persona preset design, extra harness choice, and Docker remain unbuilt/unnamed. |

Suggested owner wording for the next single task is intentionally left as a
choice, for example: **“Do T2”** for answers only, **“Rebuild the T1 scout
patch as a spec”** before code, or **“Do Step 3”** for harness comparison.
Do not infer one from “next” or “continue.”

---

## 9. Tested / not tested summary

### Tested or verified in this session

- Both zips extracted safely to scratch; canonical files hashed.
- All 16 common files byte-identical across the two zips.
- Top-level guide byte-identical to in-zip guide.
- Delivered guide/code/skills/templates/launchers read.
- Four `harness.zip`-only documents read and classified.
- Old shared chat visible text re-read and matched as above.
- Python AST syntax: `model_scout.py` and `harness_ui.py` parse.
- Shell syntax: `bash -n harness.sh install.sh` passes.
- Delivered `model_scout.py --selftest`: **1 run**, Python 3.11.2, exit 0,
  62 `ok`, 0 `FAIL`, LiteLLM Router checks skipped.

### Not tested in this session

- Installer, fresh-home install, LiteLLM download/version behavior.
- Real LiteLLM Router loading/order/fallback checks (skipped by self-test).
- OAT install/daemon/workers/reviewers or its skill loading.
- Dashboard server, browser page, DOM behavior, or the claimed 84 checks.
- `harness` runtime commands other than reading/syntax-checking the script.
- Real provider catalogs, keys, free quotas, model quality, or terms.
- Real GitHub token login, `oat init`, PR creation, dashboard Merge/Close.
- Windows/WSL, macOS, Codespaces, Docker.
- Odysseus, MCP, AI Horde, Groq, Cerebras, Colab, OpenMAIC, toolchains,
  persona rooms — all absent from the delivered v1 zip as implementations.

---

## Appendix A — full member SHA-256 hashes

### `ai-team-kit.zip` members (also the common members of `harness.zip`)

| Member | SHA-256 |
|---|---|
| `harness/GUIDE.md` | `f2d64d7fbca319f9259eadb3e34b776b226291597e72c89ef34bd682c4077ce7` |
| `harness/README.txt` | `4ec950633dfe75007676d25cc73dfec7ad12bc1411d68ea626d761b6daa72fc6` |
| `harness/harness.sh` | `0d86e563a006693da1606908535de6c36dbf14a6a820439641970fbcc5e49399` |
| `harness/harness_ui.py` | `c59bce59561f3f792fd8cc11f8bd7e9e89a903c0aebe32d73d154fcd84cacb88` |
| `harness/install.sh` | `8e9038adb7bb9b5387c45df6ee1c7b5542bb903bed32a7047c9ff4570e00cb39` |
| `harness/mac/Start AI Team.command` | `c8635505de272e00fec1ccc4e12dbde649ad6d72d1c83ac7d6879e9be217902e` |
| `harness/mac/Stop AI Team.command` | `ee80c3f8df56675b71e0f9ffc788f973582ef38859c405dc60f617e5318e7db2` |
| `harness/model_scout.py` | `263c9ac8dbdcc19b891a9197b7cb82ec99f4ff35b004923fefb2d222491b5e08` |
| `harness/skills/self-extend/SKILL.md` | `a7c50eaa28fc22f8dd9d4783d43682c0a999190c76c0d3a9de96e61bcd25965a` |
| `harness/skills/team-workflow/SKILL.md` | `1cfa57bfbe8eca6acff41d7e001330f2597824ff6b4b0814f0b0ea0f5de42fc6` |
| `harness/skills/team-workflow/templates/HANDOFF.md` | `5fa58295a38276cc00441a990b89d0e0bbc87db91e0d2f0e544003da404db111` |
| `harness/skills/team-workflow/templates/IMPROVEMENT_LOG.md` | `f0c3d059ca471ee0bee12c85619d11c717623ec2013548a3e45040625016d5eb` |
| `harness/skills/team-workflow/templates/WORKLIST.md` | `6c912621f520be2167fecf44420f735e1ba3e8a78a45868f717510671773d963` |
| `harness/skills/team-workflow/templates/worker-prompt-extension.md` | `63530a5215ff70e429df0be9e296ea182f34892d182acea937438754e1de2e5a` |
| `harness/windows/Start AI Team.bat` | `d880ab2d5bc9fc6b52824117241c466b19a60b498a8ddef25912952ef0795d09` |
| `harness/windows/Stop AI Team.bat` | `620e4585be9dc2667b4aa1c9a0b1f6f07495fae1d3bf1da259895cc0179586a3` |

### `harness.zip`-only members

| Member | Bytes | SHA-256 |
|---|---:|---|
| `harness/GIFSCYTHE_PLANNING_REPORT.md` | 9,480 | `4909852dcf761f97992ae5da49b6a4192657cd2c195888060843f6008b80fb1c` |
| `harness/draft query that need refinement.txt` | 1,961 | `c51b1ff6856d2ecf5175b0bfe9deacccf5411127985fa0a32b244f7b4addc15f` |
| `harness/gifscythe-ai-team-setup-guide.md` | 32,799 | `030c013bc3acccfbef4ce194e01eebb9cb890f47332e3a2acc4f61d916e58513` |
| `harness/gifscythe-independent-review.md` | 13,631 | `75c77c7711c93d80ec1602de15aa43304d2e739f74c3d265d7de2c14a41dc386` |

---

## Appendix B — full stdout from the one self-test run

```text
== settings are validated
  ok   a badly written pin gives a clear message instead of a crash
  ok   a single pin written as text is accepted
  ok   a plain-http service address is flagged
== answers are read sensibly
  ok   thinking text before the answer is ignored
  ok   answers sent as a list of parts are read
  ok   bug-line answers are checked strictly
== default test budget protects the scarce OpenRouter free quota
  ok   OpenRouter tests capped at the budget (12 <= 12)
== --dry-run spends nothing and writes nothing
  ok   no requests sent, no files created
== gentle pacing: one model at a time per service, with a rest between models
  ok   list written (exit code 10)
  ok   never two models at once on the same service (peak {'https://openrouter.ai/api/v1': 1, 'https://integrate.api.nvidia.com/v1': 1, 'https://api.mistral.ai/v1': 1, 'https://generativelanguage.googleapis.com/v1beta/openai': 1})
  ok   it rests between two models of the same service
  ok   NVIDIA: the biggest model is tested first
  ok   OpenRouter: the most-used model of the week is tested first
  ok   progress lines are printed while testing
  ok   with models_at_a_time = 2 never more than two at once per service
  ok   with services_at_a_time = 1 only one test runs at any moment
== picks look right
  ok   embedding, paid, no-tools, expiring, image, non-flash and 'pick for me' models excluded
  ok   tiny model that only passes the tool test is not selected
  ok   every role spans at least 2 services
  ok   independent reviewer: reviewer #1 is a different model from implementer #1
  ok   stealth model is never rank #1
== no internet during a run: nothing is changed or saved
  ok   run fails clearly (exit code 1); the router list and the picks stay as they were
  ok   every service is shown as [offline]
== run 2: same day again -> saved results, nothing new
  ok   exit code 0 and zero new test requests
== run 3: a strong new free model appears, another disappears
  ok   new model was tested and promoted
  ok   report lists the new free model
  ok   report lists the vanished model
  ok   vanished model removed from the list
== run 4: a service rate-limits us during tests -> nothing marked unusable
  ok   a rate limit is temporary: shown as [limit], nothing marked unusable
== run 5: free quota is gone (limit 0) -> model dropped
  ok   'limit 0' marks the model unusable
== a key that is refused is remembered until it is replaced
  ok   401 marks the service [refused]
  ok   a refused service is not used in the picks
  ok   next run does not try the refused key again (it prints refused, like skip)
  ok   after the key is replaced, the service is tried again and clears itself
== account setting blocks free models (OpenRouter privacy) -> clear message, nothing marked unusable
  ok   [blocked] is shown and no model is marked unusable
  ok   the message tells you where to fix it
== a role with no model of its own borrows from the others instead of staying empty
  ok   reviewer borrows picks from other roles
  ok   the report says so in plain words
  ok   the router still has a reviewer group
== when nothing works anywhere, say so (not 'empty')
  ok   exit code 1, clear message, no router list written
== the REAL network code, against a local fake AI service
  ok   --check reports both services as ready
  ok   --check does not list paid models
  ok   --check saves each service's status
  ok   real requests carry the right key for each service
  ok   a model that sends tool arguments as an object (not text) still passes the tool test
  ok   a service with its own address gets api_base in the router list
  ok   second real run: nothing changed, zero new requests
  ok   a '403 forbidden' model is set aside for about a day, not a week
  ok   an unreadable reply (maintenance page) pauses the service instead of marking the model unusable
  ok   a redirect to another site is refused, so a key never leaves for another host
== keys: test, save, replace, remove
  ok   a keys file with quotes and Windows line endings is read correctly
  ok   a refused new key is NOT saved: the old key stays
  ok   a working new key is saved (spaces and newlines stripped)
  ok   the previous keys file is kept as keys.env.bak
  ok   other keys in the file are untouched
  ok   the keys file is readable only by you
  ok   the saved status is updated and any old 'refused' flag is cleared
  ok   removing a key leaves it blank and shows [skip]
  ok   the keys table never shows a full key
  ok   a router password is created once and then kept
== router list is valid
  ok   all three role names are present
  ok   each backup rule is its own entry (LiteLLM reads only the first key of each)
  skip LiteLLM checks (litellm is not installed in this Python)

selftest passed
```
