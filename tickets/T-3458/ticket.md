---
id: T-3458
title: SYS101/SYS111 self-conformance scan cost scales with design/frob.strata's largest
  via-list x repo file count
state: in-progress
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_selfconform_kinds.py
- src/frob/strata/_effects.py
- tests/unit/strata/test_effects.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_effects.py
  reason: profiling test_sys_gate_zero_violations (cProfile over sys_gate) shows the
    real O(files x globs) fnmatch hot path is _effects.py::_via_matches_site/_via_matches
    (4.5M fnmatch calls, ~40s cumulative, largely os.path.normcase overhead repeated
    per call), not _selfconform_kinds.py::_fully_excluded_node_ids (measured 0.303s
    of the ~50s total, not the bottleneck this ticket's own filing hypothesized)
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: profiling test_sys_gate_zero_violations (cProfile over sys_gate) shows the
    real O(files x globs) fnmatch hot path is _effects.py::_via_matches_site/_via_matches
    (4.5M fnmatch calls, ~40s cumulative, largely os.path.normcase overhead repeated
    per call), not _selfconform_kinds.py::_fully_excluded_node_ids (measured 0.303s
    of the ~50s total, not the bottleneck this ticket's own filing hypothesized)
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3449 (round 2, coordinator-directed A/B re-measurement).

MEASURED directly (git worktree scratch checkouts, natives built, single-threaded -p no:xdist,
quiet box, load < 2 at measurement time):
  test_sys_gate_zero_violations:
    b94cea5d0: 49.75s, 48.36s (2 runs)
    ac5c2ae67: 50.23s
    current main (T-3457 landed): 49.68s, 49.45s (2 runs)
  test_fragments_module_fs_read_is_declared_not_selfaudit001:
    b94cea5d0: 68.47s
    ac5c2ae67: 67.65s

CONCLUSION on T-3449's original premise: there is NO wall-time regression between b94cea5d0
and ac5c2ae67 for either test -- all four measurements above land within a ~2s band per test,
nowhere near the 2x-4x the coordinator's revised hypothesis proposed for that specific
30-commit range. T-3449 is failed again (round 2) on this basis: there is no culprit commit to
bisect in that range because the two endpoints are statistically identical locally.

REAL COST DRIVER (this ticket): design/frob.strata's testsuite node's `may "exec" via ...`
list has organically grown to 250+ literal file-path glob entries (one new entry appears
between ac5c2ae67 and 462489d97 alone: tests/unit/test_check_admission.py) as the project has
added test files over its whole history -- NOT introduced by any single commit. `_selfconform_
kinds.py::_fully_excluded_node_ids` does, per node with a non-empty glob set: `matched = [rel
for rel in all_files if any(fnmatch.fnmatch(rel, g) for g in globs)]` -- O(files x globs) per
node, so the testsuite node alone costs ~8500 files x ~250 globs = ~2.1M fnmatch calls, and
this is repeated (not cached) on every sys_gate/build_graph call within a single test AND
across every test in the file that calls build_graph(_REPO_ROOT, ...) fresh. Compounded by
_repo_files_excluding_skip_dirs's own os.walk cost. This ~60-70s-per-call baseline cost
(vs. the ~27s the test's own docstring cites as its original baseline, likely measured when
the via-list was much shorter and/or fewer repo-wide files existed) is the ambient, ever-
growing cost -- and CI's own xdist-parallel workers on a 3-4 core runner each pay this same
cost SIMULTANEOUSLY and compete for the same limited cores, which is a plausible explanation
for CI wall time far exceeding any single local measurement (unmeasured here: reproducing
actual GH Actions runner contention is out of this investigation's reach without a live
runner).

SUGGESTED FIX (not applied by this ticket -- filed for scoping/prioritization, not attempted
here per T-3449's narrow scope and this investigation's time budget): memoize per-node
matched-file results across the SAME _fully_excluded_node_ids call (already single-call
memoization has no reuse target since it's called once per invocation), or restructure the
per-node scan to walk all_files ONCE and test membership against a compiled glob automaton
(e.g. group globs by directory prefix, or use pathspec's compiled matcher) instead of
O(files x globs) naive fnmatch -- an asymptotic win regardless of via-list size. A second,
independent, orthogonal mitigation: CI could lower the sys_gate/build_graph test class's own
xdist worker count via a dedicated xdist_group (already used: frob_self_scan_heavy) with an
explicit concurrency cap, so these already-CPU-heavy tests do not all run at once on a
constrained runner -- outside this ticket's scope (CI workflow config, not code).
