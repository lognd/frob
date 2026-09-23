---
id: T-5256
title: 'A refused land restores the worktree: ledger files, staged land-owned files
  and pre-land commits unwound, refusal text on the intent record'
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
blocked_by:
- T-4739
parent: T-5106
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
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
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_queue.py
- tests/ticket_land_suite/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: observed failure-log root dirt cascading into DirtyMain refusals during
    queue drains
  actor: logan
  at: '2026-09-22'
  old_length: 851
  new_length: 1297
- mode: append
  reason: closed-but-unlanded recurrence during queue drains
  actor: logan
  at: '2026-09-22'
  old_length: 1297
  new_length: 1714
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf D of T-5106 (~2 pts). A refused land leaves the worktree exactly as it found it. Blocked by T-4739 (pure compose makes the unwind a no-op for tree state).
- Any refusal after finalize (sibling finalize failure, close failure, unscoped sweep refusal, timeout) restores the worktree's ticket ledger files (state back from done, draft ids back), unstages land-owned files, and removes the "wip: pre-land snapshot"/"finalize and close" commits it added, restoring the branch tip recorded at prepare.
- The intent record (`.frob/land-queue/<id>.json`) carries the refusal text verbatim and the branch tip it restored to; `--status` prints both.
- Replaces the coordinator's `git checkout -- tickets/ CHANGELOG.md` after every refusal. Positive control: a planted post-finalize refusal leaves `git status` clean and `state:` unchanged in the worktree.


Coordinator note 2026-09-22: when --drain rejects an entry, record_failure appends a '## Failure log' to tickets/<id>/ticket.md in the ROOT checkout without committing it, so the next entry in the same drain refuses with DirtyMain ('root checkout has uncommitted changes'). Seen on T-5199, T-5136, T-5215, T-4713 in one night. The failure record belongs on the intent record and the worktree ledger, or must be committed atomically on the root.

Coordinator note 2026-09-22 (second class): a land refused AFTER finalize by the unscoped pre-land sweep leaves the ticket at state=done on the ROOT ledger with land_commit null and no code on dev (seen: T-4690 on 09-21, T-4698 on 09-22). Every sibling land then refuses with TICK005 because their worktree carries the ticket at in-progress. The unwind must restore the root ledger state too, not just the worktree.