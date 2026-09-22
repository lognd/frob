---
id: T-5261
title: Tier-A fix for redundant production-side frob:tests declarations (T-4710 follow-up)
state: in-progress
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_waive.py
- src/frob/gates/_fix_engine.py
- tests/test_gates_fix_engine.py
- tests/gates_suite/test_fix_engine.py
- docs/modules/gates.md
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'coordinator instruction: register the redundant-test-declaration Tier-A
    fix in TIER_A_HANDLERS (run_gates already wires TEST010 via _test010_violations,
    no gates/__init__.py change needed) plus its own positive-control test'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: 'coordinator instruction: register the redundant-test-declaration Tier-A
    fix in TIER_A_HANDLERS (run_gates already wires TEST010 via _test010_violations,
    no gates/__init__.py change needed) plus its own positive-control test'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: tests/gates_suite/test_fix_engine.py
  reason: existing exhaustive TIER_A_HANDLERS-set pin test needs TEST010 added, since
    this ticket registers a new handler
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/modules/gates.md
  reason: Tier-A handler doc section for the new TEST010 redundant-test-declaration
    fix
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/gates/__init__.py
  reason: _KNOWN_RULE_FIXABILITY needs TEST010=auto, guarded by TestRuleFixability
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5261
branch: t-5261
---
found while working T-4710: frob.graph._redundant_test_declarations (src/frob/graph/__init__.py) now lints a frob:tests directive still declared on the production symbol as redundant (delete when a test-side declaration already exists, move-with-refusal when it does not, per T-4710's move-semantics amendment). T-4710's own scope is src/frob/graph/* only, so the Tier-A auto-fix handler (frob.gates._fix_engine_text, dispatched via TIER_A_HANDLERS) was left unbuilt; this ticket is that handler plus its _KNOWN_GATE_RULES registration and frob.toml severity.