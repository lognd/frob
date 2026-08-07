---
id: T-0712
title: hot-graph query surface + slow-operation advisories + perf regression ratchet
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0710
- T-0711
parent: T-0709
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/app/**
- src/frob/gates/**
- docs/modules/perf.md
- tests/unit/perf/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/perf/**
  reason: new tests for T-0712's query surface/advisories/ratchet; T-0710/T-0711's
    own scope precedent included tests/unit/perf/
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label
- tests/unit/perf/test_ratchet.py::TestCheckRatchet::test_regression_beyond_tolerance_fires
- tests/unit/perf/test_gate_wiring.py::TestPerf008ProductionInvocation::test_before_no_effect_fails_to_find_perf008
- tests/unit/perf/test_gate_wiring.py::TestPerf008ProductionInvocation::test_after_loop_invariant_fs_walk_passes_perf008
- tests/unit/perf/test_gate_wiring.py::TestPerf009ProductionInvocation::test_before_no_findings_file_fails_to_find_perf009
- tests/unit/perf/test_gate_wiring.py::TestPerf009ProductionInvocation::test_after_regression_finding_passes_perf009
- tests/unit/perf/test_persist_run_cli.py::TestPersistRunDefaultPath::test_missing_perf_path_resolves_to_cwd
- tests/unit/perf/test_persist_run_cli.py::TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight
- tests/unit/perf/test_persist_run_cli.py::TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order
- tests/unit/perf/test_persist_run_cli.py::TestRatchetFindingRendering::test_regression_prints_label_and_exact_percentage
designated_repro_test: null
acceptance:
- text: GIVEN a section whose p90 regresses beyond tolerance vs the stored prior WHEN
    frob check runs with the ratchet enabled THEN a PERF finding names the section
    and both decile sets; GIVEN a loop dominated by an external call THEN an advisory
    fires with the edge's deciles
  evidence:
  - tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label
  - tests/unit/perf/test_ratchet.py::TestCheckRatchet::test_regression_beyond_tolerance_fires
- text: T-0756 new-gate-rule fixture proof for PERF008/PERF009 (registered in _KNOWN_GATE_RULES
    this change) -- a fixture with no loop-invariant effect / no ratchet-findings
    artifact FAILS to find PERF008/PERF009 through frob.gates.perf_gate (the production
    function frob check invokes) BEFORE the triggering fixture is introduced, and
    PASSES (finds the rule) AFTER the fixture is added -- proven through the real
    gate invocation, not a pure-function unit test alone
  evidence:
  - tests/unit/perf/test_gate_wiring.py::TestPerf008ProductionInvocation::test_before_no_effect_fails_to_find_perf008
  - tests/unit/perf/test_gate_wiring.py::TestPerf008ProductionInvocation::test_after_loop_invariant_fs_walk_passes_perf008
  - tests/unit/perf/test_gate_wiring.py::TestPerf009ProductionInvocation::test_before_no_findings_file_fails_to_find_perf009
  - tests/unit/perf/test_gate_wiring.py::TestPerf009ProductionInvocation::test_after_regression_finding_passes_perf009
  - tests/unit/perf/test_persist_run_cli.py::TestPersistRunDefaultPath::test_missing_perf_path_resolves_to_cwd
  - tests/unit/perf/test_persist_run_cli.py::TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight
  - tests/unit/perf/test_persist_run_cli.py::TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order
  - tests/unit/perf/test_persist_run_cli.py::TestRatchetFindingRendering::test_regression_prints_label_and_exact_percentage
threat: null
component: null
---
Child 3: consumers. (1) QUERY: frob perf hot [--top N --by p90|p50xcount] renders the hot-graph (section, callee edge, decile readout, sample count) from the sketch store; MCP tool mirror for agents. (2) ADVISORIES (suggestion tier, T-0332 noise discipline): external call edge dominating a loop body's time -> batch/cache/move-out-of-loop suggestion naming the edge and its deciles; nested-loop section hot AND upstream of a fan-in -> complexity suspect; section p90 >> p50 (heavy tail) -> variance advisory naming likely modes. (3) REGRESSION RATCHET: current run sketch vs stored prior -- quantile shift beyond alpha + configured tolerance = PERF finding naming the section and both deciles (ratchet-pool style per T-0569/T-0594 precedent, baseline-old error-new).