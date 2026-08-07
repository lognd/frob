---
id: T-0598
title: 'gate:ARCH: resolve 17 unwaived warnings (distinct from T-0393/T-0394/T-0395
  suggestion triage)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires
- tests/test_gates.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_calls_the_bound_symbol
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_fires_on_cross_file_same_test_collision
- tests/test_gates.py::TestTest015VacuousCredit::test_fires_on_no_op_test_body
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_missing_row_for_real_command_fails
- tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_missing_sunset_is_malformed
- tests/test_perf.py::TestPerf007RedundantComputation::test_two_stages_calling_the_same_uncached_parse_is_flagged
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_declared_entry_is_loaded
- tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
designated_repro_test: null
threat: null
component: null
---
gate:ARCH currently reports 0 errors, 17 warnings, 0 waived (frob-arch tool summary: 18 warnings, 79 suggestions; measured 2026-07-22). T-0393 (abstraction-opportunity advisories), T-0394 (deep-nesting advisories), T-0395 (large-file advisories) already cover the SUGGESTIONS tier -- this ticket is the WARNINGS tier, which none of those three touch. Run frob check --only arch (or grep '[gate:ARCH]' from frob check output) to enumerate the current 17 warning sites, classify each by its ARCH rule id, and for each either fix the underlying design issue or add a frob:waive with an honest reason. Acceptance: gate:ARCH summary line reports 0 unwaived warnings (fixed or waived-with-reason), no threshold loosened without a disclosed decision.