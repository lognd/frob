---
id: T-5131
title: 'perf: frob ticket flow hangs 10+ minutes, one git log --follow -p subprocess
  per ticket over 11k commits'
state: done
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_flow.py
- src/frob/app/ticket_runner/_mutate.py
- tests/test_tickets_velocity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_velocity.py
  reason: T-5131 needs a repro test for the N+1 git-spawn regression (BUG002 evidence
    requirement)
  actor: logan
  at: '2026-09-20'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: static audit 2026-09-20 pinned the exact call chain
  actor: logan
  at: '2026-09-20'
  old_length: 784
  new_length: 1509
evidence:
- tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mode_mines_via_v2_state_transitions
- tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mining_spawns_git_a_constant_number_of_times
designated_repro_test: tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mining_spawns_git_a_constant_number_of_times
acceptance:
- text: given the dev ledger at HEAD, when frob ticket flow runs cold, then it prints
    the table in under 10 s wall
  evidence:
  - tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mode_mines_via_v2_state_transitions
  - tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mining_spawns_git_a_constant_number_of_times
- text: given the fix, when frob check runs, then a PERF rule flags a git subprocess
    inside a per-ticket loop in src/frob/tickets
  evidence:
  - tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mining_spawns_git_a_constant_number_of_times
acceptance_amendments:
- op: remove
  index: 2
  old_text: given a warm cache and one new land commit, when frob ticket flow runs,
    then it mines only the new commit and finishes in under 2 s
  new_text: null
  reason: 'T-5131''s own Fix section offered two alternatives: batch the git spawns
    (implemented here, satisfies criterion 1) OR persist mined transitions in a head-sha-keyed
    cache for the warm/incremental case (criterion 2). This ticket implements only
    the batched-walk alternative; the warm-cache/incremental-mining criterion is split
    out to T-5154 (filed while working T-5131) rather than blocking this ticket''s
    real, measured 10+min -> 9.7s fix on unrelated follow-on work.'
  actor: logan
  at: '2026-09-20'
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20 on dev at 0.531.0: frob ticket flow produced no output in 3 minutes and was still running at 10+ minutes before being killed. _mine_done_transitions_v2 calls v2_state_transitions(root, ticket_id) per ticket, each spawning git log --follow -p on that ticket's file; the history has 11436 commits touching tickets/ and 691 open plus the archive, so the walk is O(tickets x history). Fix: one git log --name-status (or --format with -- tickets/) pass over the whole tickets/ tree, group by path, then diff state: per commit; or persist the mined transitions in .frob/cache.db keyed by head sha and mine only new commits incrementally. Per the perf-findings-become-lint-rules directive, ship a PERF00x detector for subprocess-in-loop-over-ticket-ids alongside the fix.

AUDIT DETAIL: _mine_done_transitions_v2 -> _store.v2_state_transitions -> _v2_path_lineage -> _v2_rename_source spawns git log --diff-filter=R -M100% --name-status -- <path>, then _mine_v2_path_transitions spawns git log --reverse -p -- <path>: at least 2 full-history revision walks per ticket, ~1400 walks over 11436 commits. The docstring's 'small disjoint slice' claim is wrong: the slice is small but git still walks every commit to find it, so v2 is O(tickets x commits), worse than the v1 single walk it replaced. Batched fix: ONE git log --reverse --name-status -p -- tickets/ walk parsed into {ticket_id: [(sha, iso, state)]} plus ONE --diff-filter=R -M100% pass for lineage; 2 spawns total, same -M100% semantics.