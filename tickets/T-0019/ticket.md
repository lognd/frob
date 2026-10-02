---
id: T-0019
title: 'frob-lease + frob-worktree: locked scope leases and frob work'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0018
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 8
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
- crates/frob-lease/**
- crates/frob-worktree/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: crates/frob/**
  reason: verb wiring moves to T-0030 so the three crates run in parallel
  actor: logan
  at: '2026-10-02'
designated_repro_test: null
acceptance:
- text: Given two tickets with overlapping globs and no files yet, when both run work
    concurrently, then exactly one succeeds and the other gets exit 3 E-LEASE-HELD
  evidence: []
- text: 'Given a held lease, when the same holder runs work again, then it returns
    already: true with the same worktree path'
  evidence: []
threat: null
component: frob-lease
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/frob-lease and crates/frob-worktree per tickets.md section 6 as updated by D26 and audit L21. Leases live in .git/frob/leases/<ticket>.toml under one lock file .git/frob/leases.lock (fs2 or rustix flock); holder = actor plus worktree path; overlap = glob intersection (globset text analysis) OR resolved-set intersection, with [tickets] registry_files exempt; TTL knob with renewal on any frob verb from the worktree; steal with --steal --reason recorded as an event. frob work <ticket>: idempotent for the same holder (returns existing worktree and lease), refuses with E-LEASE-HELD exit 3 naming the holder otherwise; creates the worktree at the [worktree] dir knob (default ../<repo>-wt/<ticket-handle>) via gob-git (spawn fallback allowed), branch ticket/<handle>, merges the base branch, transitions the ticket to in-progress, writes the lease. Verbs: work, start, requeue (release), ticket contention. SCOPE001 rule: diff of the worktree against base touches files outside the lease (reuse gob-git diff). Tests: concurrent work calls on two overlapping tickets from two threads produce exactly one lease.