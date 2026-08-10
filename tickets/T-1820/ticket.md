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
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: true
anchor_reason: permanent WIRE001 follow_up anchor -- frob quality bind CLI dests are
  unwired by design (T-1567), never any code to write; must never reach a terminal
  state or WIRE002 orphans
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

## Done report

This is a WIRE001 follow_up anchor ticket (T-1856 precedent), not a normal
bug/feature fix: `frob quality bind`'s `--list-bindings`/`--list-sources`/
`--json` argparse dests are unwired by design (`frob.__main__._dispatch`
special-cases `quality bind` before `AppConfig` is ever built, T-1567) and
there is no code to write.

Work done:
1. Added a short in-code note next to each of the three existing
   `frob:waive WIRE001 follow_up="T-1820"` directives in
   src/frob/_cli_parsers/_quality.py, pointing future readers at the
   anchor marker and stating explicitly that this ticket must never reach
   a terminal state.
2. Set `Ticket.anchor=True` on T-1820 itself (`set_anchor`, T-1856),
   recording WHY: it is a permanent WIRE001 follow_up anchor, not
   deferred work.
3. Requeued (in-progress -> queued), releasing the T-0473 cross-worktree
   lease -- the same T-1778-documented workflow T-1874 (landed earlier in
   this series) added a land-time skip-close path for.

Gate consumption, not just prose: WIRE002 (`frob.gates._wire._wire002_
violations`) mechanically requires this ticket's `follow_up` target to
resolve to a real ticket in `_OPEN_STATES` -- keeping T-1820 queued
(never done/dropped) is what keeps the existing WIRE001 waivers in
_quality.py passing WIRE002, not the prose alone. The `anchor=True`
marker plus T-1874's land-time skip-close fix are what make it possible
to land this ticket's own record (this change) while it STAYS in that
open state -- before T-1874, landing a requeued QUEUED ticket with no new
failure-log entry would have hit the same `InvalidTransition: queued ->
done` T-1778 hit; this ticket lands via that same skip-close path, not a
DONE transition.

No code fix was made to make the dests "wired" -- they are unwired
deliberately, and wiring them would defeat the point of the anchor.

### Changed
```
 tickets/T-1820/ticket.md | 6 ++++++
 1 file changed, 6 insertions(+)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
