---
id: T-0008
title: 'gob-diagnostics: envelope, exit-code table, text and JSON renderers'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0005
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- crates/gob-diagnostics/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given findings of mixed severity and fail_on = error, when evaluated, then
    exit is 1 only if an Error finding exists and 0 otherwise
  evidence: []
- text: Given stdout is not a TTY, when rendered, then output is the JSON envelope
    with schema_version
  evidence: []
threat: null
component: gob-diagnostics
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-diagnostics per cli.md sections 1 to 2 (as updated by D27) and architecture.md section 4. Types: Envelope<T> { ok, data, findings: Vec<Finding>, warnings, error: Option<EnvelopeError { code, message, remedy, retryable }>, schema_version }, ExitCode enum (Ok=0, Negative=1, Usage=2, Refused=3, Internal=4) with the row-per-refusal-class table from cli.md encoded as an enum RefusalClass with its exit code and retryable flag; Refusal error type (code string like E-LEASE-HELD, remedy, retryable) that maps to exit 3; renderers: text (grouped by file, snippet from gob-text, color via anstream respecting NO_COLOR and TTY detection), JSON (serde, stable field order), and a summary line; a fail_on(Severity) evaluator that turns findings into the exit code. Snapshot tests for both renderers. JSON schema export for the envelope via schemars.