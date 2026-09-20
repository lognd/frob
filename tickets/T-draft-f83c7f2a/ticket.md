---
id: T-draft-f83c7f2a
title: 'perf: frob ticket flow hangs 10+ minutes, one git log --follow -p subprocess
  per ticket over 11k commits'
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_flow.py
- src/frob/app/ticket_runner/_mutate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the dev ledger at HEAD, when frob ticket flow runs cold, then it prints
    the table in under 10 s wall
  evidence: []
- text: given a warm cache and one new land commit, when frob ticket flow runs, then
    it mines only the new commit and finishes in under 2 s
  evidence: []
- text: given the fix, when frob check runs, then a PERF rule flags a git subprocess
    inside a per-ticket loop in src/frob/tickets
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20 on dev at 0.531.0: frob ticket flow produced no output in 3 minutes and was still running at 10+ minutes before being killed. _mine_done_transitions_v2 calls v2_state_transitions(root, ticket_id) per ticket, each spawning git log --follow -p on that ticket's file; the history has 11436 commits touching tickets/ and 691 open plus the archive, so the walk is O(tickets x history). Fix: one git log --name-status (or --format with -- tickets/) pass over the whole tickets/ tree, group by path, then diff state: per commit; or persist the mined transitions in .frob/cache.db keyed by head sha and mine only new commits incrementally. Per the perf-findings-become-lint-rules directive, ship a PERF00x detector for subprocess-in-loop-over-ticket-ids alongside the fix.