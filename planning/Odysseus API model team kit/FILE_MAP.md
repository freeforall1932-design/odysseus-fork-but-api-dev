# AI Team Kit — file map and extraction record

This is the “where is everything?” file. It replaces the old snapshot's
`FILES.md` as the current map, while the original snapshot is preserved in the
archive.

All paths below are relative to `workbench/projects/ai-team-kit/` unless they start
with `~/` or say “repo root”.

---

## 1. Current folder at a glance

```text
workbench/projects/ai-team-kit/
├─ README.md                         Start here: status, reading order, verdict
├─ SESSION_HANDOFF.md                Current state and exact next-session gate
├─ WORKLIST.md                       One actionable queue (audit + old T1–T10)
├─ PROJECT_CONTEXT.md                Goal, architecture, decisions, old-chat intent
├─ RESEARCH_AND_OPEN_QUESTIONS.md    Findings, dated claims, Q/A status
├─ READING_GUIDE.md                  Section-by-section owner reading summary
├─ FILE_MAP.md                       This map + extraction/deletion record
├─ ODYSSEUS_SOURCE.md                Pinned pointer to the separate Odysseus repo
├─ kit/harness/                      Extracted canonical v1 kit (edit only in a named code task)
├─ reports/
│  ├─ KIT_LEARNING_AND_CHAT_MATCH.md What v1 does + old-chat match + one self-test
│  ├─ CODE_AUDIT_2026-10-17.md       Static audit findings and fix order
│  ├─ OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md
│  │                                 Owner's old-chat requests, extracted + reconciled
│  └─ FREE_PROVIDER_RESEARCH_2026-10-18.md
│                                    W-020: free tiers/terms/limits, officially verified
└─ archive/
   ├─ 2026-10-16-handoff-snapshot/   Original HANDOFF/PROVEN/OPEN/FILES
   ├─ 2026-10-17-next-session-readme.md
   │                                 Former all-in-one README, kept as history
   └─ harness-zip-extras/            Four documents only in the non-canonical zip
```

There are **no zip files left at the top level**. The next distributable zip
should be generated from `kit/harness/` only in the future repackage task
(W-080), after code/guide changes and tests.

---

## 2. Which current document should I open?

| Need | Open |
|---|---|
| “Where are we and what do I do next?” | [`README.md`](README.md), then [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md) |
| “What work remains?” | [`WORKLIST.md`](WORKLIST.md) |
| “Explain every section I need to read.” | [`READING_GUIDE.md`](READING_GUIDE.md) |
| “Why does this project exist and how do parts fit?” | [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) |
| “What did research find, and what is still unknown?” | [`RESEARCH_AND_OPEN_QUESTIONS.md`](RESEARCH_AND_OPEN_QUESTIONS.md) |
| “What does the delivered kit actually do?” | [`reports/KIT_LEARNING_AND_CHAT_MATCH.md`](reports/KIT_LEARNING_AND_CHAT_MATCH.md) |
| “What is broken, risky, or missing in code?” | [`reports/CODE_AUDIT_2026-10-17.md`](reports/CODE_AUDIT_2026-10-17.md) |
| “Which free providers/models are real, and what are their limits?” | [`reports/FREE_PROVIDER_RESEARCH_2026-10-18.md`](reports/FREE_PROVIDER_RESEARCH_2026-10-18.md) |
| “What did I originally ask for in the old chat?” | [`reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md`](reports/OWNER_INTENT_FROM_OLD_CHAT_2026-10-18.md) |
| “Where is Odysseus?” | [`ODYSSEUS_SOURCE.md`](ODYSSEUS_SOURCE.md) — a pointer to a separate repo, not a copy |
| “I want the original snapshot wording.” | `archive/2026-10-16-handoff-snapshot/` |

---

## 3. Canonical v1 kit: `kit/harness/`

These 16 files are byte-for-byte the members of the delivered
`ai-team-kit.zip`, with only the outer `harness/` prefix kept as the folder
name in the repo. They were not code-edited during extraction, the audit, or
this reorganisation.

