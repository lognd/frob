---
id: T-0023
title: 'frob-check: orchestration, --ticket scoping, --fix tier A, persisted findings,
  timing budget'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0022
- T-0020
- T-0011
- T-0015
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 8
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
- crates/frob-check/**
- crates/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given this repository with a warm cache, when frob check runs in a fresh process,
    then it finishes under 2 s and reports the timing breakdown
  evidence: []
- text: Given a Deterministic fix available, when frob check --fix runs, then the
    file is rewritten and a second run reports no finding
  evidence: []
threat: null
component: frob-check
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/frob-check per rules.md section 4 (pipeline, post-D27 step 8) and D30. frob check [--ticket <id>] [--only FAMILY] [--fix] [--fail-on severity] [--json] [--explain ID]: walk (gob-walk) -> parse -> symbols -> directives -> per-file rules in parallel with rayon, consulting the findings cache first -> repo rules keyed by graph digest -> exception evaluation -> render. --ticket limits files to the lease scope plus [check] ticket_hops dependents (knob). --fix applies Deterministic fixes and reports the rest. [[check.tool]] stages run external tools through gob-exec after the built-in rules and are timed separately (outside the 2 s budget). Emit a timing breakdown with -v and a telemetry line to .frob/telemetry.jsonl (knob). Bench: criterion harness running the full check on this repository, asserting a warm fresh-process run under 2 s on the CI profile (soft gate: record, fail only when [perf] enforce = true).