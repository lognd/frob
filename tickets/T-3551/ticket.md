---
id: T-3551
title: 'macOS: mincrate fixture crate fails to build on Python 3.14 (pyo3 lacks abi3
  feature)'
state: in-progress
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_natives_build_integration.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record macOS-only BUG002 waiver
  actor: logan
  at: '2026-08-31'
  old_length: 0
  new_length: 469
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive BUG002 reason="macOS-only defect verified from CI run 33361224273 (assert build_natives outcome failed: mincrate exit 1, PyO3 max supported version 3.13 < configured 3.14): the macOS runner ships Python 3.14 while this Linux dev box ships an older CPython, so the pyo3-without-abi3 build failure this fixes cannot reproduce here regardless of the fix; adding abi3-py311 is a pure forward-compatibility widening that cannot regress a currently-passing build."