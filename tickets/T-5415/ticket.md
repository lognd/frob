---
id: T-5415
title: 'Draft promotion races: worktree lands promote root drafts to ids that collide
  with dev''s later promotion (rename/rename ledger conflicts)'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
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
Observed 2026-09-23 on T-5307 and T-5313: a land (or dry-run) in a worktree promoted root-visible drafts T-draft-4d1978b3 and T-draft-c7aa1ed2 to T-5398/T-5399 (and T-5400) while the runner promoted the same drafts on dev to T-5402/T-5403; the next merge of dev then fails with rename/rename conflicts on tickets/*.md and the land refuses MergeConflict. Draft promotion is a ledger-identity operation and must happen exactly once, on the land branch (dev), never inside a ticket worktree unless the draft is that ticket's own follow-up filed in that worktree. Fix: land/dry-run must skip promoting drafts whose directory is already present on the target branch, and the promote verb must refuse in a worktree with a hint to run it on dev (override flag --here). Regression test: two worktrees plus dev racing the same draft end with one id. Coordinator recipe until then: merge dev with dev's side on tickets/**, then drop worktree-only T-#### dirs whose title matches a dev ticket (scratchpad dedupe-ledger.sh).