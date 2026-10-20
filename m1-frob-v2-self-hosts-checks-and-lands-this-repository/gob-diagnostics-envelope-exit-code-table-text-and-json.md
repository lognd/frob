+++
id = "01M3WYJ808PBE214Y9RH093BQT"
title = "gob-diagnostics: envelope, exit-code table, text and JSON renderers"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0008"]
labels = ["milestone:2.0.0", "component:gob-diagnostics"]
scope = ["crates/gob-diagnostics/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ8059GN1VBGSA69X5BSZ"

[[acceptance]]
text = "Given findings of mixed severity and fail_on = error, when evaluated, then exit is 1 only if an Error finding exists and 0 otherwise"
bound = true

[[acceptance]]
text = "Given stdout is not a TTY, when rendered, then output is the JSON envelope with schema_version"
bound = true
+++

Implement crates/gob-diagnostics per cli.md sections 1 to 2 (as updated by D27) and architecture.md section 4. Types: Envelope<T> { ok, data, findings: Vec<Finding>, warnings, error: Option<EnvelopeError { code, message, remedy, retryable }>, schema_version }, ExitCode enum (Ok=0, Negative=1, Usage=2, Refused=3, Internal=4) with the row-per-refusal-class table from cli.md encoded as an enum RefusalClass with its exit code and retryable flag; Refusal error type (code string like E-LEASE-HELD, remedy, retryable) that maps to exit 3; renderers: text (grouped by file, snippet from gob-text, color via anstream respecting NO_COLOR and TTY detection), JSON (serde, stable field order), and a summary line; a fail_on(Severity) evaluator that turns findings into the exit code. Snapshot tests for both renderers. JSON schema export for the envelope via schemars.
