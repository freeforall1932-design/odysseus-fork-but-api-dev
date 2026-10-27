Snapshot as of 2026-10-16
Project: Gifscythe AI team harness (OAT agent team + LiteLLM router + model picker + browser dashboard + install kit) for freeforall1932-design/gifscythe

## Files named in the chat
| Name as written | Version | Contains | Status | Upload to next chat |
|---|---|---|---|---|
| ai-team-kit.zip | final delivered (1) | folder harness/ with install.sh, harness.sh, model_scout.py, harness_ui.py, GUIDE.md, README.txt, skills/ (team-workflow with templates, self-extend), windows/ (Start AI Team.bat, Stop AI Team.bat), mac/ (two .command files) | delivered, to be superseded by T9 | always |
| AI-Team-Setup-Guide.md | current (3rd name of the guide) | step-by-step beginner guide, add-ons not yet included, v1 flaw notes at bottom | delivered, update in T8 | T8, T9 |
| gifscythe-ai-team-setup-guide.md | earlier guide | earlier version of the same guide | superseded, removed from outputs | no |
| gifscythe-agent-harness-plan-v2.md | v2 plan | first rewritten plan (flaws, fixes) | superseded, removed | no |
| model_scout.py | kit version (68 selftest checks) | model picker, paced testing, key commands, statuses | delivered inside the zip | T1, T3, T7, T9 |
| model_scout.py (patched) | in-progress | kit version plus writer/editor roles, only_roles, ENDPOINT_PRESETS, add_endpoint, list_services, --list-services, --add-endpoint | in progress, compiles, selftest not updated; never presented | T1 (if the user has it) |
| model_scout.py / model_scout_v2.py | earlier standalone versions | first presented scouts (23, then 34 checks); "model_scout_v2.py" was a working name that became model_scout.py | superseded | no |
| harness.sh | kit version (v3) | harness command: keys, scout, start/stop, open, doctor, ui, add-repo, install-skills, connect-oat | delivered inside the zip | T3, T4, T5, T9 |
| harness.sh | earlier standalone (v1/v2) | first helper script | superseded | no |
| harness_ui.py | kit version (1) | dashboard server plus the page (chat, tasks, files, changes, PRs, models, connections, skills, logs) | delivered inside the zip | T4, T5, T7, T9 |
| install.sh | kit version | installer for router, OAT, harness link, skills, Windows shortcuts | delivered inside the zip | T9 (and T4/T5 if it changes) |
| mcp/oat_mcp_loader.py | in-progress | loads MCP tools from an LM Studio style mcp.json into OAT agents | in progress, tested, never presented | T4 |
| mcp/oat_mcp_apply.py | in-progress | presets, add/remove/list, apply/unapply/status/test for OAT's MCP patch | in progress, tested, never presented | T4 |
| toolchains.sh | planned | admin-user installer for Qt6, CMake, Ninja, g++, xvfb, dotnet-sdk-8.0, clangd, node | not written | no (T6 creates it) |
| skills/team-workflow, skills/self-extend | kit version | skills for project notes and for researching/adding missing abilities | delivered inside the zip | T8, T9 |
| HANDOFF.md, WORKLIST.md, IMPROVEMENT_LOG.md, worker-prompt-extension.md (inside skills/team-workflow/templates) | kit version | templates for the user's project notes | delivered inside the zip | no |
| HANDOFF.md, PROVEN.md, OPEN.md, FILES.md (top level) | this handoff | the four handoff files | written | no (they are the handoff) |
| GIFSCYTHE_PLANNING_REPORT.md | unknown | the user's Gifscythe planning report | user's file; contents not shown in the chat | only for Gifscythe worklist tasks, none in T1 to T10 |
| Session handoff document and the first pasted install plan (no file names) | v1 plan | v1 install steps and the earlier session handoff (shown as pasted text) | superseded | no |
| gifscythe-guardrails/SKILL.md | text in the guide | project rules for Gifscythe, meant to be created in the user's repo via GitHub | not a delivered file | no |
| keys.env (and keys.env.bak) | runtime | the user's saved keys | user's private file; never upload | no |
| scout.yaml | optional | the user's model picker settings | not present by default | no |
| scout_state.json, scout_report.md, ~/.litellm/config.yaml | generated | picker memory, last report, router list | runtime | no |
| ~/.oat/config.toml, ~/.oat/.env, ~/.oat/mcp.json, ~/.config/gifscythe-harness/mcp.json, ui-token, ui-chat.json | runtime | OAT/router connection, MCP list, dashboard secret and chat history | runtime; contain secrets; never upload | no |
| agent.py (OAT runtime file, backup agent.py.aiteam-orig) | OAT 0.1.0 | file patched by `harness mcp apply` | part of the OAT install | no |
| run_tests.py, dom_test.js, setup_fixture.py, stub_router.py, fake_provider.py, mock_llm.py, e2e.py, echo_server.py, bin/oat, bin/gh, bin/harness-stub | sandbox test files | dashboard and MCP test harnesses and fakes | sandbox only, never delivered | T7, T9 would need them re-created |
| /tmp/model_scout_v3_before_creative.py | backup | scout before the creative-roles patch | sandbox only | no |

## Flags
- The guide has three names for one lineage: gifscythe-agent-harness-plan-v2.md, gifscythe-ai-team-setup-guide.md, AI-Team-Setup-Guide.md (also copied into the zip as GUIDE.md).
- model_scout.py and harness.sh each appear in several versions; version labels (v1/v2/v3) are my reading of the chat. [unsure: exact labels]
- HANDOFF.md is also a template file name inside the kit; it is a different file from the handoff HANDOFF.md.
- Contents of GIFSCYTHE_PLANNING_REPORT.md are not visible in the chat.
- The in-progress files (patched model_scout.py, mcp/*) were never presented, so the user may not have them.
