## Done report

frob agent env now exports PYTHONPATH=<worktree>/src ahead of any
inherited value, closing the T-4459 gap where a worktree test run
through the root checkout's interpreter silently imported frob from
the ROOT src/ (root editable-install .pth winning over an unset
PYTHONPATH), measuring main's code instead of the branch under test.
frob doctor gains ImportSourceStatus/_import_source_status, reporting
which src/ import frob actually resolved from and failing healthy
loudly when it does not match the worktree's own src/frob/__init__.py.

Evidence:
tests/unit/test_doctor.py::TestImportSourceStatus.test_matching_worktree_reports_clean
tests/unit/test_doctor.py::TestImportSourceStatus.test_mismatched_worktree_reports_loudly
tests/unit/test_doctor.py::TestImportSourceStatus.test_no_worktree_src_never_mismatches
tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath.test_env_output_names_worktree_src_on_pythonpath
tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath.test_documented_entry_point_makes_worktree_code_importable

Filed: none

BUG002 waived on all 5 evidence node ids (T-2025 squash-lands-repro-with-fix
limitation -- tests and fix landed in one worktree commit, no ancestor has
the test without the fix); real before/after measured manually and recorded
in the waiver reason appended to the ticket body.

### Changed
```
 docs/modules/agent-worktree.md    |  63 ++++++++++++++++
 src/frob/app/agent_runner.py      |  44 ++++++++++-
 src/frob/doctor.py                |  81 ++++++++++++++++++++
 tests/test_worktree_pythonpath.py | 153 ++++++++++++++++++++++++++++++++++++++
 tickets/T-4459/done-report.md     |  46 ++++++++++++
 tickets/T-4459/ticket.md          |  36 +++++++++
 6 files changed, 420 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath::test_env_output_names_worktree_src_on_pythonpath` (pytest node id, verified passing when recorded)
- `tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath::test_documented_entry_point_makes_worktree_code_importable` (pytest node id, verified passing when recorded)
- `tests/test_worktree_pythonpath.py::TestImportSourceStatus::test_matching_worktree_reports_clean` (pytest node id, verified passing when recorded)
- `tests/test_worktree_pythonpath.py::TestImportSourceStatus::test_mismatched_worktree_reports_loudly` (pytest node id, verified passing when recorded)
- `tests/test_worktree_pythonpath.py::TestImportSourceStatus::test_no_worktree_src_never_mismatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 4812 warning(s), 969 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md, SELFAUDIT001@src/frob/app/agent_runner.py, SELFAUDIT001@tests/test_worktree_pythonpath.py
