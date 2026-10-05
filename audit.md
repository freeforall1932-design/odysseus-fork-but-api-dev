# Odysseus Codebase Audit

**Status:** Findings are open and pending approval. No security fixes have been applied.
**Review date:** 2026-10-05
**Branch:** `arena/01a10a87-odysseus-fork-but-api-dev`
**Scope:** Targeted source review of auth/session persistence, first-run setup, token-based chat/SSRF, and feature privilege checks. This is not a penetration test or a claim of exhaustive review.

## Findings

### A-1 — High: Session and auth files are created with permissive filesystem modes

`core/atomic_io.py:31-39` opens its temporary JSON file without a restrictive mode and then atomically replaces the destination. With the common POSIX umask `022`, this creates mode `0644`. `core/auth.py:95,152-158,581-595` persists session tokens as cleartext dictionary keys in `sessions.json`; the same token is used as the browser session cookie (`routes/auth_routes.py:181-195`). `auth.json` is also written through this helper (`core/auth.py:221-222`), while first-run setup writes it with a normal `open()` (`setup.py:121-132`). `setup.py:39-42` creates data directories without restrictive permissions. The `.env` created by `setup.py:157-168` is copied from the example without tightening its mode.

**Impact:** A local user/process able to traverse the data directory (or repository directory for `.env`) could read a live session token and replay it, potentially hijacking an admin account. `.env` may contain provider credentials.

**Evidence checked:** A standard-library probe loaded `core/atomic_io.py` directly and confirmed that under umask `022`, `atomic_write_json()` creates mode `0644`.

**Suggested remediation:** Create secret-bearing files atomically with owner-only permissions before they become visible; re-lock existing auth/session/key files at startup; restrict the data directory where compatible; create `.env` with owner-only permissions. Consider storing session-token hashes rather than raw tokens. Account for Windows ACLs and Docker bind mounts.

### A-2 — High: DNS-rebinding SSRF in token-authenticated `/api/v1/chat`

`routes/webhook/webhook_routes.py:284-311` validates a caller-supplied `base_url`, then stores the hostname in a new session. `src/url_security.py:59-78,81-93` resolves and checks the hostname but returns the original URL; its docstring explicitly notes that DNS checks alone do not eliminate rebinding. The later request uses the normal pooled HTTPX client (`src/llm_core.py:510-518,2414-2415`), which does not pin the connection to the IP checked earlier. A DNS answer can therefore change between validation and connection. When a token resumes the stored session, the session branch (`routes/webhook/webhook_routes.py:257-277`) does not re-run the direct-URL validation.

**Impact:** A holder of a chat-scoped API token and a hostname they control may cause server-side requests to private/internal addresses despite the initial URL check.

**Suggested remediation:** Resolve and validate at connection time and pin the TCP destination to an approved public IP while preserving the original hostname for Host/SNI; apply the protection to every request, including resumed sessions. Add regression tests for rebinding on initial and resumed calls. `THREAT_MODEL.md:77` should also be updated: the route now performs an initial validation, but the rebinding gap remains.

### A-3 — High, conditional: Exposed first-run setup can be claimed remotely

`app.py:263-276` exempts `/api/auth/setup` from authentication. `routes/auth_routes.py:127-143` rate-limits by client IP and checks that no user exists, but does not require a loopback client or a one-time setup secret. `AuthManager.setup()` makes the first created account an admin (`core/auth.py:255-260`). The normal installers pre-seed an account, but Docker startup continues after setup errors (`docker/entrypoint.sh:147-150`), so an unconfigured instance can still start.

**Precondition:** No account has been created and the instance is reachable by an untrusted network client. A single successful request is sufficient; the rate limit does not prevent a first-claim race. This finding does not apply after an account has been configured.

**Suggested remediation:** Restrict bootstrap to loopback or require a strong one-time bootstrap secret. Consider failing startup when auth is enabled but bootstrap did not complete.

### A-4 — Medium: Feature privilege checks fail open on malformed privilege data

`src/auth_helpers.py:178-187` returns the user when `get_privileges()` raises and treats a non-dictionary result as an empty map; the default lookup then allows access. `core/auth.py:378-385` can raise when a persisted privilege map has an invalid shape. The behavior is explicitly accepted by `tests/test_auth_require_privilege_nondict.py:22-29`.

**Impact:** If a user's auth record is malformed or privilege lookup fails, route-level checks for features such as documents, research, memory, and image generation can allow access despite an intended restriction. This requires malformed/corrupt state or an unexpected lookup failure; normal valid privilege maps are not affected.

**Suggested remediation:** Fail closed on invalid privilege records or lookup errors, and add tests asserting a denial for malformed data.

## Documented residual risk

`THREAT_MODEL.md:75` acknowledges that the agent's shell/filesystem tools are not sandboxed from the application OS account or network. This remains a substantial, documented design risk if untrusted content can influence an admin-enabled agent run; it is separate from the four findings above.

## Validation performed

- **Repo-local environment:** Created the ignored `.venv/` and installed `requirements.txt`; no dependency manifest was changed.
- **Focused tests:** `.venv/bin/python -m pytest tests/test_api_chat_security.py tests/test_auth_policy.py tests/test_auth_require_privilege_nondict.py tests/test_auth_root_path.py tests/test_auth_session_revocation.py tests/test_atomic_io.py -q` — **81 passed, no warnings**.
- **Security area:** `.venv/bin/python tests/run_focus.py --area security -- --quiet` — **832 passed, 5,124 deselected, no warnings**.
- **Deprecation cleanup:** Replaced the deprecated SQLAlchemy declarative-base import with `sqlalchemy.orm` and Pydantic's deprecated `.dict()` call with `.model_dump()`; both test runs above are warning-free.
- **Syntax check:** Parsed 1,159 Python files with `ast.parse`; zero syntax errors.
- **Permission probe:** Confirmed `atomic_write_json()` produces `0644` under umask `022`.
- **Whitespace check:** `git diff --check` clean.

The passing suites validate the current code but do not invalidate the audit findings. They do not establish safe session-file permissions or close the DNS-rebinding, remote-bootstrap, or fail-open privilege gaps. Security findings remain open pending approval; no security remediation has been applied.
