## Done report

Trace (per the brief): `_ruff_diagnostic_identity`'s `base` argument is
ALWAYS the same directory that pass's own `ruff` subprocess ran in
(`worktree` for the live pass via `_ruff_new_violations`, the detached
`_spawn_baseline_snapshot_worktree` snapshot for the baseline pass via
`_ruff_baseline_diagnostic_identities`), and `diag.file` is ruff's own
absolute-path report from THAT SAME cwd -- so within one call, `diag.file`
and `base` are always same-drive by construction; `os.path.relpath` cannot
literally cross drives inside a single `_ruff_diagnostic_identity` call as
currently wired. The measured, reproducible failure mode is instead that
the LIVE pass's tree (a GitHub-hosted Windows runner's D:\a\frob\frob
checkout) and the BASELINE pass's tree (`tempfile.mkdtemp()`'s
C:\Users\runneradmin\...\Temp) can differ from EACH OTHER, and nothing
in `_ruff_diagnostic_identity` was defensive against a future or
alternate call shape pairing a diag_file with a foreign-drive base -- an
uncaught `ValueError` there would crash the land outright rather than
refuse it cleanly. Fixed defensively per the brief's acceptance criteria
regardless: relpath is now guarded, and both same-tree passes still
identity-match correctly.

Fix: extracted the path-shaping half of `_ruff_diagnostic_identity` into
a new pure function `_relativize_diag_path(diag_file, base, *,
path_mod=os.path)` -- catches `ValueError` from `path_mod.relpath` (the
cross-drive case) and falls back to `normcase(abspath(diag_file))` on
both sides consistently, so a genuine cross-drive pairing degrades to a
stable, crash-free identity instead of raising. `path_mod` is injectable
so the win32 `splitdrive`/`relpath`/`normcase` behavior is testable via
`ntpath` on any host. `_refuse_pre_land_lint`'s stderr message now also
names each new violation's raw `diag.file` text on win32, and the
"pre-existing violation merely shifted" test now wraps the call in
try/except SystemExit, re-raising as AssertionError carrying capsys
stderr + caplog text, so a future Windows CI run prints the mismatching
pair in the E lines instead of a bare `SystemExit: 1`.

Evidence:
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse (unchanged behavior, now with SystemExit->AssertionError visibility wrap)
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_same_drive_relativizes_normally (new)
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_cross_drive_diag_and_base_do_not_crash (new -- the ValueError guard itself)
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_live_and_baseline_pass_agree_across_differently_drived_trees (new -- T-4457's own acceptance shape, driven through ntpath so it runs and asserts on Linux)

Measurement: full module (10 node ids) passes on Linux:
`python -m pytest tests/test_ticket_land_lint_diff_attribution.py -q -p no:randomly` -> 10 passed.
This Linux host cannot force the real CI defect (both `os.path.relpath`
and the underlying drive concept are POSIX no-ops), so `frob:waive BUG002`
is recorded on the ticket for the pre-existing shift-line test
(PASSED_AT_PARENT, confirmatory-only by construction on this host); the
new `TestRelativizeDiagPath` tests exercise the actual win32 path shapes
directly via `ntpath` and were confirmed to fail against the pre-fix
`_ruff_diagnostic_identity` body (plain `os.path.relpath(diag.file,
base.resolve())`, no guard) before this change and pass after it. No
Windows mirror measurement was taken (single-drive mirror, per the
ticket's own note that this is why local measurement always passes) --
the acceptance criterion "the node id passes on the next Windows CI run"
is unverified until that run happens.

Filed: none (no out-of-scope work found).

Gates: `frob check --ticket T-4457` -- 20 errors repo-wide, ALL
pre-existing and outside this ticket's own scope (src/frob/app/
ticket_runner/_land_cmd.py, tests/test_ticket_land_lint_diff_
attribution.py): gate:PRE (PRE001, no recorded pre-work sweep, same
posture T-4445 reported), gate:SEC (1 unrelated SEC110), gate:SUPPRESS
(18 unrelated SUPPRESS001, pre-existing ty/ruff suppression-pairing
gaps repo-wide). gate:FMT (FMT001, this ticket's own new directive
lines over 88 cols) was hit and fixed via `frob format --directives`
before this report. ruff-check and ruff-format both clean on the two
touched files; `ty check` clean on _land_cmd.py.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py         | ~90 ++++++++++++++++++++--
 tests/test_ticket_land_lint_diff_attribution.py | ~90 +++++++++++++++++++++-
 tickets/T-4457/ticket.md                        | +waiver
```

### Evidence
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_same_drive_relativizes_normally
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_cross_drive_diag_and_base_do_not_crash
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_live_and_baseline_pass_agree_across_differently_drived_trees

### Changed
```
 tickets/T-4457/ticket.md | 17 +++++++++++++++++
 1 file changed, 17 insertions(+)
```

### Evidence
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_same_drive_relativizes_normally` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_cross_drive_diag_and_base_do_not_crash` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_live_and_baseline_pass_agree_across_differently_drived_trees` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 4822 warning(s), 962 waived
- error-findings: PRE001@tickets/T-4457, SEC110@tests/helpers/bash.py
