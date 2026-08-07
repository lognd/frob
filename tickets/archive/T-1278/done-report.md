## Done report

Changed:
src/frob/deploy/_conform.py :: extract_mutation_surface
src/frob/deploy/_conform.py :: expected_mutation_surface
src/frob/deploy/_conform.py :: deploy_conformance_violations
src/frob/deploy/_drift.py :: deploy_drift_violations
src/frob/deploy/_generate.py :: sorted_manifest_entries
src/frob/deploy/_generate.py :: manifest_digest
src/frob/deploy/_generate.py :: generate_install_script
src/frob/deploy/_generate.py :: generate_status_script
src/frob/deploy/_generate.py :: generate_uninstall_script
src/frob/deploy/_generate.py :: generate_all
src/frob/deploy/_generate_windows.py :: generate_windows_install_script
src/frob/deploy/_generate_windows.py :: generate_windows_status_script
src/frob/deploy/_generate_windows.py :: generate_windows_uninstall_script
tests/unit/deploy/test_generate_windows.py :: TestWindowsEntries.test_filters_to_windows_only
tests/unit/deploy/test_generate_windows.py :: TestInstall.test_idempotent
tests/unit/deploy/test_generate_windows.py :: TestInstall.test_creates_service_when_bin_path_declared
tests/unit/deploy/test_generate_windows.py :: TestInstall.test_creates_service_without_args
tests/unit/deploy/test_generate_windows.py :: TestStatus.test_one_line
tests/unit/deploy/test_generate_windows.py :: TestUninstall.test_removes

Work done this session: the prior agent (died mid-work, OOM) had already
added real behavioral tests for all 27 of the 0.0%-branch findings
(test_audit.py, test_conform.py, test_drift.py, test_generate.py,
test_vm_runner.py, test_generate_windows.py) across three evidence-
recording commits. This session finished the cleanup: removed stale
duplicate frob:tests directives left behind on the _conform.py/
_drift.py/_generate.py source symbols (the real edges live on the test
files, per this repo's dotted Class.method convention), and rewrote
test_generate_windows.py's directives from pytest :: form to the
dotted Class.method form required by frob:tests. Also refreshed the
stale pre-work sweep (ticket sweep) that had gone stale against the
commits made under this ticket, clearing a PRE001 gate failure.

Evidence: bound via ticket acceptance criteria [0]-[2] (already recorded
in prior sessions):
  tests/unit/deploy/test_generate_windows.py::TestWindowsEntries::test_filters_to_windows_only
  tests/unit/deploy/test_generate_windows.py::TestInstall::test_idempotent
  tests/unit/deploy/test_generate_windows.py::TestStatus::test_one_line
  tests/unit/deploy/test_generate_windows.py::TestUninstall::test_removes
  tests/unit/deploy/test_audit.py::TestDiff::test_no_diff
  tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared

Verification this session:
  pytest tests/unit/deploy/test_generate_windows.py -q -> 20 passed
  ruff check (5 touched files) -> no issues
  frob check --ticket T-1278 -> 0 errors, 396 warnings (all
    pre-existing/waived, none new under src/frob/deploy or
    tests/unit/deploy), gate:TEST 0 errors incl. 0 TEST005 findings

Filed: none (no out-of-scope work found; all 27 0.0%-branch findings
were legitimate testable behavior, none dead code beyond the one already
routed by acceptance criterion [1] -- StateDiff.is_empty via
test_audit.py::TestDiff::test_no_diff, confirmed live via
build_attestation's diff_states call chain, not removed).

Gates: check --ticket T-1278 clean (0 errors; fixed PRE001 stale
pre-work sweep mid-session).

### Changed
```
 src/frob/deploy/_conform.py                |  10 --
 src/frob/deploy/_drift.py                  |   3 -
 src/frob/deploy/_generate.py               |   6 --
 src/frob/deploy/_generate_windows.py       |   3 -
 tests/unit/deploy/test_generate_windows.py |  12 +--
 tests/unit/test_render.py                  |  67 ++++++++++++++
 tickets.md                                 | 144 +++++++++++++++++++++++++++--
 7 files changed, 207 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/unit/deploy/test_generate_windows.py::TestWindowsEntries::test_filters_to_windows_only` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate_windows.py::TestInstall::test_idempotent` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate_windows.py::TestStatus::test_one_line` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate_windows.py::TestUninstall::test_removes` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_audit.py::TestDiff::test_no_diff` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 396 warning(s), 676 waived
- error-findings: none (measured, zero errors)
