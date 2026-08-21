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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_quality.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: true
anchor_reason: permanent WIRE001 follow_up anchor -- frob quality bind CLI dests are
  unwired by design (T-1567), never any code to write; must never reach a terminal
  state or WIRE002 orphans
land_commit: 1c8145a657c6ac01133d40d779f85841beb788c5
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
- 2026-08-20 attempt 2: Re-verified post T-2746: this is (b) genuinely dead-by-design, not a detector blind spot -- no code/detector change