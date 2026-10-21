# Gifscythe — Independent review

Repository: freeforall1932-design/gifscythe
Commit: 7a0a8b8883e35e3233944095e1ca9544cd10f500

## Scope and limitations
Read-only, source-derived review of six implementation files and seven context/audit documents. Compared against the compiled audit, Audit A, Audit B, and the consolidated register. The entire repository was not cloned or line-audited; vendored code, native tests, and Windows runtime behavior were not executed. All eight findings are additional candidates, not runtime-verified results. Source is pinned to 7a0a8b8883e35e3233944095e1ca9544cd10f500.

## Summary
8 additional candidates: 1 High, 6 Medium, 1 Low. No new Critical finding claimed. Existing release blockers remain governed by the baseline audit.

## GS-101 · High · Batch output destination can change during a run

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/working_code/gifscythe/src/qtui/MainWindow.cpp
Symbols: setBusy() · chooseBatchDir() · onProcessFinished()
Evidence level: source review; runtime reproduction pending.

The batch folder text field is disabled while busy, but its sibling Browse button is not. The picker can still call setText() on the disabled field. Each subsequent batch job computes its output from the current folder, so a running batch can silently split its outputs across destinations without repeating preflight.

### Evidence
```
batchDirEdit_->setEnabled(!busy);
// browseBatchDirButton is not disabled

void MainWindow::chooseBatchDir() {
  // no busy_ guard
  if (!dir.isEmpty()) batchDirEdit_->setText(dir);
}

// next batch item
pendingOutput_ = defaultOutputFor(in);
```

### Proposed reproduction (not executed)
1. Queue at least two GIFs with a deliberately slow test engine and select output folder A.
2. Start Batch, then use the still-enabled batch-folder Browse button to select folder B.
3. Observe whether later jobs write into B while the first job writes into A. Run only with disposable inputs.

### Suggested fix
Snapshot a complete, validated job plan before starting. Disable the entire output group and guard chooser slots while busy; subsequent jobs must use immutable planned destinations.

### Prior-audit distinction
U-01 / A:GS-001 concerns collisions in the initial plan. This is a separate time-of-use mutation after preflight; U-35 only concerns Run re-enablement.

## GS-102 · Medium · A previous web request can replace the current result

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/web/app.js
Symbols: setFile() · run click handler
Evidence level: source review; runtime reproduction pending.

Selecting a new file while optimization is pending resets the preview and re-enables Run. The old request has no generation check or cancellation. Its completion then populates After and the download link alongside the new Before image. Multiple requests can overwrite results out of order.

### Evidence
```
function setFile(f) {
  currentFile = f;
  $("run").disabled = false;
}

const resp = await fetch(url, { method: "POST", body: currentFile });
const blob = await resp.blob();
// no file identity or request-generation check
$("after").src = URL.createObjectURL(blob);
```

### Proposed reproduction (not executed)
1. Start optimizing GIF A with an artificially delayed response.
2. Select GIF B before A completes, then optionally start B.
3. Let A finish last; compare the Before image, After image, and downloaded GIF.

### Suggested fix
Capture the input and a request generation at launch. Abort obsolete requests and ignore every stale success, error, and finally handler. Only the active generation should change Run state.

### Prior-audit distinction
Not the desktop temp-file leak in B:BUG-14 / U-34. This is web response ownership, not file cleanup or missing web modes.

## GS-103 · Medium · Desktop preview invalidation happens too late

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/working_code/gifscythe/src/qtui/MainWindow.cpp
Symbols: onSelectionChanged() · schedulePreview() · startPreview()
Evidence level: source review; runtime reproduction pending.

The preview generation advances only when a new eligible preview starts, not when selection or settings change. During the 1.2-second debounce, the old completion still passes its sequence guard. Clearing the queue or selecting Explode causes the next preview to return before incrementing, so the old result can reappear and remain visible.

### Evidence
```
void MainWindow::schedulePreview() {
  if (busy_) return;
  previewTimer_->start(); // generation unchanged
}

// startPreview(): invalid input / Explode return first
const int seq = ++previewSeq_;

// completion
if (seq != previewSeq_) return;
```

### Proposed reproduction (not executed)
1. Start a slow preview of GIF A.
2. Select B, clear the queue, or switch to Explode while A is still encoding.
3. Allow A to finish before a new valid preview begins; inspect After for a stale image.

### Suggested fix
Invalidate the generation immediately on every input/settings change, queue clear, and cancellation. Cancel obsolete work independently of whether a replacement preview can start.

### Prior-audit distinction
Related to A:GS-012 cancellation guidance, but adds the uncovered debounce and early-return paths. U-34 concerns leaked files, not stale visual correctness.

## GS-104 · Medium · Empty comments remove a required argv operand

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/working_code/gifscythe/src/core/GifsicleCommand.h
Symbols: add() · comments loop
Evidence level: source review; runtime reproduction pending.

SettingsIO accepts an empty comment value. The command builder adds --comment but its shared add() helper discards the empty string operand. This creates a malformed argv sequence: the following token can be consumed as comment text or trigger an option error instead of keeping the intended argument boundaries.

### Evidence
```
inline void add(std::vector<std::string>& v, const std::string& s) {
  if (!s.empty()) v.push_back(s);
}

for (const auto& c : s.comments) {
  add(args_, "--comment");
  add(args_, c); // empty operand disappears
}
```

### Proposed reproduction (not executed)
1. Load a disposable settings file containing an empty “comment =” line and an input path.
2. Inspect GifsicleCommand::args(): --comment has no empty operand.
3. Add a regression asserting that the input stays an input and the empty operand is retained or explicitly rejected.

