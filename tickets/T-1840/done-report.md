## Done report

Removed the dead `frob:waive WIRE001` directive on `_restore_pool_executors`
in tests/unit/perf/test_serial_pools_import_failure.py. WIRE001's own
autouse-pytest-fixture rescue (`_is_autouse_pytest_fixture`, T-1510)
unconditionally exempts this symbol, so the waiver has suppressed nothing
since that rescue landed. Verified via WAIVE008 (fired this exact finding
during scope check before the fix) and confirmed clean after removal:
`frob check --only wire --only suppress --only scope --ticket T-1840`
reports 0 errors, 0 warnings. Module's own tests still pass unchanged.

### Changed
```
 tickets/T-1840/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesImportError::test_import_error_still_patches_concurrent_futures_only` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesUnexpectedException::test_unexpected_import_time_exception_is_swallowed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 12 error(s), 627 warning(s), 742 waived
- error-findings: COV001@.claude/hooks/_shellscan.py, COV001@.claude/hooks/diagnosis-nudge.py, COV001@.claude/hooks/dispatch-telemetry.py, COV001@.claude/hooks/frob-suggest.py, COV001@.claude/hooks/frob-timeout-guard.py, COV001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, DOC003@docs/commands/sys.md, DOCENUM001@docs/modules/gates.md, TEST001@.claude/hooks/_shellscan.py, invalid-argument-type@src/frob/strata/_sync_may.py, invalid-type-form@src/frob/strata/_sync_may.py
