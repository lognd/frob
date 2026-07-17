---
id: T-0024
title: 'graph: @overload chains crash build_graph (UNIQUE symref); dedupe last-def-wins'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
evidence:
- tests/test_graph.py::TestDuplicateSymrefs::test_overload_and_property_setter_do_not_crash
attachments: []
---

## Done report

Last-definition-wins dedupe in _process_source_file; regression test
covers @overload chains and property/setter pairs.
