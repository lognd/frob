---
id: T-5190
title: known-gate-rule-id registry has grown to 17 unregistered ids (CI run 35510697497
  burn-down)
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
blocked_by:
- T-4113
- T-5121
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/design/registry/check-coverage.yaml
  reason: 'narrowing per coordinator directive: register 15/17 ids directly instead
    of waiting on T-4113'
  actor: logan
  at: '2026-09-21'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
body_changes:
- mode: append
  reason: record real double-lease blocker found while trying to narrow scope per
    coordinator directive
  actor: logan
  at: '2026-09-21'
  old_length: 1575
  new_length: 2634
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while burning down CI run 35510697497 (dev @ e99570be, ancestor of dev tip 4483b1da29). Re-verified on current dev tip (not stale). tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known and tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules both fail: frob.gates._rule_id_scan.generated_gate_rule_ids() now reports 17 rule ids constructed in src/frob/gates or src/frob/strata that are missing from _KNOWN_GATE_RULES / check-coverage.yaml: BASE001 (_ratchet.py:335), GUARD001 (_guard_closure.py:263), WRAP001/002/003 (_wrapper_drift.py), INV010/011 (_inv.py / _design_invariants.py), SYS114/SYS115 (_outbound_destination.py -- these two are owned by in-progress T-4113, which will register them itself), CONFIGPATH001 (_config_path_defaults.py:196), REL303 (_inbound_rate.py:172), RACE001/002 (_inv.py), PII013 (_pii_structural/__init__.py:248), CLAIM001 (_claim_lint.py:139), ROUTE001 (_route_response_model.py:155), TESTMOCK001 (_coverage.py:1816), COV010 (_coverage.py:1473). This is broader than T-3278 (which only covers 3 stale check-coverage.yaml entries in the OTHER direction -- yaml entries with no live rule) and overlaps docs/design/registry/check-coverage.yaml scope with in-progress T-4113 (SYS114/SYS115). BLOCKED on a lease collision with T-4113 when attempting frob ticket work T-3278 directly; this ticket tracks the now-larger drift for whoever picks it up once T-4113 lands or narrows scope. Do NOT touch SYS114/SYS115 here -- T-4113 owns those.

Attempted to narrow scope directly (coordinator directive, not waiting on T-4113): _KNOWN_GATE_RULES actually lives in src/frob/gates/_waive.py (not __init__.py -- __init__.py only re-exports it). Both files this fix needs are genuinely double-leased by OTHER in-progress tickets right now, not just T-4113: (1) src/frob/gates/_waive.py is held by in-progress T-5121 (TICK rule: requeue dead-worktree tickets, also touching _waive.py to register its own new rule id) -- 'scope --add' refused with ScopeLeaseConflict. (2) docs/design/registry/check-coverage.yaml is held by in-progress T-4113 as originally noted. Both entries in gate_rule_entries and _KNOWN_GATE_RULES must move in lockstep (test_gate_rule_entries_match_live_known_rules asserts len(entries)==len(known) and every target in known), so this ticket cannot land a partial fix touching only one side. blocked_by now includes both T-4113 and T-5121; whoever picks this up next should re-check both leases first (one or both may have released by then) rather than re-attempting scope --add blind.