# AI Team Kit — session handoff

**Status on 2026-10-18:** extraction, repository reorganisation, and a static
code audit are complete; the owner's quota-aware provider-pool/adaptive-council
direction is recorded; the owner's old-chat intent has been extracted; and
**W-020 free-provider research (first pass) is done** from official sources.
**No next build/research task has been named yet.** The next session must stop
at [`WORKLIST.md`](WORKLIST.md) item **W-001** and wait for the owner to name
one item.

> If the owner sends only “next” or “continue”, ask which `W-` item they mean.
> Do not choose one.

---

## 1. What just changed

The owner-named 2026-10-18 documentation task recorded the intended
quota-aware pooling of Google/NVIDIA/OpenRouter/other APIs plus an online
Colab/KoboldCpp session, an Odysseus-centred room intent, and the adaptive
council default.

Three follow-up tasks the owner then named ran in order on 2026-10-18
(documentation/research only, still no council code):

1. **Owner intent extracted** to
   [`reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md`](reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md)
   from the shared old chat's owner messages, and reconciled against v1 and
   the worklist (hidden attachments, including the first plan, are not
   recoverable from the share).
2. **W-015/W-020/W-050 strengthened**: explicit "do not combust on error"
   requirements (Retry-After, bounded counted retries, circuit breaker,
   token caps, quota ledger, chaos tests), a discovery method using the
   owner's `awesome-freellm-apis` fork, and a full signup-requirements
   checklist.
3. **W-020 executed**:
   [`reports/FREE_PROVIDER_RESEARCH_2026-10-18.md`](reports/FREE_PROVIDER_RESEARCH_2026-10-18.md).
   Core eight verified on official pages; Groq is the strongest new free
   candidate; Google/Mistral free use can train on submitted content (see the
   report for specifics and opt-outs); NVIDIA limits are unpublished;
   **Cerebras has no permanent free tier and GitHub Models is retired** — do
   not re-add them from list sites. No account was created and no provider
   was called, so login-only limit numbers (Google/Mistral) remain for the
   owner to read at setup.

After those, the owner asked for this folder to move into
`workbench/projects/` with a new sibling `workbench/projects/kobold-cli/`.
That move is done (relative links untouched; path text updated, pinned URLs
preserved), and kobold-cli's first report dissects the official KoboldCpp
Colab notebook and rules on another model's "missing flags" claims (flash
attention and MMQ are on-by-default, so two claims were rejected; KV-cache
quantization and a generic args field are genuinely absent).

The owner then explicitly asked for a direct Colab test link and a
codebase sweep. That added `workbench/projects/kobold-cli/kobold-cli.ipynb`
plus the one-line `workbench/projects/kobold-cli/COLAB_LINK.txt`, and
`workbench/projects/CODEBASE_SWEEP_AUDIT_2026-10-18.md`. The first custom
notebook failed in the owner's real Colab run with
`FileNotFoundError: /content/kobold-cli`; at the owner's correction it was
then rebuilt from the actual official KoboldCpp notebook, retaining
upstream's download/load/launch cell and changing only coding/API
presets/default settings (plus omitting the silent-audio cell). The
replacement passed local Jupyter execution with stubbed
download/binary commands, but a successful real Colab GPU/model/tunnel
run is still pending. This owner-directed exception does not close
W-021/Q14: Colab terms/limits/runtime evidence is still required before
the endpoint is relied on.

The preceding owner-named 2026-10-17 reorganisation/audit task did the
following:

- Safely fast-forwarded the session branch to the learning-report commit
  `935b179fdf2553dd3cfbd4243a3a9e1ca14b5526` after proving a restored
  untracked copy of the folder was byte-identical to that commit.
- Extracted the canonical 16-file v1 kit from `ai-team-kit.zip` to
  `kit/harness/`, preserving bytes and executable bits.
- Extracted the four documents that existed only in `harness.zip` to
  `archive/harness-zip-extras/`.
