---
id: T-3155
title: Extract evidence_covers_scope out of frob.gates to break the gates<->tickets
  edge
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/__init__.py
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
## Description + plan

MEASURED (T-3142): `frob cycle src/frob` still reports one 182-node SCC
(unchanged from T-3086's own measurement -- confirmed fresh on the
current tree, `frob.findings` did not touch this SCC's membership).
`frob cycle`'s printed node sequence is SCC membership order (a Tarjan
DFS discovery order over `frob.cycle.graph.find_cycles`), NOT a literal
walk of real edges between each consecutive pair -- verified by checking
several consecutive pairs from the printed path for an actual Python
import in either direction and finding none (e.g.
`gates/_rule_id_scan.py` <-> `tickets/_new_gate_rule_acceptance.py`: the
only connection is a DOCSTRING mention of the dotted path, not an
`import`). Any cut proposal has to be built from real import statements,
not adjacency in the printed text.

Real, verified import edges (both confirmed by reading the exact lines,
not inferred from the printout):

1. `src/frob/gates/__init__.py:297` -- eager, top-level:
   `from frob.tickets import Ticket, TicketQueue, TicketState, load_queue`
   (plus `_models`/`_provisional`/`_store` imports at lines 298-312).
   `frob.gates`' OWN package `__init__` depends on `frob.tickets`.

2. `src/frob/app/ticket_runner/_close_cmd.py:300` -- deferred,
   function-local: `from frob.gates import evidence_covers_scope`.
   `evidence_covers_scope` (D-02, `frob.gates.__init__:653`) is the
   SAME module that carries edge 1 above -- so this is a real,
   already-known cycle: `_close_cmd.py`'s own author already deferred
   this import specifically to dodge an eager cycle (it is the only
   caller of `evidence_covers_scope` outside `frob.gates` itself, per
   that function's own docstring: "A caller (today:
   `frob.app.ticket_runner`'s `_close`/`_land` ...)").

This is the concrete shape of "the tickets<->gates weld" the coordinator
pointed at: `frob.gates` needs `Ticket`/`TicketQueue`/`TicketState` for
its own TICK-family gates (`_tickets_gate.py` separately confirms this
same direction), and `frob.app.ticket_runner` (the close/land command
family, tightly bound to `frob.tickets`) needs `evidence_covers_scope`
from `frob.gates` to decide D-02. Two real edges, opposite direction,
same two packages.

Proposed cut: `evidence_covers_scope` (and its private D-02 helpers in
`frob.gates.__init__`) operate entirely on `Ticket`/ticket-scope data;
the only genuinely gates-side input is `GraphSnapshot` (already an
injected parameter, not an import gates forces on its caller -- see the
function's own docstring, "computes this against a `GraphSnapshot` and
passes the result into `frob.tickets.transition`/`land`'s `covers_scope`
parameter", i.e. the INVERSE direction is already dependency-injected).
Moving `evidence_covers_scope` itself out of `frob.gates` into
`frob.tickets` (or a neutral leaf, e.g. `frob.tickets._scope_coverage`)
removes `app/ticket_runner/_close_cmd.py`'s need to import `frob.gates`
for this specific call, mirroring the T-3086 `frob.findings` extraction
pattern (pull the shared logic to the leaf side, don't leave one package
reaching into the other for it). This does NOT remove `_tickets_gate.py`'s
own (likely inherent) gates->tickets edge -- that is a SEPARATE edge,
deliberately not addressed by this one cut, per T-3086's own directive to
cut once, re-measure, then name the next sibling.

Do NOT expand this into a full serve/tickets/testing/app pass (T-2667,
scope `src/frob/serve/_tools.py`, a DIFFERENT package quartet) or an
internal tickets/-only split (T-2202's Leaf 3:
`_accept.py`/`_setters.py`/`_land_finalize.py`/`_land_verify.py`, no
gates involvement) or a LARGE001 line-count decomposition of
`_close_cmd.py`/`_land_cmd.py`/`_lifecycle.py` (T-2835, a size concern,
not an import-cycle one) -- this ticket's scope is disjoint from all
three; checked before filing.

## Scope + leases
- src/frob/gates/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/__init__.py
