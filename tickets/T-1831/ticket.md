---
id: T-1831
title: _GroupedHelpFormatter's callback methods are genuinely wired via argparse formatter_class
  (WIRE001 follow_up anchor)
state: queued
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1571's _GroupedHelpFormatter (src/frob/__main__.py) and its two methods
(_format_action, _format_grouped_subparsers) are genuinely wired -- passed
as formatter_class=_GroupedHelpFormatter to the root argparse parser --
but the best-effort callgraph (frob.graph.callgraph) cannot trace a class
passed as a constructor kwarg and invoked internally by argparse's own
help-rendering machinery as a caller, the same class of gap as this
repo's cross-package DEAD001 waivers (T-1024 precedent) applied to WIRE001
instead. This is a WIRE001 follow_up anchor, not real deferred work:
there is nothing to implement, the code is already correctly wired and
covered by tests/unit/test_main_entry.py::TestGroupedHelpFormatter. Left
open only because WIRE002 requires a real ticket id outside tests/ trees
(docs/modules/gates.md#wire001wire002-t-1428's permanent=true escape
hatch is test-tree-only).

## Failure log
- 2026-08-08 attempt 1: Verified: this is a permanent WIRE001 follow_up anchor (T-1820 precedent, same shape). The three frob:waive WIRE001 follow_up="T-1831" directives in src/frob/__main__.py (lines 184, 202, 216) are already correct as-is -- _GroupedHelpFormatter and its two methods are genuinely wired via argparse's formatter_class mechanism, which the best-effort callgraph cannot trace. There is no code to write; WIRE002 requires a real, still-open ticket id as follow_up (the permanent=true escape hatch is test-tree-only per docs/modules/gates.md#wire001wire002-t-1428), so this ticket must stay open/queued indefinitely as that anchor. Closing it would orphan the waivers and re-trigger WIRE002 on main.
