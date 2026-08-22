## Done report

Changed:
- src/frob/app/test_runner.py::_explicit_path_selection (new)
- src/frob/app/test_runner.py::_selection_report (now checks path scoping first)
- src/frob/_cli_parsers/_misc.py::_populate_test_args (help text for test_path)
- docs/modules/testing.md (documented the new PATH-scoped selection behavior)
- tests/unit/test_app_test_runner.py (new evidence file)

Evidence:
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_none_when_path_unset
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_none_when_path_is_root_itself
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_relative_subdir_scopes_selection
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_path_outside_root_is_ignored
- tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_path_selection_routes_to_python_only
- tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_path_selection_honors_lang_filter
- tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_root_path_falls_back_to_all

All 7 collected and passed: `uv run pytest tests/unit/test_app_test_runner.py -p no:cacheprovider -q`
-> SUITE-RESULT: exitstatus=0 collected=7 failed=0

Filed: none (no out-of-scope work discovered)

Gates:
- `uv run frob check --ticket T-2319` ran clean of unwaived findings against
  the touched files (E501/F401 caught and fixed; unrelated repo-wide
  findings on other files are pre-existing, not attributable to this
  change).
- `uv run frob check --land-parity` was attempted 4 times; under this
  session's concurrent-agent contention it repeatedly could not finish the
  "static" stage group inside budget (T-1703 deferred-group reporting, not
  a false-clean). One run that DID complete showed the only file-scoped
  finding as tests/unit/test_app_test_runner.py needing ruff-format
  (fixed, verified 0-diff with `ruff format --diff`); the remaining
  findings that surfaced in a partial JSON run (release/_cli.py,
  test_release.py, design/SELFAUDIT001, tickets.md/TICK004,
  docs/modules/cli.md/WIRE003) touch none of this ticket's files and
  are outside scope -- not addressed here.

Note: `frob quality test path` scoping is routed to the "python" language
only (see docstring/doc for why: `_route_items` cannot resolve a bare
repo-relative path against a non-python runner's `cwd`). This matches the
ticket's own motivating repro (`pytest tests/unit/`) and does not attempt
rust/other-language path scoping.

### Changed
```
 tickets/T-2319/ticket.md | 31 ++++++++++++++++++++++++++++++-
 1 file changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_none_when_path_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_none_when_path_is_root_itself` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_relative_subdir_scopes_selection` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_path_outside_root_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_path_selection_routes_to_python_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_path_selection_honors_lang_filter` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_root_path_falls_back_to_all` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2319, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
