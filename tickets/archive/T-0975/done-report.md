## Done report

Changed: tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping

The test hardcoded frozenset({"archgate", "clones", "perf"}) as the expected
gates-native stage-group membership. T-0688 added exhaustive_handling to
_STAGE_GROUPS["gates-native"] in src/frob/check/__init__.py, desyncing the
literal. Fixed by importing _STAGE_GROUPS from frob.check and asserting
against the live registry value directly, so any future gate addition to
gates-native cannot desync this assertion again.

Evidence: tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping (pytest run, 58 tests passed in file)

Filed: none

Gates: frob check --ticket T-0975 -- scope is a single test file, drift/coverage
not applicable to test-only change.

### Changed
```
 tests/unit/test_app_runners_batch6.py | 9 ++++++++-
 1 file changed, 8 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4871 warning(s), 239 waived
- error-findings: none (measured, zero errors)
