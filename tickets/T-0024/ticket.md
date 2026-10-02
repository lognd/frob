---
id: T-0024
title: 'frob-land: synchronous land with preconditions, dry-run, close on land'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0023
- T-0019
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
- crates/frob-land/**
- crates/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a worked ticket with green check and evidence, when frob land runs,
    then the base branch contains the work, the ticket is done with an outcome, the
    lease is gone, and the ledger commit is on the ledger ref
  evidence: []
- text: Given a red check, when frob land runs, then exit is 3, the remedy names frob
    check --ticket, and nothing moved
  evidence: []
threat: null
component: frob-land
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/frob-land per tickets.md section 10 as updated by D23 and D25. frob land [<ticket>] [--dry-run] [--push] [--wait <secs>]: preconditions (ticket in-progress and leased by this worktree, worktree clean, base merged, frob check --ticket green at the configured fail_on, evidence present), take the land lock in the git common dir (--wait bounds acquisition only), fast-forward or merge the ticket branch onto the base branch in the primary (gob-git; spawn fallback on conflicts), write the land event and close the ticket with outcome through the ledger ref, release the lease, optionally remove the worktree, optionally push. --dry-run prints the plan as a list of steps with a plan digest. Exit codes per the cli.md table (refused preconditions exit 3 with remedy, non-retryable where retrying cannot help). Everything synchronous; no job ids. Integration test lands a ticket end to end in a temp repo.