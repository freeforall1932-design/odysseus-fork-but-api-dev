---
layout: default
---

# Providers, Auto pool and Council

Adds three things on top of the existing endpoint / chat / skills code. Nothing existing was replaced.

| Piece | Files |
|---|---|
| Provider onboarding (pick provider, paste key, models are fetched) | `src/provider_presets.py`, `routes/provider_routes.py` |
| Auto mode (saved pool + router model, keep-local) | `src/auto_router.py`, `routes/auto_routes.py` |
| Council (fan-out, debate, verify) | `src/council.py`, `routes/auto_routes.py` |
| UI (one modal, three tabs) | `static/js/providerHub.js` (chat routing hints in `chat.js`, 1 tag in `index.html`, 1 entry in `sw.js`) |

Open it from the model picker: **API key** button (Connect), **Pool** and **Council** buttons, **Auto** and **Keep local** switches.

## Connect
`POST /api/providers/models {provider, api_key}` lists the chat models a key can use. It never saves anything.
Saving goes through the existing `POST /api/model-endpoints` with the ticked models as `pinned_models`, so key
encryption, the picker and Docker loopback handling behave exactly as when an endpoint is added by hand.

Presets: OpenRouter (free models detected from pricing; key checked with `GET /key` first), Google Gemini, OpenAI,
Anthropic, Groq, Mistral, DeepSeek, Together, Cerebras, NVIDIA NIM, xAI, Hugging Face, Ollama, LM Studio, and a custom
OpenAI-compatible URL. A cloud preset always talks to its own fixed address; only local/custom may override it.

## Auto
`PUT /api/auto/pool` stores the pool (max 60) and settings in the existing per-user prefs store.
`POST /api/auto/route {message, has_image?, needs_tools?, keep_local?, exclude?}` returns `{endpoint_id, model, reason, source}`.
The router model sees a numbered list of the pool and answers `{"pick": n}`. If it is slow, down, or unreadable,
the configured default is used, or the first eligible pool entry if no default is configured. The chat itself still goes
through the normal `chat_stream`, so streaming, history and skills are untouched, and picking a different model on any
turn already worked (the selected model is sent per message).

**Keep-local is hard.** Candidates are limited to offline models; a cloud router is skipped, so the message text is never
sent to it; with no offline model in the pool the request fails (HTTP 409 / the send is blocked) rather than falling
through to a cloud model. Whether a model is "local" is recomputed server-side from the endpoint address.

## Council
`POST /api/council/run` streams events (`start, draft, member, round_done, chair, done`).
Modes: `fanout` (independent answers, chair merges), `debate` (members read the others, anonymised and shuffled, and
revise), `verify` (a worker, typically an offline model, drafts; the others review it; the chair issues
"accepted as-is" or "corrected"). Personas are optional (`researcher, logician, contrarian, builder` or custom).
Members never vote on each other, the chair is a separate seat, and a failed or declining member is reported, not hidden.
A skill (by name, from your skill library) is injected into the chair by default, or into every member with `skill_scope: all`.
`POST /api/council/plan` returns a rough call/token estimate; debate costs far more tokens than its call count suggests
because each later-round prompt carries everyone's answer.

## What this deliberately does not do
* It never rewrites a prompt to get past a refusal, and never retries a refusal on another model by itself.
  `src/auto_router.answer_with_fallback(on_refusal=True)` exists for non-streaming callers, is off by default and unused.
* A refusal is shown as a refusal. In a council it counts as "declined" and the chair is told.

## Known limits
* Council and router calls are non-streaming; the council UI shows each member as it finishes.
* "Local" is the app's existing endpoint classifier: an endpoint you marked local, or one on a loopback, private-LAN or
  Tailscale address. A server on another machine of yours therefore counts as local even though it is not this computer.
* Refusal detection on text is a heuristic (short replies that open with a refusal phrase). Provider signals
  (`content_filter`, `stop_reason: refusal`) are honoured when a caller passes them.
* Verification catches what the reviewing models know. It does not check citations; check references yourself.

## Tests
`tests/test_provider_presets.py`, `test_auto_router.py`, `test_council.py`, `test_provider_and_auto_routes.py` (175 tests), plus `TestClassifyEndpoint` in `test_model_routes.py` (25 tests; 200 total, no network).
