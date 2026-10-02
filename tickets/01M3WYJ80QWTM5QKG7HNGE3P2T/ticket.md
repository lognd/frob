+++
id = "01M3WYJ80QWTM5QKG7HNGE3P2T"
title = "frob-check: orchestration, --ticket scoping, --fix tier A, persisted findings, timing budget"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0023"]
labels = ["milestone:2.0.0", "component:frob-check"]
scope = ["crates/frob-check/**", "crates/frob/**", "crates/gob-dev/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80BJ3NMGNWTAJ7SYPA5"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80FD296GC3SAK8MNYRD"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80MB15DKQ823WGQY08T"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80P1RYNYMN2QGSG7BCD"

[[acceptance]]
text = "Given this repository with a warm cache, when frob check runs in a fresh process, then it finishes under 2 s and reports the timing breakdown"
bound = false

[[acceptance]]
text = "Given a Deterministic fix available, when frob check --fix runs, then the file is rewritten and a second run reports no finding"
bound = false
+++

Implement crates/frob-check per rules.md section 4 (pipeline, post-D27 step 8) and D30. frob check [--ticket <id>] [--only FAMILY] [--fix] [--fail-on severity] [--json] [--explain ID]: walk (gob-walk) -> parse -> symbols -> directives -> per-file rules in parallel with rayon, consulting the findings cache first -> repo rules keyed by graph digest -> exception evaluation -> render. --ticket limits files to the lease scope plus [check] ticket_hops dependents (knob). --fix applies Deterministic fixes and reports the rest. check.tool array-of-tables stages run external tools through gob-exec after the built-in rules and are timed separately (outside the 2 s budget). Emit a timing breakdown with -v and a telemetry line to .frob/telemetry.jsonl (knob). Bench: criterion harness running the full check on this repository, asserting a warm fresh-process run under 2 s on the CI profile (soft gate: record, fail only when [perf] enforce = true).
