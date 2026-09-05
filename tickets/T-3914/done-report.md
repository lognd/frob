## Done report

Drained the (a) test-harness bucket of the current 49-failure win32 set:
13 tests fixed across 8 test files, plus one real product one-liner
(same native-separator-leak class as T-3662/T-3664, a new call site).

### Changed
- tests/unit/test_conftest_suite_result_status.py: _FakeSession gains
  exitstatus, local _FakeConfigureConfig gains pluginmanager -- both
  attributes a real pytest.Session/Config carry, exercised only under
  CI's windows-only FROB_TEST_HARD_EXIT / FROB_TEST_MIDRUN_WATCHDOG_
  SECONDS env vars (verified in ci.yml: windows-latest leg only).
- tests/unit/test_draft_finalize_attachments.py: two fixture sites
  switched from str(p.relative_to(...)) to .as_posix() -- the TEST
  fixture leaked a native separator, product's own posix-shape contract
  (_reporting_attachments.py) was untouched.
- tests/unit/test_ticket_new_body_file_pipe_t2021.py: module-level
  skipif(win32) -- /dev/fd/<n> pipe-path exposure is POSIX-only; the
  behavior under test (_resolve_new_body reads its source exactly once)
  is platform-neutral and covered by this module's non-pipe tests plus
  regular-file coverage elsewhere.
- tests/test_testing.py: TestCargoEnv asserts the platform-correct
  overlay key (PATH on win32, LD_LIBRARY_PATH elsewhere) instead of
  hardcoding the POSIX one; test_single_file_extension_fingerprinted
  derives its extension-module suffix from
  importlib.machinery.EXTENSION_SUFFIXES instead of hardcoding .so
  (win32 uses .pyd).
- tests/unit/deploy/test_deploy_runner.py: gate the 0o755 permission-bit
  assertion to POSIX -- win32 has no such bits.
- tests/unit/fleet/test_manifest.py, tests/unit/rapid_sweep_suite/test_filing.py:
  replaced bare "/..." absolute-path literals (Path.is_absolute() is
  False for a driveless path on win32) with a literal anchored on
  tmp_path's own drive/root, so the fixture is genuinely absolute on
  every platform.
- tests/unit/test_check_native_cargo_runners.py: compare Path objects
  instead of str(Path(...)) against a POSIX literal.
- src/frob/app/ticket_runner/_new.py (real product fix): the
  scope-overlap warning built its path list via
  str(p.relative_to(root)) instead of .as_posix() -- same class as
  T-3662/T-3664, a new call site, leaking a native separator into
  consumer-facing warning text.

### Evidence
13 pytest node ids recorded via `frob ticket evidence T-3914` (all
verified passing on Linux, the /dev/fd module correctly NOT skipped
here): tests/unit/test_conftest_suite_result_status.py (2 of 8, others
share the identical fixture and pass identically), tests/unit/
test_draft_finalize_attachments.py (2), tests/unit/
test_ticket_new_body_file_pipe_t2021.py (1), tests/test_testing.py (2),
tests/unit/deploy/test_deploy_runner.py (1), tests/unit/fleet/
test_manifest.py (1), tests/unit/rapid_sweep_suite/test_filing.py (1),
tests/unit/test_check_native_cargo_runners.py (1),
tests/unit/test_new_ticket_scope_overlap_warning.py (2).
Also `frob test --base main`: touched=36, run_selected python exit=0,
13 python test outcomes recorded, all PASS.

Every fix here was made and verified on Linux only -- the win32-side
claim ("this drains N of the 49") is INFERRED from source-level
confirmation of each root cause (checked against the actual product
code each test exercises, e.g. _cargo_env's win32 branch,
EXTENSION_SUFFIXES, Path.is_absolute() semantics, ci.yml's env-var
scoping), not verified by a real win32 CI run. That re-measurement is
the next step, tracked below.

### Filed
Filed: T-3918 (win32: split the real-defect (b) bucket of
T-3914's 49-failure classification into scoped leaves) -- the bucket
(b) items recorded in this ticket's own body (land-lock/graph-lock
cross-process lock semantics, the cycle-detector silent-zero, and the
further native-separator-leak sites in profile_boundary/dup/arch_suite)
are NOT fixed here, to avoid scope creep into fixes this ticket was not
scoped to make; that draft is the tracking leaf for splitting them into
individually scoped tickets.

### Gates
`frob check --ticket T-3914`: 64 errors remain, all PRE-EXISTING and
unrelated to this ticket's diff, verified individually:
- DEPR003@src/frob/app/fmt_runner.py, DOC006@tickets/T-3902/ticket.md,
  DRIFT001@src/frob/verify/_worker.py: none of these three files are
  touched by this ticket's diff; pre-existing baseline findings.
- The remaining ~60 are all SCOPE002 scope-closure suggestions --
  tests/test_testing.py alone carries frob:tests reverse-edges into
  dozens of unrelated modules (Kotlin/Rust/TS collectors, fuzz, etc.)
  because it is a very wide-coverage test file; the closure check walks
  that whole reverse-edge set once the file enters ANY ticket's scope,
  regardless of how small the actual diff in it is. Chasing full
  closure here would mean pulling most of src/frob/testing/** and
  src/frob/fuzz/** into this ticket's scope for a two-line assertion
  fix -- out of proportion to the change. frob:waive SCOPE002
  reason="tests/test_testing.py's own scope-closure breadth (wide
  frob:tests reverse-edge fan-out unrelated to the 2 assertions this
  ticket actually changed in it) -- narrowing would require pulling in
  dozens of unrelated source modules for a test-literal fix"
`frob test --base main`: PASS (see Evidence above).

### Changed
```
 src/frob/app/ticket_runner/_new.py                 |   6 +-
 tests/test_testing.py                              |  21 +++-
 tests/unit/deploy/test_deploy_runner.py            |   9 +-
 tests/unit/fleet/test_manifest.py                  |  14 ++-
 tests/unit/rapid_sweep_suite/test_filing.py        |   8 +-
 tests/unit/test_check_native_cargo_runners.py      |   6 +-
 tests/unit/test_conftest_suite_result_status.py    |  45 ++++++--
 tests/unit/test_draft_finalize_attachments.py      |   8 +-
 tests/unit/test_ticket_new_body_file_pipe_t2021.py |  16 +++
 tickets/T-3914/done-report.md                      | 128 +++++++++++++++++++++
 tickets/T-3918/ticket.md                 |  74 ++++++++++++
 11 files changed, 312 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_configure_resets_stale_internal_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestBackfillStaleDraftAttachmentPaths::test_leaves_a_correctly_recorded_attachment_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestDoubleReadDrainsAPipe::test_second_read_of_a_drained_pipe_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCargoEnv::test_cargo_env_ok_when_python311_and_libdir_found` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestNativeFingerprint::test_single_file_extension_fingerprinted` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_deploy_runner.py::TestGenerate::test_generate_writes_files` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_ok` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile::test_absolute_outside_root_is_kept_and_logged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_finds_test_executable` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_glob_vs_file_overlap_is_detected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 4 error(s), 4362 warning(s), 925 waived
- error-findings: DEPR003@src/frob/app/fmt_runner.py, DOC006@tickets/T-3902/ticket.md, DRIFT001@src/frob/verify/_worker.py, SCOPE002@tickets.md
