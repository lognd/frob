---
id: T-6569
title: land claim check attributes another ticket's TICK015 (dead worktree agent,
  unlanded) to the landing ticket and refuses with ClaimDivergence
state: in-progress
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
worktree: /home/logan/projects/frob
branch: dev
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/gates/_tickets_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'crunk: TICK015 on the landing ticket itself now blocks lands'
  actor: logan
  at: '2026-09-27'
  old_length: 1033
  new_length: 1769
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


Now BLOCKING (crunk-ba, 2026-09-27): when an implementer finishes and
exits, TICK015 fires on the landing ticket's OWN worktree (no live
process cwd'd there), and the land's ClaimDivergence refuses; `frob
ticket done-report` in the worktree runs a scoped check with files=0, so
the refresh never captures the TICK015 row and the retry fails
identically. Working workaround in crunk (T-0257, T-0211 landed with
it): keep a live process with cwd in the worktree (a background sleep)
for the duration of `frob ticket land`. Deliver in addition: the landing
ticket's own TICK015 row is excluded from its claim comparison (a land in
progress IS the live use of that worktree), and the done-report's
scoped check must not run with files=0.
