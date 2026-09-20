---
id: T-draft-3c6c6336
title: 'Ticket sizing: points field, frob ticket points setter, refusal at start for
  unsized queued tickets, points-weighted flow and sprint show'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: story
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/tickets/_flow.py
- src/frob/tickets/_sprint.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_mutate.py
- docs/commands/ticket.md
- docs/modules/tickets-data-storage.md
scope_breadth_ack: true
scope_breadth_ack_reason: one model field threaded through new, setter, flow, sprint
  show and docs; each file is a one-hunk change
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a ticket with points=None, when frob ticket start runs without --unsized-ack,
    then it refuses with the remedy naming frob ticket points ID N
  evidence: []
- text: given --points 4, when frob ticket new or frob ticket points runs, then it
    refuses with the allowed set 1 2 3 5 8 13
  evidence: []
- text: given a sprint whose tickets carry points, when frob ticket sprint show LABEL
    runs, then it prints total points, points done and a points-weighted ETA
  evidence: []
- text: given a closed ticket, when frob ticket flow runs, then it reports actual
    hours from start to close and points per hour for the window
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: tickets need story points and/or effort hours, linted. Design decision (agreed default, revisit if the owner objects): points only, no hours field. points: int | None on Ticket and TicketSpec, allowed values 1 2 3 5 8 13 (Fibonacci, validated at write time like validate_milestone, never at ledger load). --points N on frob ticket new; frob ticket points ID N setter with T-1615 auto-commit. Hours are DERIVED, not entered: actual wall from the start transition to the close transition (already mined by _flow for velocity) is reported per ticket and as points-per-hour calibration in frob ticket flow, so the human enters one small number and the system measures the rest. ENFORCEMENT is at the state transition, not a repo-wide lint: frob ticket start refuses a ticket with points=None (single override flag --unsized-ack REASON, recorded on the ticket like scope_breadth_ack), frob ticket new WARNs when --points is omitted. This makes every ticket that actually enters work sized, needs no backfill of the 666 existing queued tickets, and never touches done/dropped/archived tickets -- the backwards-compat question disappears because old tickets only meet the check when someone starts them. frob ticket flow, sprint show, epic and board gain a points column and a points-weighted burn-down ETA next to the count-based one. Epics/stories roll up the sum of leaf points.