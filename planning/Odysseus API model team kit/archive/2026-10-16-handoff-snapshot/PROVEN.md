Snapshot as of 2026-10-16
Project: Gifscythe AI team harness (OAT agent team + LiteLLM router + model picker + browser dashboard + install kit) for freeforall1932-design/gifscythe

## Decisions (user-confirmed or user-stated)
- D1. Free tiers only, cloud APIs only (no local models like Ollama/LM Studio); user is middleman who reviews/merges PRs. Evidence: stated in the user's pasted session handoff doc.
- D2. Setup guide must be step-by-step, beginner wording, v1 flaw notes only at the very bottom. Evidence: user's explicit request ("put it at the very bottom", "beginner friendly").
- D3. Deliver documents as downloadable files, not artifact links. Evidence: user's saved preference shown in the chat context.
- D4. Odysseus runs natively, no Docker. Evidence: user answered "Native" to the assistant's Docker question.
- D5. Auto-merge helper stays off; nothing merges unless the user presses Merge. Evidence: user's middleman requirement (D1 source); `oat init --no-merge-queue` used in harness add-repo.
- D6. MCP is wanted. Evidence: user wrote "MCP also". [unsure: the assistant read it as MCP for the OAT pull-request team too; user did not confirm]
- D7. Paced model testing: one model at a time per service with a pause, biggest/most-used first; refused keys shown as skipped/offline-style, not silent. Evidence: user's explicit requests, implemented and tested (see findings).

## Rejected or dropped (with reason)
- llm-keypool: flag is --capabilities and `nvidia` is rejected (ran its CLI); LiteLLM already rotates/fails over (tested). OmniRoute: not needed once LiteLLM is used. Claw Orchestrator: wraps paid coding CLIs and overlaps OAT (npm description read).
- v1 installer URL oat.ibert.me: belongs to a different project (search result).
- Multi-key rotation on OpenRouter: extra accounts/keys do not raise limits (OpenRouter docs).
- Colab/KoboldCpp as a core source: Google's Colab FAQ disallows web-service offerings and remote proxies on all runtimes, and web-UI use on free tier (FAQ via search).
- AI Horde for tool-using coding roles: its OpenAI-compatible proxy has no tools/functions/streaming/structured output (horde-openai-proxy README).
- Docker for Odysseus: user chose native (D4). Docker version of the kit: never built.
- Reversed: parallel quick-testing of models replaced by paced one-at-a-time with rest (D7); `--dry-run --probe` spending requests replaced by "dry run spends nothing"; role "EMPTY" replaced by borrowing from other roles or "UNAVAILABLE".

## Findings: OAT (agent team)
- Real installer is Root-IO-Labs/open-agent-teams raw GitHub script; pinned v0.1.0 installs in a clean home (ran it; `oat version` printed 0.1.0).
- No `oat task` command and no --role flag (ran `oat task --help`: unknown; source grep).
- OAT_MODEL_ENDPOINT / OAT_MODEL_API_KEY do not exist (source grep). Custom provider via ~/.oat/config.toml with langchain_openai works: create_model reached a mock endpoint with the alias model name (ran).
- `oat init` fails without some provider key in env or ~/.oat/.env; writing the router password there lets it proceed to cloning (ran twice).
- `oat init` accepts --no-merge-queue (source line shown); `oat repo use`, `oat list`, `oat agent tell <agent> <text> --repo` exist (help output). State is in ~/.oat/state.json (struct fields read).
- Empty model-profile store means no model validation; after any onboarding every model must be onboarded and eligible (source read).
- Agents start with --auto-approve (source). Windows is "not tested" per README. OAT TUI and non-interactive both use agent.astream (grep).
- Skills load natively from five directories incl. ~/.agents/skills and <repo>/.agents/skills; test skills loaded via OAT's loader (ran).
- Daemon started by `harness start` had zero AI-key variables in its environment (checked via /proc).

## Findings: router, keys, passwords
- LiteLLM fallbacks written as one dict with several keys: only the first key is honored (ran with LiteLLM 1.103.2). Separate dicts fixed it. Priority `order` fails over to order 2 when order 1 is dead, and the dead one cools down (ran).
- LiteLLM listens on 0.0.0.0 by default (source). Weak master keys "1234"/"word" are accepted; empty one is not usable; unauthenticated request returned HTTP 500 in the sandbox (ran).
- Ubuntu passwd: empty refused; "1234" and "word" accepted (ran).
- OpenRouter docs: free models 20/min; 50/day under $10 purchased credits; 1,000/day at $10+; threshold counts credits purchased all time. Terms excerpts: may change features/limits any time, credits non-refundable after 24h, right to expire credits after 365 days (search results; user told to check openrouter.ai/terms).
- OpenRouter models API fields used by the scout (supported_parameters, pricing, expiration_date, architecture.output_modalities, created) match the docs; `sort=top-weekly` is documented.
- Codespaces: ~120 core-hours/month and 15 GB for personal free accounts, 30-minute idle timeout, 30-day retention, $0 default spending limit (docs/search results).

## Findings: tests that passed (shown in chat)
- model_scout.py (kit version): selftest 68 checks pass on Python 3.12, 3.10, 3.14; includes a real-network test against a local fake provider and real LiteLLM Router checks.
- harness_ui.py: 84 checks pass (63 server + 21 page checks via jsdom).
- Fresh install from the zip into a new home worked; fully fresh router install worked (LiteLLM 1.104.1) and selftest passed with it.
- `harness open` started router, OAT daemon and dashboard with fakes; stop shut them down. Key flows (refused key keeps old key, replace makes a .bak, remove) worked against a fake provider.
- Delivered: AI-Team-Setup-Guide.md and ai-team-kit.zip (presented).

## Findings: add-on research and builds (this phase)
- Odysseus (odysseus-dev/odysseus): AGPL-3.0-or-later (README); native install ran: pip install -r requirements.txt succeeded, uvicorn on 127.0.0.1:7011 answered HTTP 302; log showed ChromaDB memory store unreachable natively; no "mcpServers" handling in source, MCP is managed through its own /api/mcp routes; a Group chat feature exists in source; agent mode built on OpenCode (search excerpt); no release tags, default branch dev, tested commit a8c147b.
- AI Horde: official OpenAI-compatible proxy at oai.aihorde.net; converter has no tools/functions/seed/streaming/structured output; kudos priority; anonymous key lowest priority; volunteers process text (search + README fetch).
- The Agency (msitarzewski/agency-agents): 147+ persona Markdown files in 12 divisions incl. game development and design; convert script outputs SKILL.md; OpenCode install reportedly caps around 119 agents (search results).
- OpenCode (MIT; MCP, subagents, `opencode web`) and Goose (MCP-native) exist (search results).
- Qt6: Ubuntu 24.04 packages Qt 6.4.2, CMake 3.28.3; a tiny CMake project built and its QtTest passed headless with the offscreen platform (ran). dotnet-sdk-8.0 installs; the C# build failed only because the sandbox could not reach NuGet (error shown).
- MCP for OAT: loader skips a broken server and loads working ones; apply is idempotent on a fresh OAT install; a stand-in model calling an MCP tool through OAT's create_cli_agent returned the result in both async and sync runs; real mcp-server-fetch loaded one tool (with a TLS workaround needed only in the sandbox). Preset packages exist on npm/PyPI (npm view / PyPI check shown).
- OpenMAIC (THU-MAIC) search results: open-source interactive-classroom platform; no opinion given yet (see T2).
