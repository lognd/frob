---
id: T-2447
title: Register CLAUDE001 gate rule id in _waive.py _KNOWN_GATE_RULES
state: dropped
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
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
Repo-wide audit (T-2441's own "check for other unregistered gate rule
ids" follow-up) using the existing
frob.gates._rule_id_scan.find_unregistered_rule_ids scanner against
every live worktree found one more gap beyond T-2388's bare PORT001:

  CLAUDE001  src/frob/app/check_runner.py:481

Constructed via Diagnostic(code="CLAUDE001", ...) in
frob.app.check_runner (drift_report wiring, .claude/hooks/
sync-claude-config.py drift detection), currently in the live
`rule-bookkeeping` worktree (owned by in-progress T-1686/T-1970 -- not
touched here, this worktree's file is outside this ticket's own
scope/lease).

Register "CLAUDE001" in src/frob/gates/_waive.py's _KNOWN_GATE_RULES
once that worktree's change lands (or coordinate with whoever owns
T-1686/T-1970 to add it in their own change, matching the PORT001-PATH/
PORT001-IDENT precedent T-2441 follows for T-2388).

## Drop reason
- 2026-08-18: CLAUDE001 was already registered in _KNOWN_GATE_RULES by T-1969 (commit 5dd2b319c, landed independently), confirmed via a fresh find_unregistered_rule_ids(main) scan returning no CLAUDE001 hit. The rule-bookkeeping worktree this finding came from is unrelated to the fix -- CLAUDE001's construction (src/frob/app/check_runner.py) was already on main, the worktree reference in this ticket's body was incidental to where the gap was first noticed, not where the fix needed to land.