- Reassembled the old all-in-one README and the four 2026-10-16 snapshot
  files into:
  - this session handoff;
  - one [`WORKLIST.md`](WORKLIST.md);
  - [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md);
  - [`RESEARCH_AND_OPEN_QUESTIONS.md`](RESEARCH_AND_OPEN_QUESTIONS.md);
  - [`FILE_MAP.md`](FILE_MAP.md);
  - [`READING_GUIDE.md`](READING_GUIDE.md).
- Kept raw history:
  - `archive/2026-10-16-handoff-snapshot/` — original
    `HANDOFF.md`, `PROVEN.md`, `OPEN.md`, `FILES.md`;
  - `archive/2026-10-17-next-session-readme.md` — former detailed README.
- Moved the learning report to `reports/KIT_LEARNING_AND_CHAT_MATCH.md` and
  added [`reports/CODE_AUDIT_2026-10-17.md`](reports/CODE_AUDIT_2026-10-17.md).
- Removed `ai-team-kit.zip`, `harness.zip`, and the duplicate top-level
  `AI-Team-Setup-Guide.md` **after** extraction. The canonical guide is now
  only `kit/harness/GUIDE.md`; the deletion record and zip hashes are in
  [`FILE_MAP.md`](FILE_MAP.md), Section 5.
- Did **not** edit any extracted kit code or guide. Audit findings are
  recommendations in the worklist, not silent fixes.

Branch/PR state changes outside files, so treat GitHub as the source of truth:
this work is on session branch `arena/5bf33a0c-dionysus`, with draft PR #3
intended for owner review. Check `git status`, `git log -1`, and the PR's
current head/checks at the start of the next session.

---

## 2. Current truth in one screen

- **Delivered v1 exists as source** in `kit/harness/`: installer, `harness`
  command, model scout, dashboard, two skills/templates, launchers, guide.
- **Providers in v1:** OpenRouter, NVIDIA, Mistral, Google. Roles:
  architect, implementer, reviewer.
- **Not in v1:** patched creative-roles scout, dynamic endpoints/services,
  MCP files/commands/UI, Odysseus integration/persona room, extra providers,
  Docker, `toolchains.sh`, and delivered dashboard/MCP test harnesses.
- **Audit verdict:** coherent v1, no obvious stub feature, but do not trust a
  real install until the P0 items are addressed or consciously accepted:
  free-status assumptions, installer pinning, secret/helper boundary, shell
  key sourcing, masked OAT failures, stale refresh, concurrent jobs, and
  skill-install symlink handling.
- **Odysseus:** only a pinned source pointer exists
  ([`ODYSSEUS_SOURCE.md`](ODYSSEUS_SOURCE.md), pin `951d57db…`; rechecked
  still at `main` on 2026-10-18). No code was copied, installed, or run.
  Re-check that repo's `main` again before calling the pin current in a
  future session.
- **Owner-confirmed future directions:** MCP for OAT is wanted; Odysseus is
  native rather than Docker *if* chosen. On 2026-10-18 the owner clarified
  the destination as a quota-aware pool spanning Google, NVIDIA,
  OpenRouter/other APIs, and Colab/KoboldCpp while the Colab session is
  online, with an adaptive council (simulated personas → small real council
  → OAT execution) and Odysseus as the intended room surface. None of that
  pool/council behaviour is built. Core-pool provider terms/limits were
  verified in W-020 (2026-10-18); Colab terms/limits remain W-021/Q14
  research, and second-wave list providers remain W-022 leads.

---

## 3. Evidence carried forward — and its limits

### Verified in the restart/audit sessions

- Zip inventories and member hashes; 16/16 common files identical between the
  two zips; the top-level guide was identical to the in-zip guide.
- Extraction into the repo preserved the canonical/extras bytes and modes.
- Both Python files AST-parse; both shell scripts pass `bash -n`; dashboard
  inline JavaScript passes a syntax check.
