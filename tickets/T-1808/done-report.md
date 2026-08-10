## Done report

Design decision (dispatch's (a)-(e) ranking): auto-write into ~/.claude/
on every invocation was ranked out by the dispatch's own escape clause --
mutating the operator's home directory from a command run constantly is a
surprising, hard-to-reverse action, so (a) full auto-correct is rejected.
Chose the pairing of (c) and (d): the WRITE is (d) the new explicit verb
`frob claude sync [--check]` (frob.app.claude_runner, the mechanism), and
the DETECTION is (c) automatic and surfaced where an operator already
looks -- frob.app.claude_runner.drift_warning is wired into
frob.__main__.main() next to stale_install_warning/stale_binary_warning,
so every `frob` invocation prints one loud stderr line naming the exact
fix if any managed file has drifted, with no write. (b) is T-1809's own
job (the pre-land gate); (e) a playbook line was not used since (c)
already makes the signal automatic without requiring an operator to know
any command exists.

NO DUPLICATION: .claude/hooks/sync-claude-config.py stays the canonical,
dependency-free (stdlib-only) implementation, because the SessionStart
hook in .claude/settings.json invokes it with a bare python3 before any
frob venv is necessarily importable. frob.app.claude_runner loads that
script by file path (importlib, since its hyphenated name blocks a normal
import) and calls its now-public MANAGED/plan()/main(argv=None) directly.

Changed:
.claude/hooks/sync-claude-config.py::MANAGED (renamed from _MANAGED, now public)
.claude/hooks/sync-claude-config.py::plan (renamed from _plan, now public)
.claude/hooks/sync-claude-config.py::main (now takes argv: list[str] | None = None)
src/frob/app/claude_runner.py::_load_sync_module
src/frob/app/claude_runner.py::drift_report
src/frob/app/claude_runner.py::drift_warning
src/frob/app/claude_runner.py::run
src/frob/app/config.py::Subcommand.claude
src/frob/app/config.py::AppConfig.claude_command
src/frob/app/config.py::AppConfig.claude_check
src/frob/app/_config_external.py (claude_command/claude_check wired into the
  hardcoded _STRING_FIELDS/_BOOL_FLAGS argparse->AppConfig mapping)
src/frob/app/app.py (claude_runner wired into _RUNNER_MODULE_NAMES/
  _SUBCOMMAND_RUNNER_NAMES/_import_runner_module; App class carries a new
  AFFECT001 waiver matching config.py's own precedent)
src/frob/_cli_parsers/_misc.py::_add_claude_parser
src/frob/_cli_parsers/__init__.py (re-export)
src/frob/__main__.py (_add_claude_parser wired in; _dispatch's startup-warning
  block extracted into a new _print_startup_warnings helper, both for ARCH001
  and to host the T-1808 drift_warning call)
design/frob.strata (testsuite node's fs.read/fs.write may-clauses extended to
  tests/unit/test_claude_runner.py, SELFAUDIT001)
docs/modules/cli.md, docs/guides/claude-hooks.md, README.md (T-1808 sections
  and command-table rows)

Evidence: tests/unit/test_claude_runner.py -- TestDriftReport::
  test_reports_drifted_and_missing, TestDriftReport::
  test_none_for_repo_with_no_managed_config, TestDriftWarning::
  test_warns_when_managed_file_differs, TestDriftWarning::
  test_none_when_in_sync, TestDriftWarning::
  test_none_when_repo_has_no_managed_config, TestRun::
  test_check_mode_exits_1_on_drift, TestRun::test_sync_writes_managed_files,
  TestRun::test_run_rejects_unknown_action (8 node ids, all pytest,
  `frob test --base main` green: 19/19)

Filed: none (README.md, design/frob.strata, tests/unit/test_claude_runner.py,
  src/frob/_cli_parsers/{__init__,_misc}.py, src/frob/app/_config_external.py
  were added to T-1808's scope via `frob ticket scope --add` as required
  CLI-wiring/gate-satisfying files, not new out-of-scope tickets)

Gates: frob check --ticket T-1808 clean on every gate this ticket's own
  touched set can affect (AFFECT/ARCH/SCOPE/TEST/WIRE/PRE all 0 errors).
  Remaining repo-wide FAILs (gate:COV COV003 x4 on unrelated tickets
  T-0185/T-1351/T-1507/T-1512, gate:DOC/gate:DRIFT on pre-existing
  src/frob/tickets/_land.py doc-anchor drift, ruff-format 77 files,
  ruff-check 12 pre-existing warnings) are unscoped/unrelated pre-existing
  debt, confirmed against main (git show main:src/frob/tickets/_land.py
  carries the same DOC002 anchor before this ticket's diff) -- not
  introduced by this change.

### Changed
```
 tickets/T-1808/ticket.md | 78 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 77 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_claude_runner.py::TestDriftReport::test_reports_drifted_and_missing` (pytest node id, verified passing when recorded)
- `tests/unit/test_claude_runner.py::TestDriftReport::test_none_for_repo_with_no_managed_config` (pytest node id, verified passing when recorded)
- `tests/unit/test_claude_runner.py::TestDriftWarning::test_warns_when_managed_file_differs` (pytest node id, verified passing when recorded)
- `tests/unit/test_claude_runner.py::TestDriftWarning::test_none_when_in_sync` (pytest node id, verified passing when recorded)
- `tests/unit/test_claude_runner.py::TestDriftWarning::test_none_when_repo_has_no_managed_config` (pytest node id, verified passing when recorded)
- `tests/unit/test_claude_runner.py::TestRun::test_check_mode_exits_1_on_drift` (pytest node id, verified passing when recorded)
- `tests/unit/test_claude_runner.py::TestRun::test_sync_writes_managed_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_claude_runner.py::TestRun::test_run_rejects_unknown_action` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 6 error(s), 1009 warning(s), 710 waived
- error-findings: COV003@tickets/T-0185, COV003@tickets/T-1351, COV003@tickets/T-1507, COV003@tickets/T-1512, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py
