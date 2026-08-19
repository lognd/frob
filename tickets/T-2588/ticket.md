---
id: T-2588
title: frob cycle reports a false CLEAN on the natural invocation and exits 0 on findings
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/app/cycle_runner.py
- src/frob/cycle/graph.py
- src/frob/cycle/__init__.py
- tests/unit/test_app_runners_batch5.py
- tests/unit/test_cycle_runner_root_resolution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: 'T-2588: test files touched by the root-resolution fix (new coverage plus
    collateral repair of pre-existing TestCycleRunner fixtures)'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/test_cycle_runner_root_resolution.py
  reason: 'T-2588: test files touched by the root-resolution fix (new coverage plus
    collateral repair of pre-existing TestCycleRunner fixtures)'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_naive_relative_resolution_would_have_missed_this
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_agree_on_a_real_cycle
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_stay_clean_on_an_acyclic_tree
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_unresolvable_path_refuses_instead_of_reporting_clean
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_run_exits_nonzero_on_a_found_cycle
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_run_exits_zero_on_a_clean_tree
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_run_exits_nonzero_error_on_unresolvable_path
- tests/unit/test_app_runners_batch5.py::TestCycleRunner::test_cycle_found_with_suggest
designated_repro_test: tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_naive_relative_resolution_would_have_missed_this
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured, same tree, same commit, back to back

    uv run frob cycle src/frob   ->  "no cycles found"            EXIT=0
    uv run frob cycle src        ->  7 cycles, one of 160 nodes   EXIT=0

Two defects, both in the `cycle` CLI path. The gate pipeline
(`frob check --only cycle`) independently finds the same 7 cycles, so the
DETECTOR is sound -- it is the command a human or agent actually runs that
is wrong.

## Defect 1 (critical): the natural invocation reports a false CLEAN

Pointing at the package directory -- the obvious thing to type -- yields
"no cycles found" on a tree containing a live 160-node SCC that
`CYCLE001` currently errors on.

Near-certain cause: module names are resolved RELATIVE to the given path.
With `src/frob` as root, an `import frob.x` does not resolve to a node in
the graph, unresolved imports contribute no edges, and a graph with no
edges has no cycles. With `src` as root, `frob.x` resolves and the edges
appear. Verify this before fixing; do not assume it.

This is the repo's dominant bug class in its purest form: "matcher never
fired" rendered as "nothing to find". The output is indistinguishable from
a genuinely acyclic tree, and it is the reason an agent working T-2363
initially disbelieved a real cycle. See also T-2195, which fixed
src-layout resolution in `resolve_local_import` -- this is the same
src-layout blind spot surviving on a different code path.

## Defect 2: exit code is 0 on findings

`frob cycle src` printed 7 cycles and still exited 0. The command cannot be
used in any gate, hook, or script, and a caller checking only the exit
status sees success. A findings command must exit nonzero when it has
findings.

## Required fix shape

- Resolve the package root correctly regardless of which directory the
  user points at -- walk up past `src/`, or read the project layout, so
  `frob cycle src/frob`, `frob cycle src`, and `frob cycle .` agree.
- If a path genuinely cannot be resolved into an import root, REFUSE with
  an error. Never print "no cycles found" for a tree whose imports did not
  resolve -- that is the silent zero. Distinguish "measured, none present"
  from "could not resolve, did not measure" in the OUTPUT TEXT, not just
  internally.
- Exit nonzero when cycles are found.

## Positive controls, both directions -- MANDATORY here

This command has already shipped a false clean twice (T-2195, and again
now), so a fix asserted without a must-fail fixture is not acceptable.

- `frob cycle src/frob`, `frob cycle src`, and `frob cycle .` must all
  report the SAME cycle set on this repo, and it must be non-empty today
- a genuinely acyclic fixture tree must still report clean, from every one
  of those path shapes -- otherwise the fix is just "always report cycles"
- a planted 2-node cycle must be detected from every path shape (reuse
  `tests/unit/test_capability_and_deploy_cycle_regression.py::TestPlantedCycleStillDetected`)
- an unresolvable/garbage path must ERROR, not report clean
- exit code must be nonzero for the findings case and zero for the clean case

## Note

This command also emits the full per-file DEBUG parse stream to stdout
("extracted 51 import specifiers from ...") before its answer -- the same
flood filed as T-2582. Do not fix that here; it is that ticket's scope.