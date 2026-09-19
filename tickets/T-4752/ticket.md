---
id: T-4752
title: 'Claude Code hooks: 10% precision on frob-suggest, double registration doubles
  the attempt counter, blind FROB_SUGGEST_ACK on 97% of uses, no logging'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: story
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: story is a tracking parent; work happens in 4 leaf tickets
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Audit at scratchpad/HOOK-AUDIT.md. frob-suggest.py precision 10.4%, dual hook registration double-counts attempts per Bash call, FROB_SUGGEST_ACK is a blind blanket bypass used blindly in 97.3% of uses, hook logs nothing. Story tracks 4 leaves: registration/counter fix, rule verdict narrowing, per-rule ack token, and decision logging.