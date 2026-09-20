---
id: T-draft-706ae266
title: 'frob-suggest: log every block/allow/ignored-ack decision to .frob/telemetry.jsonl'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: T-draft-8c7e665d
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/*
- tests/test_hook_frob_suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: '2026-09-19: cross-story file contention on .claude/hooks/tool-call-telemetry.py'
  actor: logan
  at: '2026-09-19'
  old_length: 69
  new_length: 469
designated_repro_test: null
acceptance:
- text: every block, allow, and ignored-ack decision appends a kind=hook row to .frob/telemetry.jsonl
    with hook, rule, agent, command shape, and decision
  evidence: []
- text: logging uses the repo logging conventions and is proven by a test
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf 4 of T-draft-8c7e665d. See scratchpad/HOOK-AUDIT.md section 3.3.

ORDERING NOTE (coordinator via planner, 2026-09-19): T-4689 (story T-4687, CLI debloat) also edits .claude/hooks/tool-call-telemetry.py, which this ticket's scope glob .claude/hooks/* covers, and T-4689 LANDS FIRST. It adds verb and subverb fields to the telemetry rows this hook writes. Build the kind=hook decision rows on those fields rather than defining a second row shape for the same stream.