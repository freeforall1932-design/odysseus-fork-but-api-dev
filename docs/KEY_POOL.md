# Key rotation (multi-key provider pools)

Odysseus already accepts one API key per endpoint. A **key pool** adds the
other keys you own for the *same* provider, so a rate limit or an empty quota
does not end the conversation: the server retries the very same turn on the
next healthy key and the chat carries on from the same place.

This is the "orchestrator" part of bring-your-own-key: one route, many
credentials, one continuous conversation.

## What it does

| Situation | Before | With a pool |
|---|---|---|
| Key hits `429` on a chat turn | error event / fallback to another *model* | same model, next key; before the first token the request simply restarts |
| Key's quota is spent (`402`, or `403` + "insufficient_quota") | error | next key picks up; the exhausted key rests 30 minutes |
| Key is invalid (`401`) | error | that key rests an hour, the request moves on |
| Provider outage (`5xx`, timeout) | host cooldown | unchanged — switching keys would only burn the next quota |
| Extra key added later | edit the endpoint, break the running chat | added live, no restart, no endpoint edit |

Failover is **seamless in two cases**:

* nothing has been shown yet — the request is re-run on the next key;
* the answer stopped mid-sentence — the partial text is sent back as an
  assistant prefix, so the next key *continues where the last one stopped*
  instead of regenerating the answer. The user sees one continuous reply.

Exactly the text already on screen is pre-filled (no trimming), because a
trimmed prefix would make the model repeat the half-written word. A partial
**tool-call** stream is never spliced — restarting it would double-execute
tools — so that case surfaces the error and lets the foreground fallback policy
decide. Continuations are capped at three per request.

## Shared memory

There is no second memory store to keep in sync. The conversation — messages,
tool results, files, the session row — belongs to the session, not to the key.
Rotation only swaps the credential underneath the same request, so the next key
receives the identical transcript. That is why a swap mid-conversation reads as
"nothing happened" rather than "another assistant joined".

## Using it

**From the UI** — model picker → *API key* (provider hub) → **Connect** →
**API key rotation (pool)**: pick the endpoint, paste an extra key, optionally
label it. The list shows each credential masked, with its live health
(`cooling 42s (429)`, `ok`, `2 failures`). *Reset cooldowns* clears the rests
after you top up a provider quota.

**From the API** (admin only, like every endpoint route):

```bash
GET    /api/providers/keys?endpoint_id=<id>        # masked keys + health
POST   /api/providers/keys                          # {endpoint_id, api_key, label?, priority?}
DELETE /api/providers/keys/<key_row_id>
PATCH  /api/providers/keys/<key_row_id>             # {is_enabled: false}
POST   /api/providers/keys/reset?endpoint_id=<id>   # forget cooldowns
```

## Where the keys live

* Table `provider_keys` (`core/database.py`): `api_key` is `EncryptedText`
  (Fernet, same as every other credential), `key_fingerprint` is a SHA-256
  lookup id, and `priority` decides the preference order.
* The endpoint's own `ModelEndpoint.api_key` is the **first** member of its
  pool — existing single-key endpoints keep working with no migration, and a
  pool row is purely additive.
* Keys are never logged, never returned to the browser (only `sk-abc…1234`)
  and never written to the session row.

## Rotation policy

1. Healthy keys first, ordered by `priority`, then least-recently-used — equal
   priorities round-robin under load, so a pooled key that has never been used
   is tried before a busy one.
2. A key that failed a *key-scoped* status rests: `429` for `Retry-After` (or
   60 s), `402`/quota `403` for 30 min, `401` for 1 h. Three consecutive
   provider-wide failures rest a key briefly too.
3. If every key is cooling, the one that recovers soonest is used anyway. A
   stale cooldown must never be the reason a chat cannot start.
4. Health lives in process memory (`src/key_pool.py`), so rotating never writes
   to the database on the chat path; a restart simply gives every key a fresh
   try.

## Where it is wired in

| Seam | Effect |
|---|---|
| `src/endpoint_resolver.resolve_endpoint_runtime()` | every caller (chat, agent tools, skills, research, webhooks, background tasks) gets the next healthy key |
| `src/llm_core.stream_llm()` | pre-first-token `401/402/403/429` restarts on a fresh key; a mid-answer failure resumes from the partial text |
| `src/llm_core.llm_call_async()` | retries immediately with the next key instead of sleeping on the same one |
| `routes/provider_routes.py` | pool CRUD (`/api/providers/keys*`) |
| `static/js/providerHub.js` | pool card in the provider dialog |

## Files

| File | Role |
|---|---|
| `src/key_pool.py` | Selection, cooldowns, rotation, masking, pool summary |
| `core/database.py` | `ProviderKey` table |
| `src/endpoint_resolver.py` | Pool-aware `resolve_endpoint_runtime` |
| `src/llm_core.py` | Stream continuation + non-stream rotation hooks |
| `routes/provider_routes.py` | Pool CRUD routes |
| `static/js/providerHub.js` | Pool card, `poolKeyLabel` helper |
| `tests/test_key_pool.py` | Policy, selection, headers, streaming retry |
| `tests/test_provider_keys_routes.py` | Route layer |
| `tests/test_provider_hub_chatbox_js.py` | `poolKeyLabel` under Node |

## Verification

```bash
.venv/bin/python -m pytest -q tests/test_key_pool.py tests/test_provider_keys_routes.py \
  tests/test_provider_hub_chatbox_js.py tests/test_endpoint_resolver_headers.py \
  tests/test_llm_core_fallback.py
```

Everything is mocked: the suite proves the rotation contract, not that a
particular provider's quota page agrees.

## Not in this change

* Auto-tuned key weights from measured latency (priority is manual today).
* Cross-process pools (a second Odysseus worker keeps its own cooldowns).
* Key health persistence across restarts (deliberate: see the policy above).
* Multi-agent "team" orchestration (architect / implementer / reviewer roles).
  Planned next, modelled on ChatDev: roles run in sequence over one shared
  brief, and their notes go into Odysseus's existing memory/RAG store rather
  than a parallel one.
