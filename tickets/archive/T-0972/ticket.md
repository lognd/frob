---
id: T-0972
title: 'Burn-down: PERF001-004 to zero unwaived, then promote to ERROR (1730 findings)'
state: done
kind: bug
origin: auditor
created: '2026-07-27'
priority: medium
parent: T-0969
tier: ticket
sprint: null
scope:
- src/**
- tests/**
- frob.toml
- docs/modules/arch.md
- docs/modules/gates.md
- docs/modules/graph.md
- docs/modules/perf.md
- docs/modules/vet.md
- docs/strata/kernel.md
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: PERF001-004 burn-down requires flipping [gates.severity] in frob.toml once
    unwaived count is zero, same as T-0971/T-0973 precedent
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/arch.md
  reason: AFFECT001 requires touching the affects()-closure docs for every function
    whose body picked up a T-0972 frob:waive PERF00X marker
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 requires touching the affects()-closure docs for every function
    whose body picked up a T-0972 frob:waive PERF00X marker
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/graph.md
  reason: AFFECT001 requires touching the affects()-closure docs for every function
    whose body picked up a T-0972 frob:waive PERF00X marker
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/perf.md
  reason: AFFECT001 requires touching the affects()-closure docs for every function
    whose body picked up a T-0972 frob:waive PERF00X marker
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/vet.md
  reason: AFFECT001 requires touching the affects()-closure docs for every function
    whose body picked up a T-0972 frob:waive PERF00X marker
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/strata/kernel.md
  reason: AFFECT001 requires touching the affects()-closure docs for every function
    whose body picked up a T-0972 frob:waive PERF00X marker
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/strata/surface.md
  reason: AFFECT001 requires touching the affects()-closure docs for every function
    whose body picked up a T-0972 frob:waive PERF00X marker
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_collects_at_least_one_sample_over_a_hot_loop
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestOverBroadExcept::test_bare_except_flagged
- tests/unit/test_arch.py::TestDataClumps::test_same_three_keyword_group_at_three_sites_flagged
- tests/unit/test_arch.py::TestTemporalCoupling::test_guard_clause_on_initialized_flag_flagged
- tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_added_guard_raise_on_shared_param_flagged
- tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_cross_field_guard_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_manual_callback_list_recommends_observer
- tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_missing_member_flagged
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_idempotent_on_already_canonical_text
- tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
- tests/test_graph_affects.py::TestAffects::test_transitive_uses_contract_chain
- tests/test_graph_lock.py::TestAckDrift::test_acknowledge_records_every_describes_facet
- tests/test_graph.py::test_graph_build_lock_drift_integration
- tests/unit/perf/test_advisories.py::TestExternalCallAdvisories::test_dominant_external_edge_fires
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_leaf_in_loop_body_attributes_to_loop_section
- tests/unit/strata/test_demand.py::TestAggregateDemand::test_two_entry_nodes_sum_at_fan_in
- tests/unit/strata/test_design_load.py::TestUnbound::test_bound_excluded
- tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavigable::test_every_member_cross_refs_every_other_member
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_covers_docstring_and_comment
- tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_over_this_repos_own_arch_tree
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns
designated_repro_test: null
threat: null
component: null
---
gates-quality audit (T-0399) finding 1: PERF001-004 are WARN and never
block `frob check`. Live measured count on main (chunked `gates-native`,
2026-07-27): 1730 unwaived PERF001-004 warnings repo-wide (30 already
carry a reasoned frob:waive). Owner-gate: PERF001-004 in [gates.severity].

Plan: triage the 1730 findings file-by-file -- real O(n^2)/hoist-able
smells get fixed; genuine false positives/non-hot-path hits (see audit
findings 8/9 on PERF's lexical/indentation blindness) get a reasoned
`frob:waive PERF00# reason="..."`. Once the unwaived count is at or near
zero, flip [gates.severity] PERF001 = "error" (and 002/003/004 once each
family is clear) in frob.toml.