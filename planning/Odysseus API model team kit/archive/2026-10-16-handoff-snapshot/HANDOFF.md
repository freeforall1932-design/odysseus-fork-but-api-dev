Snapshot as of 2026-10-16
Project: Gifscythe AI team harness (OAT agent team + LiteLLM router + model picker + browser dashboard + install kit) for the user's GitHub project freeforall1932-design/gifscythe

## Coverage
- Earliest visible: the user's first message pasting a v1 install plan (OAT + LiteLLM + llm-keypool) and asking for a review/improvement; a session handoff doc follows later.
- Latest visible: "Continue where you left off (also what do you think about openmaic repo)" plus OpenMAIC search results. Many tool results are shown as "[Older tool result cleared]" throughout; assistant reasoning from earlier turns is not visible; file contents are visible only through create_file/patch calls shown in the chat.

## Goal and scope
- Free-models-only, cloud-API-only (no local models), beginner-friendly "AI team" that works on the user's GitHub project through pull requests; user reviews and merges.
- Delivered so far: AI-Team-Setup-Guide.md and ai-team-kit.zip (OAT + router + model picker + dashboard + skills + launchers).
- Now extending: MCP tools for OAT helpers, Odysseus (native) as the "room"/persona chat, more model sources (AI Horde, Groq, Cerebras, Colab-style custom endpoints), creative roles, toolchain installer for Qt6/CMake/C#.

## In progress at cutoff
- My last project request: "Continue where you left off (also what do you think about openmaic repo)". Before it the user said: "Native and MCP also does it support AI horde from community backed models that run on kudos". [unsure: "Native and MCP also" was read by the assistant as: Odysseus native (no Docker) and MCP also for the OAT pull-request team; the user never confirmed this reading]
- Finished in the sandbox (shown by tool output in chat):
  - Research on Odysseus, AI Horde, Colab rules, OpenCode/Goose, The Agency personas, OpenMAIC (see PROVEN.md / OPEN.md).
  - Odysseus native install tested in the sandbox (pip install + uvicorn start, answered HTTP 302).
  - Qt6/CMake build and headless QtTest verified in the sandbox; dotnet-sdk-8.0 installed but the C# build failed only because the sandbox blocks NuGet.
  - MCP for OAT: oat_mcp_loader.py and oat_mcp_apply.py written and tested (loader, apply twice, fake-model agent run async and sync calling an MCP tool, real fetch server loaded).
  - model_scout.py creative-roles patch applied (compiles, ruff clean).
- Half-done: model_scout.py patch not yet tested; its selftest was not updated or rerun. Backup of the pre-patch file was saved in the sandbox.
- Not started: harness.sh changes, dashboard changes, toolchain script, guide update, repackaging, final tests.
- Not yet answered to the user: the AI Horde question (research was done) and the OpenMAIC opinion (search results only).
- [unsure: the in-progress files (patched model_scout.py, the mcp folder) were never presented to the user, so the user probably does not have them; they existed only in the previous sandbox]
- Exact next action: T1.

## To-do list
- T1. Finish the scout upgrade: update model_scout.py's selftest for the creative-roles patch (fake answers and skills for write/edit, replace the "gemma-3-4b excluded" assertion because no-tools models are no longer filtered out, add tests for writer/editor roles, only_roles, add_endpoint, list_services, PROBE_MAX budget), then rerun until it passes. Deps: none. Upload: model_scout.py (patched version if the user has it; otherwise from ai-team-kit.zip, and the patch must be re-applied from OPEN.md/PROVEN.md descriptions). Effort: xhigh.
- T2. Reply to the user's two pending questions: AI Horde support (as a custom OpenAI-compatible text-only source for writer/editor; no tools; privacy) and the OpenMAIC opinion. Deps: facts in PROVEN.md. Upload: none. Effort: low.
- T3. harness.sh: replace the static service list (SERVICES, env_name, nice_name, valid_service) with the scout's --list-services output; add `harness add-endpoint`. Deps: T1. Upload: harness.sh, model_scout.py. Effort: xhigh.
- T4. harness.sh `harness mcp ...` commands (list, add preset, remove, apply, unapply, test, status, edit), help and doctor lines; dashboard API and Connections card for MCP (presets only, no custom commands from the web); tests. Deps: T3 for dynamic services is not required. Upload: harness.sh, harness_ui.py, mcp/oat_mcp_apply.py, mcp/oat_mcp_loader.py (re-create if the user lacks them). Effort: xhigh.
- T5. Odysseus native commands in harness.sh (install at a pinned commit, start/stop/status/info/open on 127.0.0.1:7011, AI keys kept out of its environment) and a dashboard link. Deps: decision D4 (native). Upload: harness.sh, harness_ui.py. Effort: xhigh.
- T6. toolchains.sh for the admin user (qt6, cmake, ninja, g++, xvfb, dotnet-sdk-8.0, clangd, node). Deps: none. Upload: none. Effort: lower.
- T7. Dashboard: roles taken from the model picker state in the Ask tab, labels for writer/editor in Models tab, keys list from enabled services; update run_tests/dom tests. Deps: T1, T3. Upload: harness_ui.py. Effort: xhigh.
- T8. Update AI-Team-Setup-Guide.md (and harness/GUIDE.md copy) with add-on sections: MCP, Odysseus native, AI Horde/Groq/Cerebras/Colab warnings, creative roles, toolchains. Deps: T1 to T7. Upload: AI-Team-Setup-Guide.md. Effort: lower.
- T9. Repackage ai-team-kit.zip, rerun all test suites and the fresh-install test, present guide and zip. Deps: T1 to T8. Upload: ai-team-kit.zip. Effort: lower.
- T10. Open choices for later: persona presets in the dashboard, OpenCode as an extra harness, a Docker version (only if asked). Deps: user decisions (OPEN.md Q-items).

## Constraints and conventions
- Target: the user's project freeforall1932-design/gifscythe. [unsure: the request mentions a "-dev repo, not the original fork"; no such repo is named in the chat]
- User preferences seen in chat: beginner-friendly plain wording with no jargon in the step-by-step; notes about what was wrong in the first plan only at the very bottom; downloadable files (not artifact links); visual spacing in list-style replies; final deliverable replies without extra commentary.
- Free-only, API-only; user chose native (no Docker) for Odysseus.
- Names: command `harness`; folder ~/harness; keys file under ~/.config/gifscythe-harness/; router list ~/.litellm/config.yaml; roles architect, implementer, reviewer (writer, editor added in the unfinished patch); ports router 4000, dashboard 8765, Odysseus 7011; OAT pinned v0.1.0.
- Avoid: running install scripts piped from the internet without reading; AI keys in the helpers' environment; the auto-merge helper; helpers creating tags or releases; claiming anything untested; Colab as a core source; Docker unless asked.
- Honesty rule used throughout: say what was tested and what could not be.

## Opening message for the new chat
I'm continuing a project: a free-model AI team (OAT helpers, LiteLLM router, model picker, browser dashboard, install kit) for my GitHub project Gifscythe. This handoff is a snapshot and may contain errors. First, compare the files I upload with FILES.md and flag any mismatches before anything else. Then wait for me to name a T-number; don't start work on your own. If I send just "next" or "continue" before choosing one, ask me which T-number.