| Repo path | Bytes | Mode | Purpose |
|---|---:|---:|---|
| `kit/harness/GUIDE.md` | 41,293 | 0644 | Beginner setup/use guide; canonical guide copy |
| `kit/harness/README.txt` | 981 | 0644 | Short kit contents and quick start |
| `kit/harness/harness.sh` | 28,164 | 0755 | Main `harness` command |
| `kit/harness/harness_ui.py` | 77,152 | 0644 | Local dashboard server and page |
| `kit/harness/install.sh` | 7,060 | 0755 | One-time installer |
| `kit/harness/model_scout.py` | 83,687 | 0644 | Model picker and its built-in self-test |
| `kit/harness/mac/Start AI Team.command` | 190 | 0755 | Mac start launcher |
| `kit/harness/mac/Stop AI Team.command` | 138 | 0755 | Mac stop launcher |
| `kit/harness/skills/self-extend/SKILL.md` | 3,076 | 0644 | Helper instructions for safely finding/adding missing abilities |
| `kit/harness/skills/team-workflow/SKILL.md` | 3,587 | 0644 | Helper instructions for handoff/worklist/log discipline |
| `kit/harness/skills/team-workflow/templates/HANDOFF.md` | 307 | 0644 | Small project handoff template (not the archived snapshot) |
| `kit/harness/skills/team-workflow/templates/IMPROVEMENT_LOG.md` | 125 | 0644 | Improvement-log template |
| `kit/harness/skills/team-workflow/templates/WORKLIST.md` | 338 | 0644 | Worklist template |
| `kit/harness/skills/team-workflow/templates/worker-prompt-extension.md` | 655 | 0644 | Prompt note telling workers to use project memory files |
| `kit/harness/windows/Start AI Team.bat` | 776 | 0644 | Windows/WSL start launcher |
| `kit/harness/windows/Stop AI Team.bat` | 452 | 0644 | Windows/WSL stop launcher |

Full SHA-256 values for every member are in the learning report, Appendix A.
The guide formerly duplicated at `AI-Team-Setup-Guide.md` had the same
SHA-256 as `kit/harness/GUIDE.md`:
`f2d64d7fbca319f9259eadb3e34b776b226291597e72c89ef34bd682c4077ce7`. The
duplicate was removed so there is one guide to edit in a future guide task.

> The extracted tree is source in this repo. It is **not** an installed
> `~/harness`; its guide/scripts still describe the delivered install flow.
> Do not run the installer from here unless a future owner-named task says to.

---

## 4. Archive: what was preserved and why

### `archive/2026-10-16-handoff-snapshot/`

| File | Original role | Current distilled home |
|---|---|---|
| `HANDOFF.md` | Coverage, goal, cutoff state, T1–T10, constraints, opening message | `SESSION_HANDOFF.md`, `WORKLIST.md`, `PROJECT_CONTEXT.md` |
| `PROVEN.md` | Decisions, rejected options, OAT/router/test/add-on findings | `PROJECT_CONTEXT.md`, `RESEARCH_AND_OPEN_QUESTIONS.md` |
| `OPEN.md` | Blocked work, Q1–Q13, assumptions A1–A11 | `WORKLIST.md`, `RESEARCH_AND_OPEN_QUESTIONS.md` |
| `FILES.md` | File inventory and upload matrix as of the snapshot | This file map |

These originals are kept byte-for-byte as evidence and wording history. They
are snapshots, not current instructions. In particular, their decision IDs
overlap with IDs used in the former README; the new context file avoids those
ambiguous IDs.

### `archive/2026-10-17-next-session-readme.md`

The former all-in-one `README.md` from the restart/learning tasks. It is kept
because it contains the detailed 2026-10-17 session log and discrepancy
history. New sessions should start from the slim current `README.md`, not
from this archive copy.

### `archive/harness-zip-extras/`

These four files existed only in `harness.zip`. They are preserved because
they explain provenance, but none is current kit code or a current guide:

| File | Bytes | Classification |
|---|---:|---|
| `GIFSCYTHE_PLANNING_REPORT.md` | 9,480 | Gifscythe planning context; useful only for Gifscythe-side work, not kit runtime evidence |
| `draft query that need refinement.txt` | 1,961 | Draft prompt that generated the four snapshot files; explains their snapshot nature |
| `gifscythe-ai-team-setup-guide.md` | 32,799 | Earlier superseded guide; do not use instead of `kit/harness/GUIDE.md` |
| `gifscythe-independent-review.md` | 13,631 | Source-only Gifscythe review at a pinned Gifscythe commit; not a kit test |

---

## 5. Extraction and zip-deletion record

### Original archives (now deleted from the working tree)

