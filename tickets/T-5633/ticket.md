---
id: T-5633
title: frob ci validity <run> and frob ci watch <run>
state: in-progress
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.535.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5633
branch: t-5633
scope:
- src/frob/coord/_ci_watch_poll.py
- tests/frob/coord/test_ci_watch_poll.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/coord/_ci_watch_poll.py
  reason: 'CI-2 own new file: coord watch''s shared poll primitive over frob.ci_validity;
    ci_runner.py/_ci.py/config.py additions deferred until CI-1 (T-draft-c099f096)
    lands and releases its lease'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/frob/coord/test_ci_watch_poll.py
  reason: 'CI-2 own new file: coord watch''s shared poll primitive over frob.ci_validity;
    ci_runner.py/_ci.py/config.py additions deferred until CI-1 (T-draft-c099f096)
    lands and releases its lease'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob ci validity <run-id> and frob ci watch <run-id>: wrappers over frob.ci_validity (STILL VALID / STALE classification against the current diff) and a poll loop that emits the run's completion with per-job conclusions, at a rate that respects the API limit; coord watch calls this primitive. Positive control: a fixture whose touched symrefs classify as unrelated-to-diff is reported verbatim, not unknown.
