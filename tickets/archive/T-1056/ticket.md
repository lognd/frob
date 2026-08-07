---
id: T-1056
title: 'EXHAUST001/002 turn-on debt burn-down: 176 residual escape-hatch sites after
  T-1022'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol
- tests/test_gates.py::TestTestGate::test_changelog_mentions_rejects_substring_in_prose
- tests/test_gates.py::TestTestGate::test_changelog_mentions_accepts_real_heading_entry
- tests/test_gates.py::TestComplianceGate::test_compliance005_registered_in_known_gate_rules
- tests/test_gates.py::TestComplianceGate::test_compliance005_fires_on_deferred_disposition
- tests/test_gates.py::TestComplianceGate::test_compliance005_silent_on_handled_by_and_out_of_scope
- tests/test_gates.py::TestComplianceGate::test_compliance005_missing_registry_dir_is_silent
- tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes
- tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry
- tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption
- tests/test_arch_gate.py::TestArchGateWaivers::test_ceiling_refires_when_grown_past_it
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_forward_progress_across_a_merge_is_clean
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_non_merge_commit_never_checked
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_archived_ticket_is_not_flagged
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_missing_worktree_reports_once_with_path_and_remedy
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_live_worktree_is_silent
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_five_stale_leases_each_reported_exactly_once
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_no_leases_directory_is_silent
- tests/test_decisions.py::test_dec001_dangling_decision_edge
- tests/test_decisions.py::test_dec002_accepted_decision_unanchored
- tests/test_decisions.py::test_accepted_and_anchored_passes
- tests/test_decisions.py::test_no_decisions_dir_skips
- tests/test_decisions.py::test_never_adopted_decisions_dir_is_silent
- tests/test_decisions.py::test_deleted_after_adoption_fires_dec003
designated_repro_test: null
threat: null
component: null
---
T-1022 closed a partial slice of the EXHAUST001/002 turn-on debt (190 -> 176
sites: predecessor's 9-file boundary-scan pass plus this pass's
check/_native.py tool_crash_result refactor, 14 sites total). 176 sites
remain (122 EXHAUST001 unresolvable-escape, 54 EXHAUST002 named-escape),
concentrated in:

  17 src/frob/gates/__init__.py
   8 src/frob/gates/_coverage.py
   6 src/frob/dup/_pipeline.py
   6 src/frob/tickets/_leases.py
   5 src/frob/deploy/_conform.py
   5 src/frob/mutate/__init__.py
   5 src/frob/outline/__init__.py
   5 src/frob/strata/_claims.py
   5 src/frob/tickets/__init__.py
   5 src/frob/vet/_capability.py
   ...remainder spread thinner across app/gates/check/strata modules.

Get the live per-file/per-code breakdown from
`uv run frob check --only exhaustive_handling --json` (gate:EXHAUST
diagnostics). Each site gets either a truthful frob:raises/
frob:callee-raises annotation (verify the callable can actually raise
what's declared), a real errors-as-values refactor (ToolResult/typani
Result at the fallible boundary, matching the tool_crash_result()
precedent this ticket's pass landed in
process/parsers/common.py/check/_native.py), or a reasoned frob:waive.