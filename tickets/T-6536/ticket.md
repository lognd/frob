---
id: T-6536
title: web rule modules print progress to stdout from library calls; route through
  the module logger
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: medium
parent: T-5140
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
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
- src/frob/webapp/_websec_sinks.py
- src/frob/gates/_a11y_gate.py
- src/frob/gates/_taint_gate.py
- tests/unit/test_webapp_no_stdout.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-395: calling `taint_gate(Path('frontend'))` and `a11y_gate` from Python prints ~226 lines like 'websec_sinks: 32 finding(s) under ...' and 'a11y_findings: 0 violation(s) in X' to stdout, plus a WARNING that `_a11y_substrate` matches the hook prefix but exposes no a11y_findings. Deliver: every such line moves to the module logger at DEBUG/INFO (RENDER001 already forbids bare stdout writes; extend its coverage to these modules), the substrate-prefix warning is silenced for modules that intentionally expose no hook, and a test captures stdout across a gate call and asserts it is empty.