### Suggested fix
Never filter required argv operands. Push both tokens together, including an empty string, or reject/skip the entire empty-comment option according to a documented policy.

### Prior-audit distinction
A:GS-011 covers malformed booleans and numeric validation, not argument cardinality. Shell quoting cannot repair an already-missing argv element.

## GS-105 · Medium · Settings query values are decoded twice

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/web/server.mjs
Symbols: handleOptimize()
Evidence level: source review; runtime reproduction pending.

URLSearchParams.get() already percent-decodes the query value. The additional decodeURIComponent() corrupts literal percent sequences inside valid JSON. A comment containing “100%” throws and returns HTTP 400; “%20” is silently turned into a space.

### Evidence
```
const raw = url.searchParams.get("settings") || "{}";
settings = JSON.parse(decodeURIComponent(raw));

// client already encodes once
"/optimize?settings=" + encodeURIComponent(JSON.stringify(s));
```

### Proposed reproduction (not executed)
1. Send a correctly encoded settings object with comments: ["100%"].
2. The extra decode throws URIError and the server returns “bad settings JSON”.
3. Repeat with comments: ["%20"] and check that the literal value changes.

### Suggested fix
Parse JSON directly from url.searchParams.get("settings"). Add transport round-trip tests for %, %20, %22, plus signs, Unicode, and malformed JSON.

### Prior-audit distinction
U-30 is missing semantic validation. This is corruption of syntactically valid transport data before validation or engine execution.

## GS-106 · Medium · Valid command text can break the HTTP response header

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/web/server.mjs
Symbols: handleOptimize() · X-Gifscythe-Command
Evidence level: source review; runtime reproduction pending.

The full command is inserted into an HTTP header without a header-safe encoding. Valid GIF comment arguments can contain newlines or characters outside Latin-1, and the engine path can also contain Unicode. Node rejects invalid header characters, turning a successful engine result into a response failure.

### Evidence
```
res.writeHead(200, {
  "Content-Type": "image/gif",
  "X-Gifscythe-Command": argv.map(shellQuote).join(" "),
});
// POSIX shell quoting is not HTTP header encoding
```

### Proposed reproduction (not executed)
1. Use a valid GIF and settings with a CJK comment or an embedded newline.
2. Allow the engine to complete successfully.
3. Check for an invalid-header exception instead of a successful GIF download. Also test a Unicode engine path.

### Suggested fix
Return command metadata separately as JSON or use a documented ASCII-safe encoding and decode it in the client. Bound metadata size; never treat shell quoting as header sanitization.

### Prior-audit distinction
A:GS-006 concerns Windows process encoding. This is Node HTTP output encoding and can fail on any supported host.

## GS-107 · Medium · Unescaped settings values can become additional keys

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/working_code/gifscythe/src/core/SettingsIO.h
Symbols: save_settings() · load_settings()
Evidence level: source review; runtime reproduction pending.

The line-based serializer writes string values verbatim, while the loader splits on newlines and treats each line as a new key. A programmatically supplied multiline comment or a valid POSIX path containing a newline cannot round-trip; its later lines can override settings. Leading and trailing whitespace is also lost.

### Evidence
```
for (const auto& c : s.comments)
  out << "comment = " << c << "\n";

// load_settings reads each physical line as a key
while (std::getline(in, line)) {
  // ... set_field(s, key, val, warnings);
}
```

### Proposed reproduction (not executed)
1. Create a Settings object with a comment containing a newline followed by “mode = merge”.
2. Serialize it and load the result into a new Settings object.
3. Assert both the comment and mode are unchanged; source analysis predicts the comment is truncated and mode is overwritten.

### Suggested fix
Define a backward-compatible escaping/quoting scheme or reject unrepresentable string values before saving. Test newline, carriage return, whitespace, equals signs, and Unicode round trips.

### Prior-audit distinction
U-16 is atomicity; U-19 is omission of inactive values. Neither covers injection of new logical keys through unescaped string serialization. This is not a claim of remote code execution.

## GS-108 · Low · Before-image object URLs are never released

Source: https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/web/app.js
Symbols: setFile()
Evidence level: source review; runtime reproduction pending.

Each file selection creates a new object URL for Before, but only After URLs are retained and revoked. Replacing the src does not release the earlier blob URL, so repeatedly choosing large files keeps them reachable until the page unloads.

### Evidence
```
if (afterUrl) {
  URL.revokeObjectURL(afterUrl);
  afterUrl = null;
}
$("before").src = URL.createObjectURL(f);
// previous Before URL is not retained or revoked
```

### Proposed reproduction (not executed)
1. Instrument URL.createObjectURL and URL.revokeObjectURL.
2. Select multiple GIFs without running optimization.
3. Verify that Before URLs are created repeatedly with no corresponding revocation.

### Suggested fix
Track a beforeUrl alongside afterUrl. Revoke the previous Before URL on replacement and release both URLs during teardown.

### Prior-audit distinction
B:BUG-14 / U-34 is desktop preview disk cleanup. This is browser blob lifetime on the input side.

## Baseline documents
- [Repository guide](https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/README.md)
- [Project vision](https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/PROJECT_VISION.md)
- [Compiled audit](https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/COMPILED_AUDIT.md)
- [Audit A](https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/AUDIT_A_extracted.md)
- [Audit B](https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/AUDIT_B_extracted.md)
- [Consolidated audit](https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/docs/audit/CONSOLIDATED_AUDIT_2026-09-10.md)
- [Session handoff](https://github.com/freeforall1932-design/gifscythe/blob/7a0a8b8883e35e3233944095e1ca9544cd10f500/SESSION_HANDOFF.md)