- Guide commands, shell dispatch, dashboard routes, and job actions were
  cross-checked statically.
- The delivered model-picker self-test was run **exactly once** on
  2026-10-17 under isolated scratch `HOME`/`TMPDIR`: Python 3.11.2, exit 0,
  **62 passed, 0 failed, empty stderr**, with LiteLLM Router checks skipped.
  Full output is in the learning report, Appendix B.
- W-020 (2026-10-18): official pricing/limits/terms pages for the core eight
  providers were read and dated in the research report; the discovery-list
  fork was pinned (`fadce14…`) and confirmed in sync with upstream. This is
  documentation evidence about *offers and rules*, not a runtime test.

### Not tested here

- The installer, LiteLLM proxy, OAT daemon/agents, dashboard server/browser
  flow, real provider accounts/models, real GitHub token/PR/Merge/Close,
  Windows/WSL, macOS, Codespaces, Odysseus runtime, MCP, and Docker.
- Anything behind a provider login (W-020 was desk research on official
  public pages: no signup, no API key, no provider call), Colab/KoboldCpp
  terms and behaviour (W-021/Q14), and every second-wave list provider
  (W-022).
- Any audit fix—none has been implemented yet.

Do **not** rerun the scout self-test just to “check the baseline”. Rerun it
only inside a named task that changes the scout or its environment, and
report that new run exactly.

---

## 4. Exact next gate

1. Owner reviews the reorganisation, preferably through
   [`READING_GUIDE.md`](READING_GUIDE.md), then decides the draft PR's fate.
   Agents do not merge it.
2. Owner names **one** worklist item (for example `W-010`, `W-020`, `W-021`,
   or `W-050`).
3. The next agent does only that item, updates the worklist/handoff in the
   same session, and reports tested/not-tested.

Recommended order is in `WORKLIST.md`, but a recommendation is not permission.

---

## 5. Start-of-session checklist for the next agent

1. Obey the repo/workbench instructions that are actually in force for the
   checkout; record branch, HEAD, and `git status` before editing.
2. Fetch/sync carefully. This workspace has previously been restored at an
   old base with the whole kit folder untracked: **never reset blindly**.
   Compare unexpected untracked files to the remote branch blobs first, back
   them up in scratch if needed, then fast-forward only when proven safe.
3. Read `README.md`, this handoff, and the top of `WORKLIST.md`. Then read
   only the topic/report files the named task needs.
4. For “what does code do”, read the real file in `kit/harness/` before
   editing. For “what should happen”, the owner's latest instruction wins.
5. Keep changes inside `workbench/projects/ai-team-kit/` unless the named task says
   otherwise. Never touch upstream `assets/` or `dotfiles/`.
6. Before finishing a workbench change, run the repo gate from inside
   `workbench/` (`python3 skills/validate_skills.py`), inspect `git diff`,
   and state exactly what was and was not tested.
7. If updating draft PR #3's title/body, `gh pr edit` previously failed with a
   Projects-classic GraphQL error and could appear to do nothing. Use a REST
   `PATCH` via `gh api repos/.../pulls/3` and read the PR back. Do not merge
   unless the owner explicitly instructs it.

---

## 6. Safety reminders

- Never commit or paste API keys, GitHub tokens, `keys.env`, dashboard tokens,
  OAT config/env files, runtime state, logs with secrets, or private chats.
- Read installer/download code before running it; W-011 exists because v1 is
  not sufficiently pinned.
- Helpers run commands as the install user. Treat skill repos, MCP servers,
  and agent shell access as code execution, not as harmless text.
- Terms/licences come before using a provider, persona pack, skill, or
  third-party code. In particular, do not rely on the owner-directed Colab
  test notebook as pool infrastructure until Q14/W-021 has checked the
  current official terms and any tunnel exposure. The rebuilt notebook is
  an upstream-based adaptation, not Colab-runtime proof.
- The owner reviews and merges pull requests. No auto-merge assumption.
