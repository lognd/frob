---
id: T-3466
title: Expose CrossTicketLeakage as a real frob check gate rule (needs worktree/base_ref
  plumbing)
state: queued
kind: feature
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
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
Filed from T-3456's own scoping-out. T-3456 wired LANDPARITY001 (T-2114 doc/test-edge) and LANDPARITY002 (T-2214 diff-scoped ARCH001) into frob check as the 'land_parity' gate, both pure functions of (worktree, merge_base, touched_paths) needing nothing frob check cannot already provide. CrossTicketLeakage (src/frob/tickets/_land.py::_check_cross_ticket_leakage) is structurally different: it needs worktree/base_ref context specific to the LAND being performed (which OTHER open ticket's lease overlaps THIS one's touched files), not a property of root's tree alone the way every other frob.gates rule is. frob check runs against a single root; it has no generic concept of 'compare this worktree against main to find cross-ticket overlap' the way frob ticket land's own precheck does. Wiring this into frob check needs frob check itself to thread worktree-vs-main comparison context through generically (new CLI plumbing, likely a --worktree or --base flag threaded into the gate-state builder), not just a new gate module reusing an existing pure function the way LANDPARITY001/002 did. Read _check_cross_ticket_leakage's own signature and _land_precheck's call site before scoping; may also need to decide whether this check even makes sense outside an actual multi-ticket fleet context (a solo frob check run in one worktree has no other tickets' leases to compare against unless it reads the SAME shared ticket-lease state frob ticket land reads).