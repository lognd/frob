---
id: T-2691
title: frob ticket land has no externally-pollable progress/lock-contention status
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
- scripts/fleet_status.py
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
An operator watching `frob ticket land` while the fleet is contended has
no visibility into whether it is progressing, waiting on land.lock, or
was preempted/killed mid-flight -- the only way to tell is inspecting the
process tree and `.frob/land.lock` by hand (observed directly during a
2026-08-20 fleet-serialization incident: a land killed by its own
foreground timeout under lock contention left a MERGE_HEAD-in-progress
worktree, an orphaned land.lock entry, and no visible signal beyond a
truncated log that the attempt had failed rather than succeeded -- 270s
of wall clock, mostly spent waiting on another ticket's held lock, then
nothing landed and no land commit produced).

`frob ticket land` already logs a WARNING when it starts waiting on a
held land.lock ("waiting up to 500s before refusing") and again when it
reclaims an orphaned one -- but that line only reaches whoever is reading
stdout live; it is not surfaced anywhere an operator or coordinator can
poll (no `.frob/land-status.json`, no `frob ticket show`/`fleet_status`
field distinguishing "queued behind lock" from "actively running gates"
from "dead, needs a retry"). Fold this into the T-2141 disclosure
direction: a small land-status marker file (holder pid, phase,
started_at, last-heartbeat) that `fleet_status.py` and a future `frob
land status` can read, so "is my land alive, and did it accomplish
anything" stops requiring manual `ps`/`git log --grep`/`git status`
archaeology after the fact.

Filed from the T-2141/T-1549/T-2303 series per an explicit coordinator
instruction during a live fleet-serialization hold (2026-08-20): the
starved-batch incident that motivated the hold is itself the missing-
disclosure case this ticket should fix.
