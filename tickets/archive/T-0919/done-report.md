## Done report

Deduped the two serial full `frob check --ticket <id>` spawns inside
done-report/land (_shared_check_spawn_fn caches one guarded_subprocess_run
result, shared between _check_gates_summary_fn and _check_gate_findings_fn),
cutting frob ticket done-report's own foreground cost roughly in half.
Per the repo owner's explicit directive, also encoded the anti-pattern in
both layers: REL31x INTERACTIVE-COST-BOUND obligation (_interactive_cost.py,
docs/strata/reliability.md) at the structural/.strata layer, and PERF012
duplicate-identical-subprocess-spawn detector (_dup_spawn.py, extending the
shared _EffectGraph substrate in _loop_effects.py for full interprocedural
propagation, docs/modules/perf.md) at the code/perf layer, both with
true-positive/false-positive test coverage.

### Changed
```
 docs/modules/perf.md                           |  66 +++++-
 docs/strata/reliability.md                     |  63 ++++++
 src/frob/app/ticket_runner.py                  | 157 ++++++++-----
 src/frob/perf/_dup_spawn.py                    | 287 ++++++++++++++++++++++++
 src/frob/perf/_loop_effects.py                 | 241 ++++++++++++++++++--
 src/frob/perf/_rules.py                        |  49 +++--
 src/frob/strata/__init__.py                    |  14 ++
 src/frob/strata/_interactive_cost.py           | 294 +++++++++++++++++++++++++
 tests/unit/perf/test_dup_spawn.py              | 182 +++++++++++++++
 tests/unit/strata/test_interactive_cost.py     | 155 +++++++++++++
 tests/unit/test_ticket_runner_gate_findings.py |  88 ++++++++
 tickets.md                                     | 209 +++++++++++++++++-
 12 files changed, 1717 insertions(+), 88 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_second_call_does_not_spawn_again` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_default_spawn_none_keeps_each_closure_independent` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_identical_subprocess_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_different_subprocess_args_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_single_helper_call_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_call_site_varying_argument_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost::test_interactive_node_without_bounded_cost_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost::test_discharged_and_non_interactive_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_spawn_kwargs_capture_output_text_and_no_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
