## Done report

T-4461's realpath fix for _relativize_diag_path/_ruff_diagnostic_identity resolves the Windows 8.3-short-name (RUNNER~1) baseline-vs-live path mismatch; a new WARNING fires on any climbing (..-prefixed) identity; new unit tests cover ntpath absolute-snapshot, POSIX absolute-tmp, and a real POSIX symlink repro (the last genuinely fails at the pre-fix parent, designated as check-repro evidence); full module measured clean on Linux (13/13) and the Windows mirror (13/13); frob check --ticket T-4461 is 0 errors/0 unresolved

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py         | 79 +++++++++++++++++++-
 tests/test_ticket_land_lint_diff_attribution.py | 97 +++++++++++++++++++++++++
 tickets/T-4461/ticket.md                        |  7 +-
 3 files changed, 178 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_ntpath_absolute_snapshot_rooted_diag_file_matches_live_identity` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_posix_absolute_tmp_snapshot_path_matches_live_identity` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_symlinked_snapshot_diag_file_unresolved_matches_realpath_base` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4825 warning(s), 966 waived
- error-findings: none (measured, zero errors)
