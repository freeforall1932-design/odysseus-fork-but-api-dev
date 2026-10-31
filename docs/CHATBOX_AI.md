# Chatbox AI provider

Odysseus can use a **Chatbox AI subscription** (`chatboxai.app`) as a model
provider, alongside bring-your-own API keys. Paste the license key once; the
server activates it, stores it encrypted, lists the plan's chat models, and
routes calls through Chatbox's gateways.

This is API compatibility only. No Chatbox code is bundled, and Chatbox
accounts, billing and model access remain theirs.

## What you get

| Piece | Behaviour |
|---|---|
| Provider preset | **Chatbox AI** in the provider dialog (`src/provider_presets.py`) |
| License activation | `POST /api/license/activate`, then `GET /api/license/detail/realtime` |
| Model catalog | `POST /api/chatbox_ai/model_list` (falls back to `/api/model_manifest`) |
| Chat — OpenAI models | `https://api.chatboxai.app/gateway/openai/v1/chat/completions` |
| Chat — Claude models | `https://api.chatboxai.app/gateway/anthropic/v1/messages` |
| Plan / quota / expiry | Settings → provider dialog card, `GET /api/providers/chatbox/status` |
| Unlink | `POST /api/providers/chatbox/deactivate` (releases the seat, disables the endpoints) |

Gemini-native and OpenAI-Responses models appear in the catalog but are marked
**not supported** and cannot be selected: Odysseus speaks OpenAI chat-completions
and Anthropic Messages today, not Gemini's native API or the Responses API.

The license key on the endpoint is a normal credential, so it also participates in the
[key pool](KEY_POOL.md): if Chatbox rate-limits or the plan quota runs out, Odysseus rotates to
another key on the same endpoint — including mid-answer. See the troubleshooting note below about
which license supplies `Instance-Id`.

## Setup (beginner steps)

