---
id: T-1830
title: Dedupe TEST006's inline staleness loop to call frob.gates._coverage.is_stamp_stale
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test006_missing_stamp
- tests/test_gates.py::TestTestGate::test_test006_stale_stamp
- tests/test_gates.py::TestTestGate::test_test006_stale_on_new_file_not_in_stamp
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`src/frob/gates/__init__.py`'s TEST006 check (`_test006_stale`, around
line 4686) hand-rolls the exact same file-hash staleness comparison
T-1366 factored out into `frob.gates._coverage.is_stamp_stale` for CI's
own tamper/staleness verification step. TEST006 should call the shared
helper instead of duplicating the loop, closing the WIRE001 finding
T-1366 had to waive (is_stamp_stale's only real caller today is CI's
inline python check, not traceable by the callgraph) and removing the
duplication.

Found while working T-1366 (declared scope: ci.yml/_coverage.py/
_baseline.py only; gates/__init__.py is out of scope there).