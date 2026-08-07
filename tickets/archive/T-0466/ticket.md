---
id: T-0466
title: 'markdown frob:waive is inert: .md-embedded frob:waive produces no graph edge,
  so ref_gate (and any snapshot-edge-based gate) cannot honor a waiver on a .md file
  -- ~30 doc-anchor REF002 + .md REF001 are unwaivable; refs gate should text-scan
  .md waivers like _docblocks/DOC004 does'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_refs.py
- src/frob/gates/
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires
designated_repro_test: null
threat: null
component: null
---
