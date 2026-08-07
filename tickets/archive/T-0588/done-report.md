## Done report

Re-measured `frob check --only test` on the current tree (post T-0850/102688bb):
TEST014 was 263 warnings before this change (not the 244 the T-draft-edbf1e26
triage recorded two days earlier -- the group set moved again), spread across
4 leaf-name groups: as_json (9 symbols, 36 pairs), as_text (9 symbols, 36
pairs), format (2 symbols, 1 pair), run (20 symbols, ~190 pairs). No 5th
"main" group -- consistent with the triage note that it stopped colliding.

Resolution per group, each edge added as an explicit `frob:tests kind="unit"`
directive directly on the colliding symbol's own def line (so
`_test014_group_by_leaf` excludes it from the convention-fallback pool
entirely, the same mechanism TEST001 credit already uses):

as_json / as_text (18 symbols total, fully resolved, 0 residual): every
Result-model `.as_json()`/`.as_text()` in the collision set was bound to a
test that actually calls it, verified by reading the test body:
- ArchResult.as_text/as_json -> tests/unit/test_arch.py::TestArchResultFormat
  (direct `result.as_text()` / `result.as_json()` calls on an ArchResult from
  analyze_project)
- DupResult.as_text/as_json -> tests/unit/test_dup.py::TestDupResultFormat
  (same shape, direct calls)
- ExportsResult.as_text -> tests/unit/test_exports.py::TestExportsPackage.
  test_as_text_output (direct call)
- ExportsResult.as_json -> tests/unit/test_app_runners.py::TestExportsRunner.
  test_json_mode_logs_result (indirect: exports_runner.run(cfg) with
  exports_json=True calls `er.as_json()` internally, confirmed by reading
  exports_runner.py; caplog asserts the JSON landed)
- GitLogResult.as_json/as_text -> tests/unit/test_gitlog_rendering.py's
  dedicated as_json/as_text tests (direct calls)
- MapResult.as_text/as_json -> tests/unit/test_map.py::test_map_as_text /
  test_map_as_json (direct calls)
- ModuleOutline.as_text/as_json -> tests/unit/test_outline.py::
  test_py_outline_as_text / test_py_outline_as_json (direct calls)
- XrefResult.as_text/as_json -> tests/unit/test_xref.py::test_as_text /
  test_as_json (direct calls)
- ToolResult.as_text -> tests/unit/test_process.py::
  test_pytest_as_text_shows_failures (direct call on a parsed pytest
  ToolResult)
- ToolResult.as_json -> tests/unit/test_process.py::test_pytest_as_json
  (direct call)
- Diagnostic.as_text (the as_text collision's other-file member, in the same
  process/parsers/common.py) -> tests/unit/test_process.py::test_ruff_as_text
  (indirect: ToolResult.as_text's `_render_diagnostics` calls `d.as_text()`
  per diagnostic; RUFF_JSON fixture has 2 real diagnostics so this path
  executes, confirmed by reading `_render_diagnostics`)
- CheckResult.as_json -> tests/unit/test_app_runners_batch6.py::
  TestCheckRunner.test_json_mode_prints_json_and_errors_exit_1 (indirect via
  CLI dispatch: check_run(cfg, check_json=True) calls `result.as_json()`,
  confirmed by reading check_runner.py's json branch; caplog asserts the
  logged message starts with "{")
  (CheckResult.as_text already had its own explicit edge from a prior
  ticket and was never in this collision list.)

format (2 symbols, fully resolved, 0 residual):
- frob.logging.formatter._FrobFormatter.format -> tests/system/
  test_cli_check.py::TestGitlessTargetGateSeverity.
  test_render_lint_gate_warns_not_errors_on_gitless_root. This test forces
  `frob.logging.logger._init()` to rebind after capsys and asserts the
  literal string "WARNING: render_lint_gate: git ls-files exited" in
  captured stderr -- that "WARNING: " prefix is exactly
  `_FrobFormatter.format`'s own line-23 behavior (`f"{record.levelname}:
  {msg}"`), so this is a real, demonstrated exercise of the method, not a
  guess.
