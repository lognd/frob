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
sprint: null
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