## Done report

T-4125 measured a bare ["ty", "check", ...] argv in this land's own
pre-land type-check stage resolving through PATH to a global ty binary
whose version differs from the project's own pinned venv -- so the land
refused a ticket on findings from a checker the project neither uses
nor pins. T-4125's population measurement named 7 such call sites
(mechanism (b): checker-version skew, confirmed directly in this repo,
not the earlier tree-timing hypotheses).

The fix is frob.process._project_tool: project_tool_argv builds the one
correct argv (uv run --project <root> <tool> ...) and resolve_project_
tool additionally names the resolved binary path and version. Every
call site from T-4125's population (_land_cmd.py's _ty_check_files/
_ruff_check_files, check/_python.py's _run_ruff/_ruff_format_result/
_run_ruff_autofix/_ty_base_cmd, pyfmt_runner.py's four ruff call sites)
now routes through it -- both the previously-bare spellings AND the two
already-correct-looking "uv run ruff" spellings that lacked an explicit
--project and so depended on the subprocess cwd.

The land's pre-land type-check refusal message
(_assert_touched_files_type_check_pre_land, now split with
_refuse_touched_files_type_check for ARCH001) names each new error's
file/line/text, the worktree and commit checked, and the resolved ty
path+version -- closing the diagnostic gap the original report
identified (a refusal naming only a count, with no way to reproduce it).

frob.gates._bare_toolchain.bare_toolchain_gate (BARETOOL001, WARN-tier)
is the regrowth guard: an AST scan over every git-tracked .py file for
a List/Tuple literal whose first element is a hardcoded bare toolchain
name, wired and tested (10 tests) but NOT YET registered in frob.gates'
job registry (src/frob/gates/__init__.py) -- that file is under T-4124's
live lease for the duration of this work. Filed T-4146 to wire the
one-line registration once that lease frees.

T-3019's bare-ruff choice in frob.check._python is explicitly superseded
(reasoning updated in the module's own docstrings): it avoided an
unscoped `uv run ruff` (cwd-derived project, untracked uv.lock hazard),
which project_tool_argv's explicit --project <root> closes without
falling back to a bare name.

### Changed
```
 docs/modules/process.md                 |  55 ++++++++++
 src/frob/app/pyfmt_runner.py            |  15 ++-
 src/frob/app/ticket_runner/_land_cmd.py |  77 +++++++++++---
 src/frob/check/_python.py               |  46 ++++----
 src/frob/gates/_bare_toolchain.py       | 104 ++++++++++++++++++
 src/frob/process/_project_tool.py       | 180 ++++++++++++++++++++++++++++++++
 src/frob/vet/_bare_toolchain.py         | 111 ++++++++++++++++++++
 tests/unit/test_check.py                |  55 +++++-----
 tests/unit/test_project_tool.py         | 123 ++++++++++++++++++++++
 tests/unit/vet/test_bare_toolchain.py   | 109 +++++++++++++++++++
 tickets/T-3887/done-report.md           |  78 ++++++++++++++
 tickets/T-3887/ticket.md                |  28 ++++-
 tickets/T-4125/done-report.md           |  72 +++++++++++++
 tickets/T-4125/ticket.md                |  21 +++-
 tickets/archive/T-2252/ticket.md        |   9 +-
 tickets/archive/T-2320/ticket.md        |   9 +-
 tickets/archive/T-3019/ticket.md        |  16 ++-
 17 files changed, 1036 insertions(+), 72 deletions(-)
```

### Evidence
- `tests/unit/test_project_tool.py::TestProjectToolArgv::test_shape` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_bare_toolchain.py::TestBareToolchainFindings::test_flags_bare_argv_literal` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_bare_toolchain.py::TestBareToolchainGate::test_flags_bare_argv_literal` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffRealPaths::test_invokes_ruff_via_project_tool_argv_not_bare_ruff` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffAutofix::test_success_runs_fix_then_format_via_project_tool_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_genuinely_new_finding_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_pre_existing_finding_that_merely_shifted_lines_does_not_refuse` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 34 error(s), 4467 warning(s), 934 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/gates/_bare_toolchain.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, CROSSTICKET001@docs/modules/process.md, CROSSTICKET001@src/frob/app/pyfmt_runner.py, CROSSTICKET001@src/frob/check/_python.py, CROSSTICKET001@src/frob/gates/_bare_toolchain.py, CROSSTICKET001@src/frob/process/_project_tool.py, CROSSTICKET001@src/frob/vet/_bare_toolchain.py, CROSSTICKET001@tests/unit/test_check.py, CROSSTICKET001@tests/unit/test_project_tool.py, CROSSTICKET001@tests/unit/vet/test_bare_toolchain.py, DOC002@src/frob/gates/_bare_toolchain.py, DOC002@src/frob/vet/_bare_toolchain.py, DOC006@tickets/T-4144/ticket.md, DRIFT002@src/frob/check/_python.py, DUP001@src/frob/app/ticket_runner/_land_cmd.py, FMT001@src/frob/gates/_bare_toolchain.py, FMT001@src/frob/process/_project_tool.py, FMT001@src/frob/vet/_bare_toolchain.py, LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, REF001@.github/ISSUE_TEMPLATE/config.yml, REF002@.github/ISSUE_TEMPLATE/bug_report.yml, REF002@.github/ISSUE_TEMPLATE/feature_request.yml, REF002@.github/PULL_REQUEST_TEMPLATE.md, REF002@CODE_OF_CONDUCT.md, REF002@CONTRIBUTING.md, REF002@SECURITY.md, SCOPE002@tickets.md, SELFAUDIT001@src/frob/vet/_bare_toolchain.py, SELFAUDIT001@tests/unit/test_project_tool.py, SELFAUDIT001@tests/unit/vet/test_bare_toolchain.py, WIRE001@src/frob/gates/_bare_toolchain.py
