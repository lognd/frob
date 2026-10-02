+++
id = "01M3WYJ80MB15DKQ823WGQY08T"
title = "frob-evidence + frob-tests: evidence providers, dir store, touched-set test selection"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0020"]
labels = ["milestone:2.0.0", "component:frob-evidence"]
scope = ["crates/frob-evidence/**", "crates/frob-tests/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ809HJ88ZWB20SCTJS3K"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80DWFZK0DPR4CBP0KHT"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80JTE725WDR4N6A18DJ"

[[acceptance]]
text = "Given a worktree where one function changed, when frob test --base main runs, then only tests reaching that function run and an evidence event is appended"
bound = false

[[acceptance]]
text = "Given a ticket of a code-changing type with no measured evidence, when close runs, then exit is 3 with the remedy naming frob test"
bound = false
+++

Implement crates/frob-evidence and crates/frob-tests per tickets.md section 9 (dir: and https stores only for M1 per audit M35) and build-test-ci.md. Evidence record = event kind evidence { provider, ref, digest, uri, status measured|unmeasured, captured_at }; providers: nextest (parse libtest JSON or junit from cargo nextest via gob-exec with the Cargo program class), command (arbitrary allowlisted tool output with redaction), file (hash a path). Blobs under 16 KiB (knob) inline, larger ones in the dir: store (default .git/frob/artifacts, non-authoritative) addressed by blake3. ticket evidence add|list|fetch verbs; the close guard trait from frob-ledger is implemented here: close requires at least one measured evidence record for code-changing types unless --no-evidence --reason. frob-tests: touched set = files changed against --base mapped through gob-symbols affects() to Rust test functions and their packages; frob test --base <ref> runs cargo nextest with the selected filter via gob-exec, records evidence on the active ticket when run in a worktree. TEST001 rule: frob:tests directive names a test that does not exist.
