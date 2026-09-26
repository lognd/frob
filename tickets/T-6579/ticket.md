---
id: T-6579
title: frob ticket new hung for 5 h in D state at 1.7 GB RSS in the crunk repo (global
  tool, duplicate title)
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/app/ticket_runner/_new.py
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
Measured 2026-09-26 10:25 UTC: pid 708425, `frob ticket new --title "Screen
discovery adapter: React Router routes.tsx scanner" --kind feature --parent
T-0158 --scope src/cr...` from the global uv tool (dev 5e69b3fb68), cwd
/home/logan/projects/crunk, 19271 s elapsed, 2190 s CPU, state D, RSS
1.7 GB, wchan 0. A ticket with that exact title already existed (T-0174);
the duplicate-title path should refuse in under a second. The crunk root was
clean and no new ticket dir appeared; the owner killed it.

Investigate what a `ticket new` does that can grow to 1.7 GB and run for
hours (the --ack-related graph walk? a full check? a lock spin on
.frob/tickets.lock?) and bound it: a wall-clock deadline on every
subprocess or lock wait inside `ticket new` with a refusal naming the
stage, and the duplicate-title check before any graph or check work.
Positive control: a test that plants a held tickets.lock and shows ticket
new refuses with the lock holder within the deadline instead of waiting.
