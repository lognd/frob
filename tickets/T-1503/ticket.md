---
id: T-1503
title: WIRE001 on test_extract_native.py's _python_side/_rust_side golden-test helpers
state: queued
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_extract_native.py
- tests/unit/test_capability_native.py
- tests/unit/test_arch_python_native.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_capability_native.py
  reason: same WIRE001 golden-test-helper pattern (a module-level comparison helper
    called only from its own file's test methods) now exists in these two files too
    (T-1221/T-1222); consolidating under this one existing ticket rather than filing
    near-duplicates
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_arch_python_native.py
  reason: same WIRE001 golden-test-helper pattern (a module-level comparison helper
    called only from its own file's test methods) now exists in these two files too
    (T-1221/T-1222); consolidating under this one existing ticket rather than filing
    near-duplicates
  actor: logan
  at: '2026-08-07'
designated_repro_test: null
threat: null
component: null
---
WIRE001 flags `_python_side`/`_rust_side` in tests/unit/test_extract_native.py
(T-1220's golden-parity tests for frob_core.extract_tree_python) as unreached
outside their own tests -- they exist solely as per-file test helpers that
assemble the existing Python-side computation vs the native kernel's output
for comparison within TestExtractTreePythonParity's own methods, mirroring
the tests/unit/test_conftest_stackdump.py::_load_conftest precedent (T-1466).
Follow-up: evaluate whether this pair should move to a shared test-support
module (frob.testing or a conftest fixture) if a future native-extraction
golden test wants the same comparison, or whether the current per-file scope
is intentionally final (in which case this ticket should close as won't-fix
with that recorded).