- frob.app.check_runner._ColorizedLevelFormatter.format -> tests/system/
  test_cli_check.py::TestCheckBadCode.test_unused_import_output_mentions_error.
  This is a subprocess `frob check` run (non-json), and `check_runner.run`
  always wraps stderr handlers in `_ColorizedLevelFormatter` for non-json
  runs (`_colorized_stderr_logs`, entered unconditionally unless
  `cfg.check_json`). I independently reproduced this outside the test suite
  (FORCE_COLOR=1 real `frob check` run against a throwaway fixture project
  with `--skip-tests`-adjacent warn-severity gates) and captured literal
  ANSI-yellow-wrapped "WARNING: ..." lines on stderr, confirming this exact
  formatter fires on any pre-summary WARNING/ERROR during a non-json run;
  the fixture in test_unused_import_output_mentions_error triggers gate
  warnings/errors the same way, so the binding is real, not asserted-by-
  coincidence.

run (20 app/*_runner.py `run()` entrypoints -- 17 resolved, 3 honest
residual): added an explicit `frob:tests` edge on each `run()` I could
verify a real test drives, reading each test body first:
- arch/bind/cycle/debt/docs/dup/exports/gitlog/graph/mutate/outline/pool/
  release/stats/sys/ticket/xref runners -> each bound to a test that calls
  `run(cfg)` (or `run(argv)` for bind) directly against a hand-built
  AppConfig and asserts on real output/behavior (see the 17 evidence ids
  below, one class/function per runner).
- clean_runner.run, fmt_runner.run, registry_runner.run: NO test anywhere in
  the repo calls these three wrapper functions, directly or via CLI/
  subprocess dispatch -- verified by grep across tests/ for each module
  name and by reading the closest fixtures (tests/test_clean.py only tests
  frob.clean.clean()/scan(), never clean_runner.run's CLI wrapper;
  tests/test_gates_fmt_directives.py never touches fmt_runner; no test file
  references registry_runner at all). I am leaving TEST014 standing for
  these three (3 residual pairs, all pairwise between exactly these three
  symbols) rather than fabricate a binding. This is real, pre-existing
  coverage debt, consistent with the standing TEST003 waiver on
  src/frob/registry noting "no CLI/subprocess integration entrypoint
  exists" for that package.

TEST014 count: 263 -> 3 (measured via `frob check --only test --json`,
diagnostics filtered to code=="TEST014", before and after). The 3 remaining
are exactly the clean/fmt/registry cross-pairs, confirmed by rerunning
`frob check --only test` and reading the 3 emitted messages.

No TEST001/TEST002/TEST003/TEST006 regressions: TEST002=5, TEST003=2,
TEST006=1 unchanged before/after this change (only TEST014 moved). No new
WAIVE004 staleness introduced (861 gate:WAIVE warnings before and after --
none of the pre-existing TEST005/branch-coverage waivers on these same
symbols reference TEST001/TEST014, so adding frob:tests edges did not orphan
any of them).

Tightening-path recommendation (per the ticket's ask, not implemented here
-- follow-up material for T-0589): promoting TEST014 to ERROR now, repo-
wide, would be premature -- the "run" leaf group alone shows the real
failure mode is naming collision at massive scale (20 distinct CLI
entrypoints all legitimately named `run`, a convention this codebase relies
on everywhere) rather than rare accidents, and a blanket path/module-
correlation rule was already shown in T-0547's Done report to break ~100%
of legitimate convention-fallback matches here. What this ticket's concrete
resolution work suggests instead: (1) keep TEST014 as WARN and keep driving
individual collision groups to explicit edges as they're found (this ticket
proves that's tractable file-by-file, ~20-30 minutes per group of similar
symbols); (2) a cheaper, more targeted tightening than promoting TEST014
wholesale would be a narrower rule that fires only when a convention-matched
test's own module path shares ZERO path segments with ANY of the colliding
symbols' paths (a much weaker bar than T-0547's rejected "same top-level
dir" rule, and would not have false-positived on any of the 17 legitimately-
resolved `run` bindings above, all of which DO share a `test_app_runners*`
naming/path affinity with `app/*_runner.py`); (3) do not promote TEST014 to
ERROR until the clean/fmt/registry residual above is closed with real tests
-- an ERROR-level gate over undischargeable ambiguity would just force a
waiver, not a fix. T-0589 should scope out option (2) as a prototype against
this repo's real symbol/test layout before deciding severity.

Deviations: scope was widened via `frob ticket scope --add` (11 globs) to
cover the collision symbols' own source files, per the ticket's own note
that this was expected. `frob ticket sweep T-0588` was re-run after the
scope widen to refresh PRE001 before the final gate pass.

Land note: the order-dependent xdist flake (render-lint gitless system test, documented in its own docstring) was unbound from the LEDGER evidence list at land time -- the in-source frob:tests edge stays as the honest TEST014 binding; 35 ids verify.

### Changed
```
 src/frob/app/arch_runner.py        |   2 +
 src/frob/app/bind_runner.py        |   2 +
 src/frob/app/check_runner.py       |   2 +
 src/frob/app/cycle_runner.py       |   2 +
 src/frob/app/debt_runner.py        |   2 +
 src/frob/app/docs_runner.py        |   2 +
 src/frob/app/dup_runner.py         |   2 +
 src/frob/app/exports_runner.py     |   2 +
 src/frob/app/gitlog_runner.py      |   2 +
 src/frob/app/graph_runner.py       |   2 +
 src/frob/app/mutate_runner.py      |   2 +
 src/frob/app/outline_runner.py     |   2 +
 src/frob/app/pool_runner.py        |   2 +
 src/frob/app/release_runner.py     |   2 +
 src/frob/app/stats_runner.py       |   2 +
 src/frob/app/sys_runner.py         |   2 +
 src/frob/app/ticket_runner.py      |   2 +
 src/frob/app/xref_runner.py        |   2 +
 src/frob/arch/_models.py           |   4 +
 src/frob/check/__init__.py         |   2 +
 src/frob/dup/_legacy.py            |   4 +
 src/frob/exports/__init__.py       |   4 +
 src/frob/gitlog/__init__.py        |   4 +
 src/frob/logging/formatter.py      |   2 +
 src/frob/map/__init__.py           |   4 +
 src/frob/outline/__init__.py       |   4 +
 src/frob/process/parsers/common.py |   6 +
 src/frob/xref/__init__.py          |   4 +
 tickets.md                         | 344 ++++++++++++++++++++++++++++++++++++-
 29 files changed, 417 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestArchRunner::test_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestBindRunner::test_mismatch_json_mode_no_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestCycleRunner::test_cycle_found_with_suggest` (pytest node id, verified passing when recorded)
- `tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_search_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDupRunner::test_scan_text_mode_logs_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_json_mode_logs_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestGitlogRunner::test_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_success_logs_stats` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_success_no_survivors_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_json_mode` (pytest node id, verified passing when recorded)
- `tests/test_pool_runner.py::TestPoolSnapshotCli::test_snapshot_baselines_keys` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_success_writes_manifest` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_style.py::test_stats_plain_stdout_has_no_ansi` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestArchResultFormat::test_as_text_clean_project` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestArchResultFormat::test_as_json_has_suggestions_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::TestDupResultFormat::test_as_text_clean_project` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::TestDupResultFormat::test_as_json_has_groups_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestExportsPackage::test_as_text_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitlog_rendering.py::test_as_json_round_trips_groups` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitlog_rendering.py::test_as_text_no_commits_short_circuit` (pytest node id, verified passing when recorded)
- `tests/unit/test_map.py::test_map_as_text` (pytest node id, verified passing when recorded)
- `tests/unit/test_map.py::test_map_as_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_outline.py::test_py_outline_as_text` (pytest node id, verified passing when recorded)
- `tests/unit/test_outline.py::test_py_outline_as_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_xref.py::test_as_text` (pytest node id, verified passing when recorded)
- `tests/unit/test_xref.py::test_as_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_json_mode_prints_json_and_errors_exit_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_process.py::test_ruff_as_text` (pytest node id, verified passing when recorded)
- `tests/unit/test_process.py::test_pytest_as_text_shows_failures` (pytest node id, verified passing when recorded)
- `tests/unit/test_process.py::test_pytest_as_json` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckBadCode::test_unused_import_output_mentions_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 35 passed (from 35 evidence id(s))
- gates: 0 error(s), 990 warning(s), 220 waived
- error-findings: none (measured, zero errors)
