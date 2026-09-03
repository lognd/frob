---
id: T-3727
title: GATERULE001 fires on downstream repos own lint rule-ids not waivable (apollo)
state: done
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_rule_id_scan.py
- tests/gates/test_rule_id_scan_branches.py
- docs/modules/gates.md
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_rule_id_scan.py
  reason: GATERULE001 must only fire against frob own checkout (is_frob_own_repo),
    not downstream repos own rule-id catalogs
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/gates/test_rule_id_scan_branches.py
  reason: include the GATERULE001 branch-coverage test file and its own doc for the
    is_frob_own_repo scoping fix
  actor: logan
  at: '2026-09-03'
- op: add
  glob: docs/modules/gates.md
  reason: include the GATERULE001 branch-coverage test file and its own doc for the
    is_frob_own_repo scoping fix
  actor: logan
  at: '2026-09-03'
- op: add
  glob: frob.lock
  reason: frob ack writes acknowledgment digests into frob.lock
  actor: logan
  at: '2026-09-03'
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryDownstreamRepoExemption::test_downstream_repo_with_own_rule_catalog_is_silent
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryDownstreamRepoExemption::test_downstream_repo_declaring_a_different_project_name_is_silent
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryDownstreamRepoExemption::test_frobs_own_repo_still_scanned
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_unregistered_id_reported_as_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: GATERULE001 demands PREFIX+digits literals be in _KNOWN_GATE_RULES; downstream lint catalogs (COLOR001/SPACE001) trip it, frob:waive GATERULE001 not honored (T-2448). Fix: apply only to frob own repo or honor downstream rule-id namespace.