| Archive | Bytes | SHA-256 | Members | Disposition |
|---|---:|---|---:|---|
| `ai-team-kit.zip` | 83,953 | `aea5c8df14ecf11e47fd4ca85f16f6b5a64e5d029c8d6e093dfdd68d15adf73e` | 16 | Canonical delivered v1; extracted to `kit/harness/` |
| `harness.zip` | 108,680 | `d1e0b3b83bd6b95c3eb761825e0c06a443f051d8fb383ca259e8ae526203b1cd` | 20 | Non-canonical superset; common 16 represented by `kit/harness/`, extras extracted to `archive/harness-zip-extras/` |

Extraction rejected unsafe paths/symlinks, preserved executable bits, and
rechecked that all 16 common members were identical. The zips were removed
only after the extracted trees and this record existed.

Git history on the session branch still shows the earlier commits that added
the zips; the current source of truth for future edits is the extracted tree,
not a zip. A future release zip should be regenerated deterministically from
`kit/harness/` and given a fresh hash in W-080.

---

## 6. Runtime files on the owner's machine (never commit)

These paths are created or used when the kit is installed/run. They are not
part of the repo source, and several contain secrets:

| Path (on the installed machine) | Contains | Rule |
|---|---|---|
| `~/.config/gifscythe-harness/keys.env` and `.bak` | Provider keys and LiteLLM master key | Never upload/commit/paste |
| `~/.config/gifscythe-harness/ui-token` | Dashboard access token | Never share |
| `~/.config/gifscythe-harness/ui-chat.json` | Local dashboard chat markers/history | Private runtime data |
| `~/harness/scout_state.json` | Provider status, catalog cache, probes, picks, key fingerprints | Generated; do not commit as source |
| `~/harness/scout_report.md` | Last model-picker report | Generated |
| `~/harness/scout.yaml` | Optional user scout settings | Review before sharing; may reveal endpoints |
| `~/.litellm/config.yaml` | Generated router model list; references key env names | Generated |
| `~/harness/litellm.pid`, `ui.pid`, `litellm.log`, `ui.log` | Process IDs and logs | Runtime only |
| `~/.oat/config.toml` | OAT provider config including router master key | Secret-bearing |
| `~/.oat/.env` | OAT startup key/base URL and optional Tavily key | Secret-bearing |
| `~/.oat/state.json`, `~/.oat/repos/`, `~/.oat/output/` | OAT repos, agents, worktrees, and logs | Runtime data; may contain project content |
| `~/.agents/skills/` | Installed skills | Installed state, not this repo's source |
| Future `mcp.json` locations from the old plan | Intended MCP server list | Not in v1; treat as sensitive config if rebuilt |

---

## 7. Missing, lost, or not-yet-written files

Confirmed absent from both delivered zips and from the extracted tree:

| File/feature | Status |
|---|---|
| Patched `model_scout.py` with writer/editor, `only_roles`, endpoint presets, `--list-services`, `--add-endpoint` | Reported written in old sandbox, never presented; rebuild only in W-030 |
| `mcp/oat_mcp_loader.py` | Reported written/tested in old sandbox, never presented; rebuild only in W-040 |
| `mcp/oat_mcp_apply.py` | Reported written/tested in old sandbox, never presented; rebuild only in W-040 |
| `toolchains.sh` | Planned, never written; W-060 |
| Dashboard/MCP test files (`run_tests.py`, `dom_test.js`, fixtures, fake router/provider/OAT/GitHub binaries) | Sandbox-only in old chat; recreate in W-016/W-032/W-040 as needed |
| Odysseus program files | Deliberately not copied; use `ODYSSEUS_SOURCE.md` pointer |
| `gifscythe-guardrails/SKILL.md` | Guide text for a Gifscythe-side skill; not a delivered kit file |
| A current release zip | Deleted old zips after extraction; regenerate only in W-080 |

---

## 8. Guide lineage (so old names do not confuse a future session)

The setup guide had several names for one lineage:

1. `gifscythe-agent-harness-plan-v2.md` — earlier rewritten plan, superseded;
   not in this repo.
2. `gifscythe-ai-team-setup-guide.md` — earlier guide, preserved only as a
   `harness.zip` extra.
3. `AI-Team-Setup-Guide.md` — delivered separate guide name; removed here as a
   duplicate.
4. `kit/harness/GUIDE.md` — **current canonical guide in this repo.**

When W-070 updates the guide, edit `kit/harness/GUIDE.md` and keep the former
download name only as a release/export name if the owner wants it at
repackage time.
