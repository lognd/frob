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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/vet/_capability.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_core.py'
  actor: logan
  at: '2026-09-19'
  old_length: 679
  new_length: 1915
evidence:
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_typescript_core_net_undeclared_fires
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_typescript_core_net_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_rust_core_exec_undeclared_fires
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_rust_core_exec_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
logand.app pilot reports browser-side capabilities could not be auto-verified, leaving permanent SYS101 warnings -- yet vet _capability HAS a typescript pattern table (.ts/.tsx/.js in _EXT_LANGUAGE). Investigate whether the conformance path (scan_directory_capabilities via _selfconform / sys audit) actually walks TS/JS files or silently skips them (wiring bug), or whether the pilot's code globs missed the frontend tree (doc/UX gap). Either way the fix must make TS scanning provably active -- this feeds directly into T-0158's coverage matrix, which should gain a live wiring assertion (language column proven active end-to-end through sys audit, not just patterns existing).

T-4718 sweep (condensed from src/frob/vet/_capability_core.py, the
`SCANNED_LANGUAGES` block, trimmed for DOCARCH002's 12-line cap): the
trimmed block's full original text, kept verbatim below.

#: Every language bucket `_EXT_LANGUAGE` maps at least one extension to --
#: i.e. every language a capability-scan CALLER (self-conformance's
#: `_selfconform.py::_sorted_capability_files`, `vet`'s dependency scan)
#: actually reaches via `language_for`/`scan_file_capabilities`. Exists so
#: a drift-lock test can assert this set equals
#: `_capability_registry.LANGUAGES` (the registry's claimed-supported set)
#: without either side hand-duplicating the other's language list -- a new
#: registry language with no `_EXT_LANGUAGE` extension entry (or vice
#: versa) fails that test loudly instead of silently going unscanned
#: (T-0169: this exact class of gap is what let TS/JS self-conformance
#: scanning go dark in the logand.app pilot).
#:
#: T-2358: moved here (from `_capability.py`) alongside `language_for` --
#: `_capability_core.py` already defines `_EXT_LANGUAGE` both symbols are
#: derived from, so this was the natural home once `_capability_scan.py`
#: needed `language_for` back (see `language_for`'s own T-2358 note).