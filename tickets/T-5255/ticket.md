---
id: T-5255
title: Land prepare phase adopts and promotes worktree-only drafts and drops stale
  promoted-draft dirs before the merge (ledger-only promotion, T-4652)
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
blocked_by:
- T-5166
- T-4738
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
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land.py
- tests/ticket_land_suite/**
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
Leaf C1 of T-5106 (~3 pts). Draft hygiene in the land's prepare phase. Blocked by T-5166 (sibling finalize regression) and T-4738 (phase skeleton); realises T-4652's rule that draft promotion is a ledger-only land operation.
- prepare enumerates every `tickets/T-draft-*` the branch carries that the root ledger does not: adopt it onto the root ledger and promote it there (one atomic ledger write, citations rewritten), BEFORE the merge.
- A draft dir that the root already promoted under a numbered id (title match, T-4571's merge-driver state precedence keeps the loser's dir) is dropped from the branch in prepare, so sibling finalize never sees it.
- A draft leased by another live worktree is left alone and named in the log; it is not a refusal.
- Replaces the coordinator's adopt-drafts.sh. Positive control: a branch carrying an unpromoted draft plus a stale promoted-draft dir lands clean; the same branch refuses today.
