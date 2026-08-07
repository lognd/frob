## Done report

Land review refused T-0712: TEST016 found the original bound evidence
killed 0/8 mutants in src/frob/app/perf_runner.py's changed lines
(_persist_run/_hot_sort_key/_print_findings) -- confirmatory-only, not
adversarial. Added tests/unit/perf/test_persist_run_cli.py: four
behavioral tests invoking `frob.app.perf_runner.run` directly (the same
production function `frob perf collect`/`frob perf hot` dispatch through)
and asserting on precise rendered stdout/JSON values.

Manually verified each targeted mutant is killed by applying it, running
the new tests, confirming failure, then reverting:
- line 397 `cfg.perf_path or Path(".")` -> `and`: AttributeError on
  None.resolve(), test_missing_perf_path_resolves_to_cwd fails.
- line 403 `== UNATTRIBUTED_SECTION_ID` -> `!=`: store stays empty,
  test_only_attributed_section_persists_with_summed_weight fails
  (len(rows) != 1).
- line 405 `+= hit.weight` -> `-=`: negative total dropped by
  add_value's non-negative guard, same test fails (p50 reads 0 not ~2.0).
- line 437/438/439 advisories list `+` -> `-` (both operators): TypeError
  crashes every collect-invoking test immediately.
- line 454 `finding.label or finding.section_key` -> `and`: renders the
  opaque hash key instead of the label, test_regression_prints_label_and_
  exact_percentage fails ("hot_loop" not in output).
- line 455 `worst_relative_shift * 100` -> `/`: percentage collapses from
  ~918% to ~0%, same test fails.
- line 521 `if by == "p90"` -> `!=`: `--by p90` and `--by p50xcount`
  return the SAME (wrong) order, test_by_p90_and_by_p50xcount_disagree_
  on_order fails.

All 4 new tests pass against the unmutated tree; `uv run pytest -q -n0
tests/unit/perf/` (97 tests) and `uv run frob test --base main` both
exit 0. Bound as ticket acceptance[1]'s evidence (the T-0756 fixture
criterion, already covering PERF008/PERF009's production-invocation
proof) alongside the existing PERF008/PERF009 fixture tests.

Also fixed a `_perf_script` helper type annotation (`tuple[str, str]` ->
`tuple[float, str]`, since it takes numeric weights) caught by `ty` after
adding the new test file; `uv run frob check --only lint`/`--only
static` both clean (only the pre-existing strata_core/frob_core
unresolved-import ty diagnostics, a worktree native-build artifact per
the agent playbook, remain).

### Changed
```
 docs/modules/perf.md                |  77 ++++++++++++-
 src/frob/__main__.py                |  22 ++++
 src/frob/app/config.py              |   3 +
 src/frob/app/perf_runner.py         | 185 ++++++++++++++++++++++++++++-
 src/frob/gates/__init__.py          |  25 ++--
 src/frob/perf/__init__.py           |  33 ++++++
 src/frob/perf/_advisories.py        | 224 ++++++++++++++++++++++++++++++++++++
 src/frob/perf/_ratchet.py           | 199 ++++++++++++++++++++++++++++++++
 src/frob/perf/_sketch_store.py      |  87 +++++++++++++-
 tests/unit/perf/test_advisories.py  | 134 +++++++++++++++++++++
 tests/unit/perf/test_gate_wiring.py | 116 +++++++++++++++++++
 tests/unit/perf/test_hot_query.py   |  76 ++++++++++++
 tests/unit/perf/test_ratchet.py     |  90 +++++++++++++++
 tickets.md                          | 158 ++++++++++++++++++++++++-
 14 files changed, 1406 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_ratchet.py::TestCheckRatchet::test_regression_beyond_tolerance_fires` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_gate_wiring.py::TestPerf008ProductionInvocation::test_before_no_effect_fails_to_find_perf008` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_gate_wiring.py::TestPerf008ProductionInvocation::test_after_loop_invariant_fs_walk_passes_perf008` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_gate_wiring.py::TestPerf009ProductionInvocation::test_before_no_findings_file_fails_to_find_perf009` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_gate_wiring.py::TestPerf009ProductionInvocation::test_after_regression_finding_passes_perf009` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_persist_run_cli.py::TestPersistRunDefaultPath::test_missing_perf_path_resolves_to_cwd` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_persist_run_cli.py::TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_persist_run_cli.py::TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_persist_run_cli.py::TestRatchetFindingRendering::test_regression_prints_label_and_exact_percentage` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
