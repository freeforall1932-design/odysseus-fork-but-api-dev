# Free provider research — W-020 first pass (2026-10-18)

## What this file is

Worklist item **W-020**: verify current free tiers, terms, signup requirements,
and API shapes so that W-015 can stop guessing which models are free, and so the
future quota-aware pool (W-050) has real numbers to pace itself with.

**Research date:** 2026-10-18. Every provider fact below comes from that
provider's own documentation/pricing/terms pages read on that date (URLs in
each section). Free tiers change often — re-check before relying on any number
here, and treat anything marked *not found* as unknown, not as "no restriction".

### Method (and the role of the owner's list fork)

Discovery list: the owner's fork
[`awesome-freellm-apis`](https://github.com/freeforall1932-design/awesome-freellm-apis)
at commit `fadce148a189cd5e53f28e883d408b594099ee44` (2026-10-17), verified
**identical to upstream** `open-free-llm-api/awesome-freellm-apis` at read time
(0 ahead / 0 behind). It claims "511+ free LLM APIs from 30 providers" and is
useful for candidate names, signup/key links, and claimed limits.

It is **not evidence**: its data is synced from a third-party site
(freellm.net), and this pass found it stale or wrong in places (it still lists
Cerebras under "Permanent Free Tiers" months after Cerebras ended its permanent
free tier; xAI appears twice under two names; the Cline row has empty links;
"DeepSeek free" needs checking). Rule used here: **list = lead, official page =
proof.** Nothing was signed up for and no API key was created or used; limits
that only appear behind a login are marked *login-only*.

Classes used below (the same ones W-015 must encode):

- **Free-tier eligible** — a permanent free offer the owner can use at $0.
- **Free only under conditions** — free today, but with a catch (trial purpose,
  monthly included usage, tiny daily budget, data used for training, …).
- **Metered/paid risk** — trial credits or any path where "free" can silently
  become billing. Default: excluded from the pool.
- **Unknown** — not verified in this pass.

---

## 1. Headline results

| Provider | Class | One-line truth (2026-10-18) |
|---|---|---|
| OpenRouter | Free-tier eligible (conditional daily cap) | `:free` models: 20 req/min, **50/day**, rising to **1,000/day** once ≥10 lifetime credits purchased. Best error/budget signals of the eight. |
| Groq | **Free-tier eligible** | Permanent Free plan, published per-model RPM/RPD/TPM/TPD, no training on customer data. Strongest new candidate. |
| Google Gemini API | Free-tier eligible, per-model | Free tier exists for Flash-class models only; exact limits are login-only and "not guaranteed". **Unpaid use lets Google train on your content.** |
| NVIDIA API Catalog (NIM) | Free only under conditions | No-cost *trial for prototyping*; credits system removed; rate limits **unpublished** (per model/account, shown in account UI). Production use needs a paid licence. |
| Mistral (Studio/La Plateforme) | Free only under conditions | "Free mode": keys with no card + *included monthly usage*; exact limits login-only. Free-mode data may be used for training (opt-out exists); pay-as-you-go must stay off to avoid billing. |
| Cloudflare Workers AI | Free only under conditions | 10,000 Neurons/day free on the Workers Free plan (hard stop). Enough for light/small-model work, not heavy agent loops on 70B models. |
| Cerebras | **Metered/paid risk — exclude** | No permanent free tier since 2026-07: $5 trial credits *after adding a payment method*, expiring after 30 days. |
| GitHub Models | **Gone — remove** | Fully retired 2026-07-30 (playground, catalog, API, BYOK). |

Two old-chat claims are settled by this pass:

- **OpenRouter "$10 → 1,000/day": true today, with fine print.** The daily cap
  is chosen by *lifetime* credits purchased, so spending the balance does not
  drop you back to 50/day; but unused purchased credits may expire 365 days
  after purchase, and the limit policy itself can be changed by OpenRouter.
  Buying credits is also a (small) paid step — the owner's call, not assumed.
- **"Listed in the catalogue" ≠ free** — confirmed everywhere it matters
  (Google and Mistral especially). Audit A-01 stands; Section 10 gives W-015
  an evidence rule per provider instead of `assume_free`.

---

## 2. OpenRouter (delivered)

- **Get a key:** create an account at openrouter.ai, then create a key in
  Settings/Workspace → Keys (list link: `openrouter.ai/workspaces/default/keys`).
  No card needed to start. Credit purchases are $5–$25,000 per transaction.
- **What "free" means:** models whose ID ends in `:free` cost $0. Free-variant
  limits: **20 requests/minute; 50 requests/day** if lifetime purchased credits
  < 10, **1,000/day** at ≥ 10 (granted from 9 to absorb fees/rounding). Limits
  are account-global — extra accounts/keys do **not** raise them (docs say so
  explicitly; also against this project's rules).
- **When free runs out:** `429` with rate-limit headers. A *negative* account
  balance can also block free models with `402`. Nothing silently bills: a
  `:free` request either runs free or errors.
- **Error/budget signals (best in class):** distinct `402` (credit),
  `403` (budget cap), `429` (rate) with `error.metadata.limit_source`,
  sometimes `Retry-After`; `GET /api/v1/key` reports
  `free_model_daily_requests {used, limit, remaining}` — W-015/W-050 should
  read this before long tasks.
- **API shape:** OpenAI-compatible `https://openrouter.ai/api/v1`, Bearer key.
  Tool calling is per-model (`supported_parameters` includes `tools`) — the
  scout already relies on catalogue pricing/`supported_parameters` fields.
- **Data:** OpenRouter does not log prompts/completions by default (metadata
  only) and does not train on them; upstream providers vary — providers that
  log/train are only routed if the account's training toggle allows it; ZDR
  routing can be enforced. Check each chosen `:free` model's provider policy.
- **Suggested guard settings:** 1 in flight; pace to the *daily* cap, not the
  minute cap (50/day is only a handful of agent turns — reserve OpenRouter for
  short calls unless the owner chooses the $10 lifetime-purchase step).
- Sources (read 2026-10-18): `openrouter.ai/docs/api-reference/limits`
  (fetched), `openrouter.ai/docs/faq`, `openrouter.ai/terms` §4.2 (credit
  expiry), `openrouter.ai/pricing`.

## 3. NVIDIA API Catalog / NIM (delivered)

- **Get a key:** free NVIDIA Developer Program account at build.nvidia.com →
  open a model → "Get API Key" (or `build.nvidia.com/settings/api-keys`).
  Phone verification during signup is reported by the list and user reports,
  but was **not** found stated in NVIDIA's own FAQ text — treat as *likely,
  unverified*.
- **What "free" means:** the API Catalog is a **no-cost trial of NIM for
  prototyping, research, development, testing, and learning**; moving an
  application to production requires an NVIDIA AI Enterprise licence. Staff
  posts (official forum, 2025-09-10 / 2025-06-24): the old credit system was
  removed; trial **rate limits vary per model and account and are not
  published** — your maximum shows at the top-right of build.nvidia.com; the
  trial itself has no time limit. Forum users commonly report "Up to 40 RPM"
  in their account UI, but NVIDIA does not promise that number.
- **API shape:** OpenAI-compatible `https://integrate.api.nvidia.com/v1`,
  Bearer `nvapi-…` key. Tool calling depends on the model.
- **Data use:** not verified from official pages in this pass → *unknown*.
- **Suggested guard settings:** no fixed number can be encoded. Default to
  1 in flight and gentle pacing (start ≈6–10 requests/minute), lengthen
  cooldown on every `429`, and add a manual "my account limit" field the
  owner fills from the build.nvidia.com UI at setup (W-015).
- Sources: NVIDIA NIM FAQ (NVIDIA Developer Forums, staff post 2024-09-11,
  still linked as the FAQ), staff replies in forums threads 344567 / 337051.
  The forum itself blocked direct fetching; wording above is from the indexed
  text of those official-forum posts.

## 4. Mistral — Studio / La Plateforme (delivered)

- **Get a key:** Mistral Studio account (console.mistral.ai / admin.mistral.ai)
  → API keys. Docs quickstart: **"Free mode: API access is enabled by default
  with no credit card required. Usage and rate limits apply."**
- **What "free" means:** Free mode includes a **monthly usage allowance**
  within the limits shown on the account's Limits page (per-model requests/second
  + tokens/minute; help pages also describe a tokens/month cap). The exact free
  numbers are **login-only**, so they cannot be printed here honestly — the
  owner reads them once at setup. Pay-as-you-go, if enabled, extends usage
  beyond the allowance using prepaid credits → **keep it off** for a free-only
  pool, and use the Organization spending-limit feature as a hard stop (docs:
  at the limit, API access is suspended until next month).
- **Per-model warning:** a model appearing in the catalogue is not proof it is
  inside the free monthly allowance. `labs-…`/Preview models are free but
  **always train on your data with no opt-out** (commercial terms) — exclude
  them by default for private code.
- **Data:** Mistral's help centre (2026-08-31): in **Free mode**, input/output
  data may be used to train models; you may opt out (Admin → Privacy). Zero
  Data Retention is pay-as-you-go only.
- **API shape:** `https://api.mistral.ai/v1` (OpenAI-style chat completions,
  as the kit already assumes); function calling on supported models.
- **Suggested guard settings:** local monthly token ledger; 1 in flight;
  treat 429 "tokens per month" as *stop until next month*, not as a cooldown.
- Sources: `docs.mistral.ai/admin/billing-usage/usage-limits` (fetched),
  `docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key`,
  `help.mistral.ai` articles 347617 / 698531 / 455207,
  `legal.mistral.ai/terms/commercial-terms-of-service` (Labs training).

## 5. Google Gemini API / AI Studio (delivered)

- **Get a key:** Google account → `aistudio.google.com/apikey` (creates/uses a
  Cloud project). No card for the Free usage tier ("Active project or free
  trial"). Requirements: **18+**; only in listed available regions; the
  service is positioned for developer/professional use.
- **What "free" means — per model, not per account:** the official pricing
  page has a Free Tier column per model. Flash/Flash-Lite-class models show
  "Free of charge"; others have **no** free API tier (e.g. the Gemini 3
  developer guide states `gemini-3.1-pro-preview` has no free tier in the API;
  image-generation models are not on the Free Tier). The kit's current
  `flash`-only filter points the right way but is not proof for every future
  Flash-named model.
- **Limits:** measured as RPM + input TPM + RPD, **per project** (not per
  key); RPD resets at midnight Pacific. Current per-model numbers are shown
  only in AI Studio (login) and are "not guaranteed". Numbers in the archived
  snapshots and on forums are stale (users reported large cuts during
  2025–2026) → do not encode them; the owner reads AI Studio at setup.
- **Data — important:** for **Unpaid Services**, Google uses submitted content
  and responses to improve its products/ML, and human reviewers may read them
  (disconnected from your account/key first). Official warning: *"Do not
  submit sensitive, confidential, or personal information to the Unpaid
  Services."* (EEA/CH/UK accounts get the paid-services data terms instead.)
  For this project: fine for public/open-source code and writing; think twice
  before sending private code or personal text.
- **API shape:** `https://generativelanguage.googleapis.com/v1beta` (native +
  OpenAI-compatible surface the kit uses). Function calling is a core Gemini
  feature on current Flash models.
- **Suggested guard settings:** until the owner reads the AI Studio numbers,
  start at 1 in flight, ≤10 RPM, and a conservative few-hundred-requests/day
  self-cap; then replace with the real per-model values.
- Sources: `ai.google.dev/gemini-api/docs/pricing`,
  `…/docs/rate-limits` (last updated 2026-10-15), `…/docs/billing`,
  `ai.google.dev/gemini-api/terms` (effective 2026-03-23; fetched).

## 6. Groq (candidate → recommended)

- **Get a key:** account at console.groq.com → `console.groq.com/keys`.
  The **Free plan is $0** (plans page: "Build and Test on Groq"); a payment
  method is only needed to upgrade to the Developer tier, and you can
  downgrade back to Free at any time.
- **Limits (published, per model, organisation-level):** RPM, RPD, TPM, TPD
  (some orgs also input/output TPM splits). Examples fetched 2026-10-18 from
  the official rate-limits page: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`,
  `qwen/qwen3.8-27b` → 30 RPM, 1K RPD, 8K TPM, 200K TPD. Exact values for your
  org are in Settings → Limits; responses carry `x-ratelimit-remaining-*` /
  `x-ratelimit-reset-*` headers and `retry-after` on `429` (note the quirk:
  `x-ratelimit-limit-requests` refers to the *daily* request limit).
- **Data (strong):** Terms: user data "is not retained or used by Groq other
  than to perform the Generative AI Services"; Terms of Sale §4.2: "We will
  never access Customer Data for training purposes." Inference data is not
  retained by default (limited reliability/abuse retention, ZDR opt-in).
- **API shape:** OpenAI-compatible `https://api.groq.com/openai/v1`; tool use
  available on supported models (check per model at W-030).
- **Verdict:** best-documented permanent free tier of the candidates; models
  rotate (the list's model examples already differ from last year's), so the
  scout must read `/models` + the limits page, never hard-code.
- **Suggested guard settings:** encode the per-model RPD/TPD as the budget;
  1–2 in flight is plenty; cached tokens don't count toward limits.
- Sources: `console.groq.com/docs/rate-limits` (fetched),
  `…/docs/billing-faqs`, `…/settings/billing/plans`, `…/docs/your-data`,
  `…/docs/legal/archive` (Terms of Use / Terms of Sale excerpts).

## 7. Cerebras (candidate → excluded by default)

- **Official position (rate-limits FAQ, fetched 2026-10-18):** *"Is there a
  permanently free tier? No."* New accounts get **$5 in free credits after
  adding a verified payment method**; credits expire **30 days** after grant;
  without a payment method, Playground/API stay inactive. When credits end,
  access stops
...[truncated 7666 chars]