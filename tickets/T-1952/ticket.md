---
id: T-1952
title: Re-ack docs/modules/tickets.md sections for T-1935's rapid-sweep wording change
  once T-1720's lease frees
state: queued
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1935 changed _file_regression_ticket's and run_deferred_post_land_sweep's own count/wording (identity vs finding count caveat) in src/frob/app/ticket_runner/_rapid_sweep.py, but docs/modules/tickets.md#symbolic-attribution-t-1690 and #deferred-post-land-sweep-rapid-only-t-1684 could not be touched or re-acked because docs/modules/tickets.md was under T-1720's live lease at the time (frob:waive AFFECT001/DRIFT001 both reference this ticket). The underlying attribution/filing/sweep BEHAVIOR is unchanged -- only reported wording -- so no doc CONTENT edit is actually owed, but the ack/digest needs refreshing: run frob ack src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket and frob ack src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep once T-1720 releases the lease, then drop the two waivers.