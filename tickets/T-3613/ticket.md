---
id: T-3613
title: make land --queue/--drain (T-1444) the default agent path with pollable completion
  records
state: queued
kind: ux
origin: human
created: '2026-08-31'
priority: high
parent: T-3611
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
src/frob/tickets/_land_queue.py already implements a land queue/drain
design (one drainer, losers enqueue). Verify the CLI surface
(--queue/--drain/--plan flags), fix whatever keeps agents from using
it, and make ENQUEUE the documented default agent path: an
implementer's land call should return in seconds (intent recorded) with
the single drainer doing the serial work, instead of every agent
parking in a 60s sleep loop re-probing land.lock. Include: drainer
crash recovery (queue survives, next drainer picks up), loud per-intent
completion records agents can poll cheaply (a file, not a lock probe),
and the tickets-landing doc updated. Measure: agent wall-time from
"done implementing" to "shell free" drops from minutes/hours to
seconds; drain throughput unchanged or better.
