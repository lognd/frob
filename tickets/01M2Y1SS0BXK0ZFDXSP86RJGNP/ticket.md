+++
id = "01M2Y1SS0BXK0ZFDXSP86RJGNP"
title = "perf: frob ticket flow hangs 10+ minutes, one git log --follow -p subprocess per ticket over 11k commits"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-09-20T00:00:02Z"
aliases = ["T-5131"]
labels = ["milestone:1.0.0", "component:tickets"]
scope = ["src/frob/tickets/_flow.py", "src/frob/app/ticket_runner/_mutate.py", "tests/test_tickets_velocity.py"]

[[acceptance]]
text = "given the dev ledger at HEAD, when frob ticket flow runs cold, then it prints the table in under 10 s wall"
bound = false

[[acceptance]]
text = "given the fix, when frob check runs, then a PERF rule flags a git subprocess inside a per-ticket loop in src/frob/tickets"
bound = false
+++

Measured 2026-09-20 on dev at 0.531.0: frob ticket flow produced no output in 3 minutes and was still running at 10+ minutes before being killed. _mine_done_transitions_v2 calls v2_state_transitions(root, ticket_id) per ticket, each spawning git log --follow -p on that ticket's file; the history has 11436 commits touching tickets/ and 691 open plus the archive, so the walk is O(tickets x history). Fix: one git log --name-status (or --format with -- tickets/) pass over the whole tickets/ tree, group by path, then diff state: per commit; or persist the mined transitions in .frob/cache.db keyed by head sha and mine only new commits incrementally. Per the perf-findings-become-lint-rules directive, ship a PERF00x detector for subprocess-in-loop-over-ticket-ids alongside the fix.

AUDIT DETAIL: _mine_done_transitions_v2 -> _store.v2_state_transitions -> _v2_path_lineage -> _v2_rename_source spawns git log --diff-filter=R -M100% --name-status -- <path>, then _mine_v2_path_transitions spawns git log --reverse -p -- <path>: at least 2 full-history revision walks per ticket, ~1400 walks over 11436 commits. The docstring's 'small disjoint slice' claim is wrong: the slice is small but git still walks every commit to find it, so v2 is O(tickets x commits), worse than the v1 single walk it replaced. Batched fix: ONE git log --reverse --name-status -p -- tickets/ walk parsed into {ticket_id: [(sha, iso, state)]} plus ONE --diff-filter=R -M100% pass for lineage; 2 spawns total, same -M100% semantics.