1. Get a license key at [chatboxai.app](https://chatboxai.app).
2. In Odysseus, open the model picker → **API key** (the provider hub) → **Connect**.
3. Pick **Chatbox AI**, paste the license key, click **Fetch models**.
   The first fetch activates this server as one device and shows plan, quota
   and expiry above the model list.
4. Tick the models you want and click **Connect**.
5. Odysseus registers up to two endpoints:
   * `Chatbox AI` — OpenAI-compatible gateway;
   * `Chatbox AI · Claude` — Anthropic-compatible gateway.

   Ticked models are pinned to their endpoint, so no `/models` probe runs (the
   gateway catalog is not an OpenAI model list). Both endpoints are added to the
   Auto pool when **Also add to the Auto pool** is kept ticked.

The license key is stored encrypted in the database and is **never returned to
the browser**. The provider dialog only shows a masked form (`cbx1…9f2a`).

## Where the key goes

* Activation, validation, deactivation and license detail: the configured
  Chatbox API origin (default `https://api.chatboxai.app`).
* Chat and tool calls: the gateway base URL saved on the endpoint.
* Header: `Authorization: Bearer <license>` for the OpenAI gateway;
  `x-api-key: <license>` for the Anthropic gateway; plus `Instance-Id` for the
  activated device (needed for per-instance quotas and seat accounting).
* Requests do **not** follow redirects, and the key is never logged, echoed in
  an error, or included in the license-detail JSON that gets stored.

Odysseus sends prompts and tool results to Chatbox's gateway exactly as it
would to any other cloud provider. Treat it as a remote provider: no local-only
data, no secrets in prompts.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `CHATBOX_API_ORIGIN` | `https://api.chatboxai.app` | API origin. Set this if Chatbox gives you a regional/alternate origin. Must be a bare `http(s)://host[:port]` (no path/credentials). |
| `CHATBOX_INSTANCE_NAME` | `Odysseus` | Device name shown to Chatbox when activating. Each server counts as one instance. |

No new Python dependency: the client uses `httpx` (already required).

## Storage and ownership

* Table `chatbox_ai_licenses` (`core/database.py`). `license_key`, `instance_id`
  and the raw detail JSON use the existing `EncryptedText` (Fernet) columns.
* `key_fingerprint` is a SHA-256 lookup id, so request-header building never
  has to decrypt every row. One active license per owner; activating a second
  key marks the first inactive.
* The provider routes are **admin-only**, like every other endpoint-creation
  route. User-owned endpoints still obey the normal owner filter.
* Unlinking calls Chatbox's deactivate endpoint (best effort), deletes the local
  row, and clears the key from + disables the matching `model_endpoints`. A
  failed upstream release is reported as a warning, not silently swallowed.
* Header lookup is process-cached for 5 minutes and never performs network I/O;
  a missing/corrupt row degrades to "no `Instance-Id`" rather than failing a chat.

## Troubleshooting

| Symptom | Meaning / fix |
|---|---|
| "Chatbox AI rejected this license key" | Key is wrong, expired, or the plan was refunded. Check chatboxai.app. |
| Activation succeeds, chat returns 401/403 | The endpoint's key differs from the activated license; reconnect from the provider dialog. |
| "Chatbox AI is rate-limiting requests (HTTP 429)" | Plan quota or rate limit. Wait; the dialog's quota card shows remaining tokens. |
| Device/seat limit on activation | Chatbox limits instances per license. Remove an old device in chatboxai.app, or set `CHATBOX_INSTANCE_NAME` to reuse a name. |
| Gemini/Codex models greyed out | Not supported yet (native Gemini / Responses APIs). |
| Quota card stops updating | `Refresh usage` re-reads `/api/license/detail/realtime`; a 5xx keeps the last cached summary. |
| Chat works but usage is not counted against you | The gateway may attribute a missing `Instance-Id` differently; re-fetch models to re-activate. |
| A second license added to the same endpoint rotates without its seat | Chatbox keeps one active license row per owner, so only the active one supplies `Instance-Id`. Use one license per server for now (WORKLIST B9). |

## Files

| File | Role |
|---|---|
| `src/chatbox_ai.py` | Origin, license, catalog, gateway mapping, encrypted storage, header helpers |
| `src/provider_presets.py` | `chatboxai` preset + discovery adapter and per-gateway variants |
| `routes/provider_routes.py` | `/api/providers/models` (chatbox branch), `/api/providers/chatbox/{activate,status,deactivate}` |
| `core/database.py` | `ChatboxAILicense` model |
| `src/llm_core.py` | Detect the Anthropic gateway; label errors "Chatbox AI" |
| `src/endpoint_resolver.py` | Gateway chat/models URLs, `x-api-key` vs Bearer, `Instance-Id` |
| `static/js/providerHub.js` | License card, plan/quota, unsupported-model badges, per-gateway connect |
| `tests/test_chatbox_ai.py` | HTTP contract, parsing, masking, errors (mocked) |
| `tests/test_chatbox_routing.py` | Provider detection, URLs, headers |
| `tests/test_provider_chatbox_routes.py` | Route layer (activation/status/deactivate/models) |
| `tests/test_chatbox_license_store.py` | Encryption at rest, owner scope, unlink cleanup |
| `tests/test_provider_hub_chatbox_js.py` | Node checks for `connectGroups` / quota text |

## Verification

```bash
pytest -q tests/test_chatbox_ai.py tests/test_chatbox_routing.py \
  tests/test_provider_chatbox_routes.py tests/test_chatbox_license_store.py \
  tests/test_provider_hub_chatbox_js.py
```

The suite mocks Chatbox's HTTP API, so it proves the contract shape, key
handling, routing and storage — **not** that a particular live license works.
A live check needs a real key and network access to `api.chatboxai.app`.

## Not in this change

* A first-party Odysseus-hosted API (this is Chatbox's API, not ours).
* Gemini-native and OpenAI-Responses chat implementations.
* Chatbox image generation, embeddings/rerank, RAG upload, account login
  (email/OAuth) — only the license-key path is implemented.
* Desktop/Android app shells. Odysseus remains a local web server: the Windows
  portable launcher and macOS launcher already open the local URL in your
  browser, and the PWA can be installed from that page.
