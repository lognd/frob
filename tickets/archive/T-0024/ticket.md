---
id: T-0024
title: 'graph: @overload chains crash build_graph (UNIQUE symref); dedupe last-def-wins'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestDuplicateSymrefs::test_overload_and_property_setter_do_not_crash
designated_repro_test: null
threat: null
component: null
---
