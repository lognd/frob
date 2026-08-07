## Done report

## Done report

Changed:
src/frob/app/config.py::AppConfig.exports_consumers
src/frob/app/config.py::AppConfig.exports_lang
src/frob/app/config.py::AppConfig.from_args (string-field mapping list)
src/frob/app/exports_runner.py::_run_consumers
src/frob/app/exports_runner.py::run
src/frob/__main__.py::_add_exports_parser (--consumers, --lang)
docs/commands/exports.md (usage examples, flags table, public API block)
tests/unit/test_app_runners.py::TestExportsRunner (3 new cases)

Evidence:
tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_logs_result
tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_json_output
tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_err_result_exits_1
(recorded via `frob ticket evidence T-0876`; full TestExportsRunner class + test_exports.py
pass: `uv run pytest tests/unit/test_app_runners.py tests/unit/test_exports.py -q` -> 51 passed)

Filed: none

Gates: `uv run frob check --ticket T-0876 --only lint` clean; `--only gates-fast`,
`--only gates-native`, `--only gates-security` all 0 errors (warnings are pre-existing
repo-wide noise, none attributable to this change). Fixed along the way: COV005
(frob:doc directive had ridden onto the private `_run_consumers` helper -- moved back
to sit only on the public `run`), and extended ticket scope to include
tests/unit/test_app_runners.py (SCOPE001) since the CLI-level tests for this ticket
live there.

Note: mid-session I accidentally ran `make core` / `frob ticket start T-0876` once
against the shared checkout path (/home/logan/projects/frob) instead of this worktree
before catching the mistake; that left a stale ticket lease there which I stole back
via `frob ticket start T-0876 --steal` once inside the correct worktree. No code/doc
edits happened in the shared checkout, only the transient ticket-state/lease mutation
described above.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_logs_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_json_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_err_result_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 2278 warning(s), 219 waived
- error-findings: none (measured, zero errors)
