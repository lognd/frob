---
id: T-0169
title: capability conformance did not scan TS/JS in the logand.app pilot -- verify
  per-language wiring
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/vet/_capability.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_typescript_core_net_undeclared_fires
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_typescript_core_net_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_rust_core_exec_undeclared_fires
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_rust_core_exec_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages
designated_repro_test: null
threat: null
component: null
---
logand.app pilot reports browser-side capabilities could not be auto-verified, leaving permanent SYS101 warnings -- yet vet _capability HAS a typescript pattern table (.ts/.tsx/.js in _EXT_LANGUAGE). Investigate whether the conformance path (scan_directory_capabilities via _selfconform / sys audit) actually walks TS/JS files or silently skips them (wiring bug), or whether the pilot's code globs missed the frontend tree (doc/UX gap). Either way the fix must make TS scanning provably active -- this feeds directly into T-0158's coverage matrix, which should gain a live wiring assertion (language column proven active end-to-end through sys audit, not just patterns existing).