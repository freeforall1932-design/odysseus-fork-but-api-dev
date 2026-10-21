Snapshot as of 2026-10-16
Project: Gifscythe AI team harness (OAT agent team + LiteLLM router + model picker + browser dashboard + install kit) for freeforall1932-design/gifscythe

## Blocked work and what is missing
- In-progress files never presented to the user: patched model_scout.py, mcp/oat_mcp_loader.py, mcp/oat_mcp_apply.py. They existed only in the previous sandbox. Blocks T1, T3, T4, T8, T9. [unsure: whether the new chat can see them]
- T1: the creative-roles patch is untested. Known expected selftest breaks: the assertion that a no-tools model (gemma-3-4b) is excluded (no-tools models are no longer filtered out); fake answers and default fake skills lack write/edit; budgets changed (default 32, OpenRouter 16, 8 requests max per model).
- T3: depends on T1 (the --list-services and --add-endpoint options exist only in the unpresented patch).
- T4: `harness mcp` commands and the dashboard MCP card are not written. The loader was tested only through create_cli_agent with a stand-in model, not through a daemon-launched real agent.
- T5: Odysseus commands not written. In Odysseus, providers and MCP servers are added in its web UI (no env-var or mcp.json import); first-run admin is created in the browser; its memory needs a separate ChromaDB service when run natively.
- T6: toolchains.sh not written; installing packages needs an admin user, the helper user has no sudo.
- T7, T8, T9: depend on T1 to T6.
- Unreachable from the sandbox: C# build (NuGet blocked), live AI Horde/Groq/Cerebras/Colab endpoints, real GitHub steps (token login, `oat init` clone, real PRs, Merge/Close buttons), Windows/Mac/Codespace specifics, Docker.
- Earlier unresolved: `oat-agent -n ... -M litellm:implementer` printed nothing and no request reached the mock; the check was done instead by calling create_model directly. [unsure: cause never found]
- Unauthenticated router request returned HTTP 500 in the sandbox (a missing module in the sandbox environment); real-install behavior not seen.
- Pending reply to the user: AI Horde support and the OpenMAIC opinion (T2).
- Requested by the user, not built: a persona/"room" feature in the dashboard (T10), Replit-style "lazy" MCP connections beyond the Connections tab (T4).

## Research questions
- Q1. Does "Native and MCP also" mean MCP for the OAT pull-request team? Matters: decides whether the OAT patch (re-applied after OAT upgrades) is built (T4). Resolve: confirm with the user or proceed with D6.
- Q2. What is OpenMAIC and does it fit (classroom/persona "room", multi-agent)? Matters: the user asked for an opinion (T2). Resolve: read its README and licence; the search result contents were not visible in this chat.
- Q3. How does oai.aihorde.net behave live (base path, model list, context and max tokens, queue time, anonymous key)? Matters: writer/editor source (T3). Resolve: test from an internet-connected machine.
- Q4. Licence of the agency-agents repo. Matters: converting its personas to skills (T10). Resolve: read its LICENSE.
- Q5. Current free limits and terms for Groq, Cerebras, GitHub Models, Cloudflare. Matters: presets (T3). Resolve: check each provider's docs.
- Q6. What the real workspace helper's output looks like in the dashboard Chat tab. Matters: chat usability (T7). Resolve: one real run.
- Q7. Does a real daemon-launched OAT agent load the MCP tools, how long do npx-based servers delay startup, and does an OAT upgrade overwrite the patch? Matters: T4. Resolve: real run after `harness mcp apply`.
- Q8. Odysseus: can providers/MCP be added programmatically (/api/mcp format, admin auth), can ChromaDB run natively, how stable is the dev branch, how risky are its shell tools, how do group chat and personas work? Matters: T5, T10. Resolve: use it in a browser, read routes.
- Q9. Real GitHub flow end to end (fine-grained token, `oat init` clone, PR creation, Merge/Close). Matters: all delivered steps. Resolve: user runs them and reports errors.
- Q10. Does GitHub's remote MCP server accept a PAT for non-Copilot accounts? Matters: the "github" preset (marked experimental) (T4).
- Q11. Route for building/testing the Windows .exe (GitHub Actions windows-latest with the Workflows permission). Matters: Gifscythe worklist items. Resolve: try one workflow via a PR.
- Q12. Does the user want OpenCode as an extra harness, persona presets in the dashboard, or a Docker version? Matters: T10.
- Q13. What happens to the helpers when the WSL Start window is closed? Sources conflicted. Matters: guide advice (T8). Resolve: test on a Windows machine.

## Assumptions treated as true, never verified
- A1. "MCP also" means MCP for the OAT team too (D6).
- A2. Odysseus can use the LiteLLM router as an OpenAI-compatible provider (README-level only).
- A3. Real free models can pass the quick tool-calling tests (only fake providers were tested).
- A4. Base URLs oai.aihorde.net/v1, api.groq.com/openai/v1, api.cerebras.ai/v1 in the unpresented patch were written without checking them in this chat.
- A5. Real services behave like the fake-provider tests.
- A6. WSL keeps running while the Start window stays open (Q13).
- A7. Codespaces figures come from docs plus third-party excerpts.
- A8. agency-agents personas can be converted and installed via the Skills tab.
- A9. The Chat tab can read the workspace helper's log at ~/.oat/output/<repo>/<agent>.log (from source reading; real logs unseen).
- A10. PROVEN.md's OpenMAIC line is based on the search query wording and result titles; the result contents were not visible, so treat it as unconfirmed.
- A11. Odysseus group chat works as a "room" of personas (source shows a Group chat feature; behavior untested).
