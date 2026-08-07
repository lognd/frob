---
id: T-0316
title: 'packaging: bare ''uv tool install frob'' does not install the strata_core
  native extension'
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_sys_audit_fails_loud_when_strata_present
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (aprog-public): 'uv tool install frob' does not pull the strata_core Rust wheel as a dependency -- it must be uv pip installed by hand into frob's tool venv. Without it every .strata file fails NativeExtensionUnavailable, frob sys audit degrades to SYS004 (still exits 0, so it silently goes dark), and design/** COV/SYS checks stop running. Bit mid-campaign when a reinstall wiped the manually-added wheel. This is the 'awkward setup step' the frob owner wants remediated. Fix: declare strata_core (and frob_core) as proper distributable dependencies of the frob wheel, or ship them as bundled native extensions, so a fresh 'uv tool install frob' yields full .strata support with no manual step. If truly can't auto-install, fail LOUDLY (nonzero, clear message) rather than silently degrading. Coordinate with the same native-build story make core uses.