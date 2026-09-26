---
id: T-draft-018385d7
title: land claim check attributes another ticket's TICK015 (dead worktree agent,
  unlanded) to the landing ticket and refuses with ClaimDivergence
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
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/gates/_tickets_gate.py
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
Reported by the crunk session (2026-09-26): T-0176's worktree agent had
finished but not landed, so after the 6 h lease age TICK015 (dead
worktree/branch/process reading, T-5121) fired for T-0176. T-0160's first
land then failed with ClaimDivergence because that TICK015 finding showed
up as a new in-scope error in T-0160's claim check, although it is about
another ticket. Verified on dev b41443f46d: TICK015 findings carry the
tickets.md identity, so the ClaimDivergence comparator in _rapid_sweep.py
(`("ClaimDivergence", "tickets.md")` identity) cannot tell whose ticket a
TICK015 row is about.

Deliver: TICK015 (and the other per-ticket TICK rows) carry the subject
ticket id in the finding identity; the land claim check ignores TICK rows
whose subject is not the landing ticket and logs them as informational;
a TICK015 about the landing ticket itself still refuses. Positive control:
a fixture ledger with a dead-worktree sibling; the landing ticket's claim
check passes and the log names the sibling's TICK015 as ignored.
