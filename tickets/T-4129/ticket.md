---
id: T-4129
title: 'SCOPE002 doc-closure debt: _closeout.py''s own agentic-workflow.md edge pulls
  in an unrelated file cascade'
state: queued
kind: docs
origin: human
created: '2026-09-06'
priority: medium
blocked_by:
- T-4127
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4108: src/frob/_cli_parsers/_ticket/_closeout.py::_add_ticket_attach_and_lifecycle_end_parsers's frob:doc target lives in docs/guides/agentic-workflow.md, not in scope when only _closeout.py is scoped. Adding that doc file to scope cascades badly: docs/guides/agentic-workflow.md itself cites _new.py, _query.py, _core.py, _check.py symbols via other anchors, pulling in a chain of unrelated files just to close one edge. Pre-existing, unrelated to T-4108's own fix (the repeated --evidence-cmd refusal). Remedy: either split the shared doc's anchors so a single-verb ticket does not have to absorb the whole file's cross-references, or decide the edge is fine to leave broad and waive SCOPE002 for it at the doc level.