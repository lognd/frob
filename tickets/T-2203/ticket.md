---
id: T-2203
title: 'tests/test_lang.py: 4 frob:tests directives use invalid kind="control" (T-2195
  land warning)'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_top_level_layout
- tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_src_layout_too
- tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_resolves_a_nonempty_target_set
- tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_detects_a_real_violation
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Landed with T-2195 (808e0c6fb3f4): frob:tests directives at tests/test_lang.py:921,927,942,962 use kind="control", which is not a valid kind (must be one of e2e/integration/property/unit). Change to kind="unit" (they are ordinary pytest unit tests exercising real consumers) or drop the kind= attribute entirely.