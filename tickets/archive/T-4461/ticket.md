---
id: T-4461
title: 'Windows CI: baseline ruff identities are relativized against the live root
  (..\..\runner~1\...), the last red test'
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land_lint_diff_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_ntpath_absolute_snapshot_rooted_diag_file_matches_live_identity
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_posix_absolute_tmp_snapshot_path_matches_live_identity
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_symlinked_snapshot_diag_file_unresolved_matches_realpath_base
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
designated_repro_test: tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_symlinked_snapshot_diag_file_unresolved_matches_realpath_base
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34748056574 (head 6f6ca432c, includes T-4445 and T-4457), Windows leg, the ONLY remaining test failure on any leg. T-4457's visibility change now names the mismatch exactly (captured log in the assertion message): live identity ('src\bad_lint.py', 'F401', '`os` imported but unused') "not found in baseline (baseline identities: [('..\..\..\..\..\runner~1\appdata\local\temp\frob-land-baseline-5d1uymtm\src\bad_lint.py', 'F401', '`os` imported but unused')])". So in `_ruff_baseline_diagnostic_identities` (src/frob/app/ticket_runner/_land_cmd.py) the baseline pass's diagnostics are relativized against the LIVE repo root, not against the baseline snapshot root: ruff on the runner reports the baseline file as an absolute path under the temp snapshot (C:\Users\RUNNER~1\AppData\Local\Temp\frob-land-baseline-<id>\src\bad_lint.py -- note the 8.3 short name RUNNER~1, because %TEMP% on the runner is expressed that way), and os.path.relpath(that, live_root) yields ..\..\..\..\..\runner~1\... which can never equal the live side's 'src\bad_lint.py'. On POSIX the same code passes only because ruff there returns paths relative to its cwd (the snapshot), so relpath happens to collapse; T-4457's traced claim that "base and diag.file always come from the same pass's tree" is falsified by this log. FIX: (1) the baseline pass must relativize each diagnostic against the snapshot root it linted (pass the snapshot path as `base` to _ruff_diagnostic_identity / _relativize_diag_path, and resolve both sides through os.path.realpath so 8.3 short names (RUNNER~1) and long names compare equal -- realpath on win32 expands short names); (2) assert in code (log at WARNING) when a computed identity path starts with '..' -- that shape is always a wrong base; (3) unit test that feeds an absolute snapshot-rooted diag.file with a different live root (ntpath via the injectable path module T-4457 added, plus a POSIX case with an absolute /tmp path) and asserts the baseline identity equals the live identity; (4) add a Linux reproduction to tests/test_ticket_land_lint_diff_attribution.py that makes ruff report absolute paths (e.g. pass absolute file arguments to the baseline ruff invocation, or run it from a cwd outside the snapshot) so the bug is visible on POSIX too and check-repro can fail at the parent. ACCEPTANCE: the node id tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse passes on the next Windows CI run; the new unit tests pass on Linux and on the winrun mirror. Sprint v0.531.0 (the last red test in CI). Successor of T-4457/T-4445/T-4403.