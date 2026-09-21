---
id: T-draft-06eaaa96
title: known-gate-rule-id registry has grown to 17 unregistered ids (CI run 35510697497
  burn-down)
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
blocked_by:
- T-4113
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while burning down CI run 35510697497 (dev @ e99570be, ancestor of dev tip 4483b1da29). Re-verified on current dev tip (not stale). tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known and tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules both fail: frob.gates._rule_id_scan.generated_gate_rule_ids() now reports 17 rule ids constructed in src/frob/gates or src/frob/strata that are missing from _KNOWN_GATE_RULES / check-coverage.yaml: BASE001 (_ratchet.py:335), GUARD001 (_guard_closure.py:263), WRAP001/002/003 (_wrapper_drift.py), INV010/011 (_inv.py / _design_invariants.py), SYS114/SYS115 (_outbound_destination.py -- these two are owned by in-progress T-4113, which will register them itself), CONFIGPATH001 (_config_path_defaults.py:196), REL303 (_inbound_rate.py:172), RACE001/002 (_inv.py), PII013 (_pii_structural/__init__.py:248), CLAIM001 (_claim_lint.py:139), ROUTE001 (_route_response_model.py:155), TESTMOCK001 (_coverage.py:1816), COV010 (_coverage.py:1473). This is broader than T-3278 (which only covers 3 stale check-coverage.yaml entries in the OTHER direction -- yaml entries with no live rule) and overlaps docs/design/registry/check-coverage.yaml scope with in-progress T-4113 (SYS114/SYS115). BLOCKED on a lease collision with T-4113 when attempting frob ticket work T-3278 directly; this ticket tracks the now-larger drift for whoever picks it up once T-4113 lands or narrows scope. Do NOT touch SYS114/SYS115 here -- T-4113 owns those.