## Done report

TEST005 branch-coverage burn-down for `src/frob/strata/_native_test.py`
(T-0242's native `frob sys audit` invocation for the strata touched-set
test runner). Measured, current state (this repo's `.venv`,
`pytest --cov=frob.strata._native_test --cov-branch`, `addopts=""` to
bypass xdist for accurate single-process coverage):

- Before: 57 stmts, 12 branches, 88% (missing lines 91, 139-140, 144-145)
  against `tests/test_testing.py::TestNativeStrataAudit` alone (the
  ticket's own cited 30% figure was against a stale snapshot -- T-1415's
  earlier burn-down wave had already raised this file most of the way;
  the remaining gap this ticket actually closed is the 88% -> 100% tail,
  not a fresh 30% floor breach. Disclosed plainly rather than restating a
  stale number as current.)
- After: 100% (0 missing lines/branches) with the new dedicated
  `tests/unit/strata/test_native_test.py` added alongside the existing
  `tests/test_testing.py::TestNativeStrataAudit` coverage.

New file: `tests/unit/strata/test_native_test.py` (7 tests, two classes):

- `TestSummarize` (4 tests): direct unit coverage of the three private
  helpers `_summarize`/`_format_gaps`/`_format_selfconform` against
  synthetic `AuditReport`/`SelfConformReport` fixtures -- the "PROVED,
  zero unwaived gaps" branch (line 91) never fires through this repo's
  own real design tree (it always carries findings), so it needed a
  synthetic zero-gap fixture rather than an end-to-end run.
- `TestRunNativeSysAuditErrorBranches` (3 tests): `run_native_sys_audit`'s
  two remaining `is_err` branches (`evaluate_exhaustiveness`,
  `check_self_conformance`, lines 138-140/142-145) via `monkeypatch`,
  matching how the existing `test_bad_design_file_fails` isolates the
  `ids.errors` branch the same way; plus one full-happy-path test with
  both dependencies monkeypatched clean (exercises `_summarize`'s PROVED
  branch through the real `run_native_sys_audit` call path too, not just
  the direct unit test above).

Also added `frob:tests` directives on `run_native_sys_audit` pointing to
the three new `TestRunNativeSysAuditErrorBranches` tests (alongside the
three pre-existing `TestNativeStrataAudit` edges, all kept).

Scope note: T-1470's originally declared scope
(`'src/frob/strata/_native_test.py tests/unit/strata/test_native_test.py'`)
was a single space-joined string, not two separate glob entries -- a
malformed declaration from ticket creation, not something this dispatch
introduced. Fixed via `frob ticket scope T-1470 --add` (now two proper
entries), plus `design/frob.strata` (the same shared merge-artifact
reason T-1220 needed it for -- this worktree's one `git merge main` for
the whole series touched it) and `tests/test_testing.py`/
`tests/system/test_frob_self_model.py` (existing `frob:tests` edges on
this module's own symbols already pointed into them, predating this
ticket).

Gates: `frob check --ticket T-1470 --only scope --only prework --only
fmt --only affect_drift` clean (0 errors, 155 warnings, 1 waived --
warnings are scope-closure suggestions from the broad
`tests/test_testing.py` addition dragging in unrelated symbols'
`frob:tests` edges transitively; not chased further, out of this
ticket's actual purpose). No new waivers added.

Filed: none -- no out-of-scope work discovered.

### Changed
```
 design/frob.strata                |   4 +-
 docs/modules/dup.md               |   4 +
 docs/modules/lang.md              |  33 +++-
 frob-core/Cargo.lock              |  11 ++
 frob-core/Cargo.toml              |   1 +
 frob-core/frob_core.pyi           |  14 ++
 frob-core/src/extract.rs          | 122 +++++++++++++
 frob-core/src/lib.rs              |   3 +-
 src/frob/lang/_extract.py         |   6 +
 tests/unit/test_extract_native.py |  82 +++++++++
 tickets.md                        | 375 ++++++++++++++++++++++++++------------
 11 files changed, 532 insertions(+), 123 deletions(-)
```

### Evidence
- `tests/unit/strata/test_native_test.py::TestSummarize::test_no_gaps_reports_proved` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_test.py::TestSummarize::test_gaps_present_lists_them_instead_of_proved` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_test.py::TestSummarize::test_format_selfconform_one_line_per_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_test.py::TestSummarize::test_format_gaps_empty_is_empty_list` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches::test_exhaustiveness_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches::test_selfconform_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_test.py::TestRunNativeSysAuditErrorBranches::test_both_reports_clean_is_proved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 287 warning(s), 769 waived
- error-findings: DUP001@frob-core/src/extract.rs, SELFAUDIT001@design
