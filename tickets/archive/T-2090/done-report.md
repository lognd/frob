## Done report

Changed:
- src/frob/testing/_collect.py::collect_python_tests (calls the new
  _autorebuild_missing_natives when missing_natives is non-empty, and
  enriches the recorded failure detail with the missing native + build_cmd
  when collection still fails afterward)
- src/frob/testing/_collect.py::_autorebuild_missing_natives (new)
- src/frob/testing/_collect.py::python_collection_missing_natives (new
  public accessor, mirrors python_collection_failure_detail's module-state
  pattern)
- src/frob/testing/_collect.py::_set_collection_missing_natives (new)
- src/frob/testing/__init__.py (exports python_collection_missing_natives)
- src/frob/tickets/_evidence.py::add_evidence (new missing_natives= param)
- src/frob/tickets/_evidence.py::_check_evidence_resolution (missing_natives
  param picks which of two distinct UnknownEvidence messages fires)
- src/frob/app/ticket_runner/_verify.py::_apply_evidence (threads
  python_collection_missing_natives() into add_evidence; surfaces
  python_collection_failure_detail() on a collection-Err log line)
- docs/modules/testing.md (T-2090 public-API paragraph + frob:describes)

Evidence:
- tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing
  (designated repro: FAILED_AT_PARENT at e13105e46425fd2c49fc84d3fdd803db54c2f671,
  confirmed via frob ticket evidence --check-repro)
- tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
  (updated to assert the new "does not exist in this tree" wording and the
  absence of the cache-deletion advice for the natives-already-built case)
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd
- tests/test_testing.py::TestCollectPythonTests::test_python_collection_missing_natives_reflects_last_call
All bound to acceptance criteria 0, 1, 2 via --accepts.

Filed: none -- no out-of-scope work found.

Gates: `frob check --ticket T-2090 --only affect_drift --only prework --only test`
clean (0 errors, matched pre-existing warning set only) after adding the
doc paragraph, frob:tests edge, and its unit test. `frob check
--land-parity` clean (0 unscoped errors). `frob ticket evidence
--check-repro` confirmed FAILED_AT_PARENT (genuine repro) against the
test-only commit. TEST016 mutation check initially flagged one
confirmatory-only survivor (a dead `or ''` fallback in the new
enrichment code); removed the unreachable fallback rather than waiving it,
re-ran, close succeeded clean.

### Changed
```
 docs/modules/testing.md               |  23 ++++++
 src/frob/app/ticket_runner/_verify.py |  25 ++++++-
 src/frob/testing/__init__.py          |  12 +--
 src/frob/testing/_collect.py          |  86 ++++++++++++++++++++++
 src/frob/tickets/_evidence.py         |  68 ++++++++++++++---
 tests/test_testing.py                 | 134 ++++++++++++++++++++++++++++++++++
 tests/test_tickets.py                 |  38 +++++++++-
 tickets/T-2090/ticket.md              |  73 ++++++++++++++++--
 8 files changed, 432 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)
