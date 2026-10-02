---
id: T-0035
title: gob-git commit_paths leaves other checkouts holding the ref with a stale index
state: in-progress
kind: bug
origin: agent
created: '2026-10-02'
priority: high
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob-v2-wt/t-0035
branch: t-0035
scope:
- crates/gob-git/**
- crates/frob-land/src/git.rs
- crates/frob-land/src/land.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: crates/frob-land/src/land.rs
  reason: the git restore workaround lived in land.rs, not git.rs
  actor: logan
  at: '2026-10-02'
designated_repro_test: null
acceptance:
- text: Given a primary with main checked out and a linked worktree, when commit_paths
    on refs/heads/main runs from the worktree, then the primary's index and tickets/
    files match the new tip and a following commit_paths from the primary succeeds
  evidence: []
threat: null
component: gob-git
anchor: false
anchor_reason: null
land_commit: null
---
commit_paths syncs index and worktree files only in the checkout it runs from. A ledger commit made from a linked worktree (evidence add, work transition, land) advances the ref while the primary checkout, which has that branch checked out, keeps the old tickets/ files and index; the next ledger write from the primary refuses with E-GIT-LOCAL-EDITS. frob-land works around it with git restore. Fix in gob-git: after the CAS succeeds, sync every worktree (list_worktrees) whose HEAD is symbolic to the ref, updating index entries and files for exactly the changed paths under index.lock, skipping and reporting any checkout with genuine local edits to those paths. Then remove the git restore workaround from frob-land (crates/frob-land/src/git.rs) if it is in scope, otherwise report it.