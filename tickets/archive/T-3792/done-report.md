## Done report

Changed:
src/frob/arch/__init__.py::_analyze_one_file (rel path now .as_posix())
src/frob/tickets/_reporting_attachments.py::_record_attachment (rel_path now .as_posix())
src/frob/tickets/_brief.py::_infer_verify_commands (candidate path now .as_posix())
src/frob/gates/_tickets_gate.py::_tick010_stale_lease_report (message uses plain str, not repr, for worktree path)

Root cause: str(Path)/f"{path}" produces backslash-separated paths on
win32; downstream consumers compare against forward-slash prefixes
(is_test_file's PurePosixPath parts check) or do exact-string
containment checks against a path built with forward slashes/no repr
escaping. Fixed each site to emit posix-shaped/plain strings.

Evidence (winrun-confirmed PASS on win32, also green on Linux):
tests/test_arch_gate.py::TestArchGateLargeFile::test_test_file_exempt_from_large001
tests/test_tickets.py::TestAttach::test_index_increments
tests/test_tickets_brief.py::TestInferVerifyCommands::test_matches_test_file_by_stem
tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_missing_worktree_reports_once_with_path_and_remedy

Filed: none

Gates: frob check --ticket T-3792 clean of SCOPE001/PRE001 after
scope correction + sweep; pre-existing repo-wide gate failures
(gate:COV/DRIFT/LANG/PRE/REF/SCOPE002 advisories, ruff-format) are
unrelated to this ticket's touched set.

### Changed
```
 tickets/T-3792/ticket.md | 38 +++++++++++++++++++++++++++++++++++---
 1 file changed, 35 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_test_file_exempt_from_large001` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestAttach::test_index_increments` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestInferVerifyCommands::test_matches_test_file_by_stem` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_missing_worktree_reports_once_with_path_and_remedy` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4364 warning(s), 923 waived
- error-findings: none (measured, zero errors)
