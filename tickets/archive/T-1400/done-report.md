## Done report

(WAVE14-A session, continuation)

Continued from the prior WAVE13-B session's hand-off (perf_runner.py
already closed and committed in this worktree). This session's own work:

Closed three near-floor TEST005 gaps named in this session's brief, each
verified via a scoped `pytest --cov=<module> --cov-branch` run:

- `_config_meta.py::stale_install_warning`: 4.3% -> 97% (module overall;
  the function's own remaining miss is lines 142-143, a defensive
  `except Exception` debug-log branch this session judged out of scope
  to chase further). New file `tests/unit/test_app_config_meta_branches_t1400.py`
  (5 tests): no-declared-version (missing pyproject / wrong project name),
  unresolvable `find_spec` (None spec / None origin), and both
  `importlib.metadata.version` failure branches (`PackageNotFoundError`
  and a generic exception).
- `telemetry.py::tips_disabled`: 20.0% -> fully covered (function-local;
  module overall 92%, remaining misses are in unrelated functions). New
  file `tests/unit/test_app_telemetry_branches_t1400.py` (4 tests,
  1 parametrized x4): telemetry-disabled short-circuit, default-enabled
  (both env vars unset), and explicit falsy `FROB_NO_FOOTGUN_TIPS` values
  ("0"/"false"/"False"/"").
- `clean_runner.py::run`: 72.2% -> fully covered (function-local; module
  83%, remaining misses are in the untouched `_resolve_tier` helper). New
  file `tests/unit/test_app_clean_runner_branches_t1400.py` (3 tests):
  `clean()` returning `Err` (`CleanError.NotARepo`, `sys.exit(1)`), the
  `-y`/`--yes` executed-report branch, and the dry-run-with-real-entries
  branch (`would remove` + the trailing hint line) -- none of the
  sibling `TestCleanRunnerRun` suite's two existing cases (empty-tree
  dry-run, `--json`) reach any of these three.

All three new test files intentionally live under `tests/unit/test_app*`
(this ticket's own scope glob) rather than alongside each function's
existing test suite (`tests/unit/test_config.py`, `tests/test_telemetry.py`,
`tests/unit/test_app_runners_t0875_leaf_collision.py`) -- none of those
three sibling files matches the ticket's declared scope, so new coverage
was added as its own scoped file instead of editing out-of-scope files.

Also fixed a real regression the prior session's `test_perf_runner_t1400.py`
introduced and left unresolved: `tests/unit/strata/test_selfconform.py::
TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`
was failing on main-merged HEAD (11 real SYS104/SYS100 violations) because
that file's 8 new `Test*` classes were never declared in `design/frob.strata`'s
`testsuite` node `interface=` list, and 3 of its `write_text()` calls were
never declared under the node's `fs.write` capability list. Declared the
8 missing `interface=` attrs (alphabetically placed) and added
`tests/unit/test_perf_runner_t1400.py` to the `fs.write` `via` list;
`test_repo_design_and_declarations_are_self_conformant` now passes clean
(0 violations, only the pre-existing waived SYS100 signal.signal entry).

Repo-wide/app-wide TEST005 remainder (honest disclosure, not chased this
session): a full `pytest tests/ --cov=frob.app` run (the closest a
dispatched sub-agent can get to an unscoped measurement per playbook 6b/6c)
still lists 40 TEST005 findings under `src/frob/app/**` after this
session's fixes -- fleet_runner.py, deprecated_runner.py, _daemon_proxy.py
(4 functions), parse_runner.py, deploy_runner.py, scaffold_runner.py,
check_runner.py's `_ColorizedLevelFormatter.format`, ack_runner.py,
doctor_runner.py, natives_runner.py, debt_runner.py, registry_runner.py,
pool_runner.py, fmt_runner.py (branch-level), plus 15 module-line-level
findings (`__init__.py`, `_check_chunking.py`, `graph_runner.py`,
`stats_runner.py`, `test_runner.py`, `ticket_runner/*` x4, etc). These
were NOT re-triaged individually this session -- the prior T-1400 session's
own hand-off already flagged "roughly 40 of the ~50 unsampled runner
modules" as the outstanding remainder, and this list matches that
description closely enough to be the same population, not a new
discovery. Given this session's scope did not extend to a full runner-by-
runner sweep, these remain open for a follow-up T-1400 (or successor)
session with a larger time budget.

Lease collision noted, not resolved: `frob check --ticket T-1400` refuses
in this worktree -- T-1400's recorded lease belongs to worktree
`.claude/worktrees/w14b-tick`, not this one (`w4k-test005`), even though
this session was dispatched to continue T-1400 here. Did not run
`frob ticket start T-1400` to reclaim the lease (playbook 0.4: skip and
report on a lease collision, never force it) -- w14b-tick's own recent
commits do not reference T-1400, so this may be a stale lease rather than
active concurrent work, but that was not independently confirmed. Flagging
for the coordinator to adjudicate before this ticket's evidence/close step.

Not closing T-1400: the lease collision above blocks any ticket-scoped
`frob check`/`done-report`/`close` call from this worktree, and the
honest repo-wide remainder (40 TEST005 findings, unchanged in kind from
the prior session's own disclosed cut) means the ticket's acceptance
criterion is still unmet regardless of the lease issue.

### Changed
```
 tests/unit/test_perf_runner_t1400.py | 311 +++++++++++++++++++++++++++++++++++
 tickets.md                           | 208 ++++++++++++++---------
 2 files changed, 445 insertions(+), 74 deletions(-)
```

### Evidence
- `tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_matching_violation_is_attributed_to_its_symbol` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_violation_with_no_matching_symbol_is_dropped` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef::test_two_violations_on_the_same_symbol_accumulate_both_rules` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable::test_renders_one_row_per_entry_with_smell_tag` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable::test_empty_entries_still_prints_header_and_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestCollectStacksFromFileRequiresFile::test_missing_file_exits_1_with_logged_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestCollectStacksSamplerBranch::test_sampler_flag_dispatches_to_sampler_collector` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestPrintFindingsAdvisoryLoop::test_renders_one_line_per_advisory` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_entry_for_a_different_file_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_entry_with_no_symbol_record_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop::test_matching_entry_produces_a_gutter_at_the_symbols_start_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestPersistRunUnresolvedSection::test_hit_with_unknown_section_id_is_skipped_without_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering::test_hot_without_json_renders_a_table_with_header_and_row` (pytest node id, verified passing when recorded)
- `tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering::test_hot_top_truncates_the_table_rows` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
