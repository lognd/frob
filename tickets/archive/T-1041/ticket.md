---
id: T-1041
title: 'PERF005/PERF008 residue burn-down: 20 findings across arch/perf/vet/gates/testing'
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/arch/_concurrency_model.py
- src/frob/arch/_ocp.py
- src/frob/arch/_python.py
- src/frob/arch/_rust.py
- src/frob/arch/_async_hazards.py
- src/frob/perf/_effect_summaries.py
- src/frob/perf/_hotgraph.py
- src/frob/vet/_capability.py
- src/frob/gates/__init__.py
- src/frob/gates/_fmt_directives.py
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/_secrets.py
- src/frob/testing/_collect.py
- tests/test_serve.py
- tests/unit/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_scan_finds_a_synthetic_rule_id
- tests/test_gates.py::test_gates_run_gates_integration
- tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render
- tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_fully_resolvable_call_path_has_no_unknown_member
- tests/test_perf.py::test_perf_end_to_end_profile_load_and_heat
- tests/test_serve.py::test_warm_state_rebuilds_iff_tree_changed
- tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes
designated_repro_test: null
threat: null
component: null
---
Burn down the repo-wide PERF005 (recursion without a provable termination
measure, 9 findings) and PERF008 (loop-invariant call inside a loop, 11
findings) warning residue -- not build-blocking today, but real perf/
correctness debt worth clearing per the coordinator's standing burn-down
directive under T-0204.

PERF005 (9): src/frob/arch/_concurrency_model.py:250,
src/frob/arch/_ocp.py:178, src/frob/arch/_python.py:576,
src/frob/arch/_rust.py:712, src/frob/perf/_effect_summaries.py:457,
src/frob/perf/_effect_summaries.py:509, src/frob/perf/_hotgraph.py:301,
src/frob/vet/_capability.py:3297, src/frob/vet/_capability.py:4721.

PERF008 (11): src/frob/arch/_async_hazards.py:158,
src/frob/gates/__init__.py:9313, src/frob/gates/__init__.py:6723,
src/frob/gates/__init__.py:3275, src/frob/gates/_fmt_directives.py:298,
src/frob/gates/_rule_id_scan.py:133, src/frob/gates/_secrets.py:876,
src/frob/testing/_collect.py:150, src/frob/vet/_capability.py:3057,
src/frob/vet/_capability.py:1479, tests/test_serve.py:547.

For PERF005: add the suggested `frob:invariant` termination-measure
annotation where the recursion genuinely terminates (prove-or-justify
posture, T-0952 precedent), or convert to iterative where that is
cleaner.

For PERF008: hoist the loop-invariant call (usually a compiled regex or
a repeated lookup) out of the loop -- real micro-fixes, not waivers.

Lease caution: `src/frob/gates/**` and `src/frob/vet/**` may be actively
landing from sibling agents/tickets at dispatch time -- re-verify their
ticket state is done/landed (and re-merge main) before touching those
two files' worth of findings; leave any still-blocked finding an
explicit, counted residue in the Done report rather than force it.