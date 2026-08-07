---
id: T-1272
title: 'gates: waive COV006 dict-dispatch blind spot in TestWaivePresets'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWaivePresets::test_waive_preset_resolves_reason_and_matches_like_inline
- tests/test_gates.py::TestWaivePresets::test_unknown_preset_is_malformed_directive
designated_repro_test: null
threat: null
component: null
---
T-1176's TestWaivePresets tests reach dsl.py::_attrs_verb_error_waive only through the _VERB_ATTRS_VALIDATORS dict-dispatch table, which frob.graph.callgraph's best-effort BFS cannot trace (same blind spot as the T-1024 _scope_covers waivers). Added matching frob:waive COV006 comments.