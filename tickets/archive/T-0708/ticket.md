---
id: T-0708
title: 'native-missing fail-loud tests broken: SYS004 behavior drifted'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/system/test_cli_native_missing.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_sys_audit_fails_loud_when_strata_present
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
designated_repro_test: null
acceptance:
- text: GIVEN a repo with .strata files and no built native WHEN frob check runs THEN
    SYS004 fails loud AND both tests pass
  evidence:
  - tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_sys_audit_fails_loud_when_strata_present
  - tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present
  - tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
threat: null
component: null
---
CI triage 2026-07-22: tests/system/test_cli_native_missing.py x2 fail on current main (test_check_fails_loud_with_sys004_when_strata_present, test_check_unaffected_when_no_strata_files). Investigate whether the native-staleness/fingerprint work (T-0570 doctor, _native_staleness) changed the SYS004 fail-loud contract or the tests' fixtures rotted; fix whichever is wrong -- the contract (a missing native with strata files present must fail LOUD, not silently skip) must hold.