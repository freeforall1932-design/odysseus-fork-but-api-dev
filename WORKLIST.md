# Audit Worklist

**Status:** Security findings are pending user approval; no security remediation has started. Two unrelated deprecation warnings were cleaned up separately.

## Priority 0 — Obtain approval

- [ ] Confirm which audit findings should be fixed and whether the agent shell/filesystem sandbox risk is in scope.
- [ ] Keep all work on `arena/01a10a87-odysseus-fork-but-api-dev`.

## Priority 1 — Protect auth and session persistence (A-1, High)

- [ ] Add a secure atomic-write path for secret-bearing JSON files that creates temp files with owner-only permissions before writing/renaming.
- [ ] Re-lock existing `auth.json` and `sessions.json` files on startup; handle failure explicitly and preserve Windows ACL behavior.
- [ ] Restrict the data directory where compatible, including Docker bind-mount behavior and ownership.
- [ ] Create `.env` with owner-only permissions rather than inheriting the example file's mode.
- [ ] Consider hashing persisted session tokens and add POSIX permission tests for newly created and pre-existing files.
- [x] Baseline auth/session and atomic-I/O tests run (81 focused tests passed without warnings); rerun after an approved fix.

## Priority 1 — Close token-chat DNS rebinding (A-2, High)

- [ ] Design an outbound transport that pins each connection to a validated public IP while preserving Host/SNI.
- [ ] Apply it to `/api/v1/chat` initial calls and resumed sessions; ensure redirects cannot bypass validation.
- [ ] Add deterministic regression tests for DNS changing between validation and connection, including a resumed session.
- [ ] Update the relevant `THREAT_MODEL.md` entry to describe the residual behavior accurately.
- [x] Baseline API-chat and security-area tests run (832 security-area tests passed without warnings); add direct DNS-rebinding regressions and rerun after an approved fix.

## Priority 1 — Secure bootstrap (A-3, conditional High)

- [ ] Restrict `/api/auth/setup` to trusted loopback access or a strong, one-time bootstrap secret.
- [ ] Decide whether startup should fail when auth is enabled but bootstrap/setup fails.
- [ ] Add tests for remote first-run rejection, valid local bootstrap, and concurrency/one-time behavior.
- [x] Baseline auth-policy and root-path middleware tests run (included in the 81 focused tests); add remote-bootstrap coverage and rerun after an approved fix.

## Priority 2 — Fail closed on invalid privilege data (A-4, Medium)

- [ ] Change `require_privilege()` to deny when the privilege record is malformed or lookup fails.
- [ ] Update the existing fail-open regression test and add tests for lookup exceptions and malformed stored maps.
- [x] Baseline privilege/auth security tests run (included in the focused and security-area suites); add fail-closed assertions and rerun after an approved fix.

## Priority 3 — Validate and document residual risk

- [ ] Decide whether an OS-level sandbox or stronger isolation for shell/Python/file tools is required by the deployment threat model.
- [ ] If approved, scope a separate design for least-privilege execution, filesystem confinement, and network egress controls; do not treat prompt instructions as a sandbox.

## Test environment

- [x] Established repo-local ignored `.venv/` and installed `requirements.txt`.
- [x] Ran focused audit tests: 81 passed, no warnings.
- [x] Ran security area: 832 passed, 5,124 deselected, no warnings.
- [x] Replaced deprecated SQLAlchemy and Pydantic APIs responsible for the two warnings; confirmed they are gone in the security-area run.
- [ ] After approved security changes, rerun focused tests, related security suites, then the broader suite as practical.
- [x] Recorded the validation commands/results in `audit.md`; baseline passes do not prove the audit findings are fixed.
