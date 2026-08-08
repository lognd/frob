---
id: T-1820
title: frob quality bind's argparse dests are permanently unwired by design (WIRE001
  follow_up anchor)
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
- src/frob/_cli_parsers/_quality.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1567's frob quality bind subparser registers --list-bindings/--list-sources/--json
purely for --help discovery -- frob.__main__._dispatch special-cases
'quality bind' before AppConfig is ever built (bind_runner.run takes raw
argv), mirroring the pre-existing top-level bind_p in _core.py which has
the identical unwired shape (grandfathered, predates WIRE001). This is a
WIRE001 follow_up anchor, not real deferred work: the dests are
permanently unwired by design and there is nothing to implement. Left
open only because WIRE002 requires a real ticket id outside tests/ trees
(docs/modules/gates.md#wire001wire002-t-1428's permanent=true escape
hatch is test-tree-only).

## Failure log
- 2026-08-08 attempt 1: Scope (src/frob/_cli_parsers/_quality.py) was, at the time of this attempt, explicitly held by another concurrent agent per this session's dispatch instructions (forbidden glob src/frob/_cli_parsers/**). Coordinator later corrected: this ticket is a permanent-by-design WIRE001 waiver anchor (T-1558 precedent) that must stay open/queued indefinitely -- the three frob:waive WIRE001 follow_up="T-1820" directives in that file are already correct as-is; there is no code to write and this ticket should never be closed.
