---
id: T-1645
title: TICK009 demands scope precision from queued tickets, before the touched set
  can be known
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/test_gates.py
- docs/modules/gates.md
- src/frob/app/ticket_runner/_lifecycle.py
- tests/unit/test_app_runners_batch7.py
- tests/test_gates_tick009_tick010.py
- src/frob/app/ticket_runner/_query.py
- tests/unit/test_app_runners_t0714_doable_summary.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: T-1645's start-time nudge enhancement lives in the start command, not just
    the TICK009 gate
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: T-1645's start-time nudge enhancement lives in the start command, not just
    the TICK009 gate
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_gates_tick009_tick010.py
  reason: TICK009 unit tests live here, not test_gates.py
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: doable's scope-breadth summary mirrors TICK009 and must stay consistent
    with the QUEUED exemption
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_app_runners_t0714_doable_summary.py
  reason: asserts doable's scope-breadth summary, which now must exclude QUEUED like
    TICK009
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_queued_ticket_no_finding_even_with_broad_scope
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_chronically_over_broad_glob_warns
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_in_progress_over_broad_glob_still_warns
- tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_queued_tickets_never_contribute_a_nudge
- tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_warns_on_over_broad_scope
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_precise_scope_warns_nothing
designated_repro_test: null
threat: null
component: null
---
TICK009 flags a ticket whose scope glob matches more than 25 files, asking the author to "narrow it to the specific files this ticket touches". It fires regardless of the ticket's STATE.

For an in-progress ticket that is exactly right: the work is underway, the touched set is knowable, and a sprawling scope both hides drift and (per T-1639) locks files against every other land.

For a QUEUED ticket it asks for information that does not exist yet. Nobody has opened the code. "The specific files this ticket touches" is a prediction, and the honest prediction for "audit why frob missed each doc gap" or "make capability detection symbol-resolved" genuinely is `src/frob/gates/**`. Demanding precision earlier than it can be known has two bad outcomes, both observed here: the author either invents a narrow list that turns out wrong (and the implementer scope-adds anyway, so the declaration was noise), or leaves the honest broad scope and carries a permanent warning.

Current state on main: 48 tickets carry TICK009, ~204 findings. 40 of the 48 were filed in a single session of incident-response ticketing, where the honest scope for most really was a package glob.

Proposed: gate TICK009 on state, exactly as T-1639 proposes for CrossTicketLeakage.
- QUEUED: no finding. The scope is an estimate.
- IN-PROGRESS / done: finding as today. By `frob ticket start` the author has the code open and can say what they touch; that is also when a broad scope starts costing other people.

Consider also making `frob ticket start` the moment of enforcement -- surfacing "your scope matches 68 files, narrow it now" at start time is far more actionable than a warning that accumulates silently in a full-repo check nobody reads per-ticket.

Related and worth deciding together: T-1639 (queued scope should not block lands) and T-1614 (the waiver audit, which will meet the same "was this justified when written or only now?" question). All three are the same underlying issue -- a declaration made before the work is a different kind of claim than one made during it, and frob currently treats them identically.

Do NOT resolve this by raising the 25-file threshold. The threshold is not the problem; applying the rule at the wrong point in the lifecycle is.