# Gifscythe — Planning Report (final)

Snapshot as of repo state S31 (`main`, 34-commit history — the pre-S31 history
was squashed/re-uploaded at some point, so old commit SHAs no longer resolve;
treat this report as the current source of truth, not the earlier drafts of
it in chat).

Two tracks, on purpose: **EXE** (ship first, minimal remaining work) and
**WEB** (client-side wasm, explicitly a second, currently-unproven track).
Nothing here commits you to anything — paste it into `docs/planning/` and
edit freely.

---

## 1. EXE track — finish, don't rewrite

**Decision:** stay on C++17 + Qt6. A rewrite (Tauri, or the parked C# shell)
discards ~250 already-verified tests and CI for a marginal ergonomics gain.
`OFFLINE_BUILD_REVIEW.md`'s own weighted scoring already settled this
(C++/Qt6 ≈258 vs Tauri ≈205 vs Electron ≈174) — nothing since has changed
that math.

**Ordered remaining work** (per the repo's own "what remains before 1.0.0"
list — do these in order, not in parallel, since later items assume earlier
ones are done):

1. **Finish the GUI's partial-write safety** (U-59/P0-7, Qt half). The
   CLI/core got this at S28; the GUI still writes straight onto the target
   file. This is the same failure class as the external audit's top
   (HIGH-severity) finding — Explode bypassing the partial-write guard on
   both surfaces. Do this before anything else on this list.
2. Release re-cut: U-09/P0-4 + the U-95 release-notes edit.
3. Clean-Windows smoke test (W-18) — re-point at a real green CI run, then
   actually run it on real hardware (this hasn't happened yet; a CI artifact
   is not the same as a clean-machine run).
4. Desktop probes (W-19): kill-engine-mid-run, physical drag-drop,
   engine-missing GUI state. `DESKTOP_PROBES.md` has the procedures.
5. GS-203's GUI half, remaining Qt/platform rows.
6. Remaining web-intake batch items (P2-19/U-92 next, then the P2/P3 rows).
7. Owner decisions: OD-16 (see §3), OD-18, the version-bump call.

**Already done, don't redo:** Qt LGPL notice (U-08, closed S19). C# spike is
parked (`OD-C7`) — inert but kept CI-running so it doesn't rot; no further
investment until the list above ships.

---

## 2. Web track — minimal wasm, additive, not a replacement

**Decision:** the existing Node-based `web/` server build stays exactly as
it is — untouched, still the officially shipped web path — while a
client-side wasm build is developed *alongside* it as an unproven,
additive track (`web/wasm/`). Nothing gets deleted until the wasm build is
actually proven.

Why not just harden the Node server instead: it needs Node installed and a
manually-started process, which isn't the "no server, double-click and use"
experience the whole project is going for. Wasm is the only path to that,
but it has to earn its way to shippable, not be assumed there.

Why not delete the server now and commit fully to wasm: no `.wasm` binary
has ever actually been produced or run, by any agent, in any session so far
(see §4). Deleting a working, hardened thing to bet on something untested
is the least stable option on the table, not the boldest one.

---

## 3. The wasm task — build it, or borrow it, but prove it either way

This is the one piece of the whole plan that's still genuinely open. Two
honest paths; pick one (or run both and compare):

### Option A — build gifsicle.wasm from scratch (existing scaffold)

The scaffold already exists (`web/wasm/`: `build_wasm.sh`, `config.wasm.h`,
`glue_harness.mjs`, `prove_wasm.mjs`, `wasm.js`, `index.html`) and reuses
`web/command.mjs` + `web/validate.mjs` verbatim. What's missing is the
actual compile: every attempt so far — across at least two separate agent
sandboxes, mine included — has been blocked at the exact same point:
Emscripten's toolchain download comes from
`storage.googleapis.com/webassembly/emscripten-releases-builds/`, and that
domain is unreachable from every sandbox tried so far. This is an
environment/network limitation, not a code problem — the gifsicle source is
straightforward single-process C with no `fork()`, so it should compile
cleanly once a real toolchain is reachable.

**Task:** on a machine with real, unrestricted internet access (a personal
machine, or a CI runner without an egress allowlist), run
`web/wasm/build_wasm.sh`, then `prove_wasm.mjs` against a real file. This
cannot be done from inside the kind of sandboxed agent environment this
project has been built in so far — it needs to be someone's actual machine,
once.

**Byte parity note:** this path preserves the project's existing
verification approach (compare wasm output byte-for-byte against the native
1.96 oracle already captured), since it's compiling the exact same vendored
source.

### Option B — adopt an existing pre-built implementation

Gifsicle has already been compiled to WebAssembly by other open-source
projects, and at least one installs cleanly in a network-restricted sandbox
(tested directly, this session):

| Package | Target | Notes |
|---|---|---|
| [`gifsicle-wasm-browser`](https://github.com/renzhezhilu/gifsicle-wasm-browser) (npm) | Browser | Single ~336KB bundled file, no separate `.wasm` fetch, `gifsicle.run({input, command})` API accepting real CLI-style argv. **Installed successfully via `npm install` in this sandbox** — confirmed the GCS wall does not block npm. Restores **gifsicle 1.92** behavior — not the project's vendored 1.96, so it will not byte-match the existing oracle; a new correctness baseline would be needed. Could not fully execute it in a plain Node test here (it appears to assume real browser Worker semantics) — untested past install. |
| [`@wasm-codecs/gifsicle`](https://www.npmjs.com/package/@wasm-codecs/gifsicle) (npm) | Node.js only | Clean `encode(buffer, options)` API, MIT license, part of the `cyrilwanner/wasm-codecs` monorepo. No browser build yet per its own README — would need porting for a client-side page. |
| [`gifsicle-bin`](https://pypi.org/project/gifsicle-bin/) (PyPI) | Python wheel + WASM/JS | Explicitly built for "frontend developers... without needing a backend." Worth a closer look if Option A stays blocked. |

**Task:** if Option A stays blocked for longer than you're willing to wait,
spike `gifsicle-wasm-browser` in a real browser (not Node) against the same
`logo.gif` oracle used elsewhere in the project, and decide whether a
1.92-vs-1.96 behavioral diff is acceptable for a first shippable web build.

**Licensing note — applies to both options equally:** adopting someone
else's compiled binary does not change the OD-16 question at all. It's
still GPLv2 engine code running in-process alongside Ms-PL first-party
code; the origin of the `.wasm` file is irrelevant to that analysis. Don't
let "we didn't compile it ourselves" read as "so the license question
doesn't apply here."

### Automatic crash/failure diagnostics (applies to whichever option ships)

Requested explicitly: when someone finally runs this with real internet
access, a crash or failure should be self-diagnosing, not something that
needs a live debugging session to explain. Concretely:

- Wrap wasm module instantiation and every `run()` call in try/catch.
  Never let a failure surface as a silent no-op or a generic "something
  went wrong."
- Capture and log, on any failure: the exact error/exception, the wasm
  module's own stdout/stderr (Emscripten exposes this via `print`/
  `printErr` callbacks — route both into the log, don't drop them),
  the exact command/argv that was attempted, and the environment (Node
  version or browser user-agent).
- Write that log somewhere durable and visible — a downloadable `.log`
  file, or an on-page "show error details" panel — not just the console.
- Fail loud at load time too: if the `.wasm` file itself fails to fetch or
  instantiate, say so immediately and specifically, rather than letting the
  first symptom be a confusing downstream error from code that assumed the
  module loaded.
- Treat this the same way the rest of the project treats "tests that can't
  fail" (the external audit's Priority 6) — a diagnostic path that can't
  actually produce a log on a real failure isn't done.

---

## 4. Open decisions this report doesn't make for you

- **OD-16** (`docs/legal/README.md` §3–4): may `web/wasm/` ship with the
  GPLv2 engine in-process alongside Ms-PL code? Currently answered
  "(a) no, until counsel actually answers" — that's a real, load-bearing
  answer, not a placeholder. Needs an actual owner/counsel decision before
  either wasm option above is shippable, regardless of which one you build.
- **OD-18** and the version-bump call — unresolved, not urgent relative to
  the list in §1.
- **Option A vs Option B** (§3) — genuinely your call; this report lays out
  the tradeoff rather than picking one, since "less work now" and "less
  work overall" point in different directions here.

---

## 5. Sources

Repo docs referenced: `README.md`, `PROJECT_VISION.md`, `STATUS.md`,
`WORKLIST.md`, `SESSION_HANDOFF.md`, `docs/planning/OWNER_DECISIONS.md`,
`docs/planning/PLANNING.md`, `docs/legal/README.md`, `docs/web/
WEB_FEASIBILITY.md`, `web/WEB_PLAN_TEMPLATE.md`, `.github/workflows/
build.yml`, and the two external-audit files at repo root ("space bunny
review", independent read-only review via the public GitHub API).

External packages referenced: `gifsicle-wasm-browser`, `@wasm-codecs/
gifsicle`, `gifsicle-bin` (links in §3).
