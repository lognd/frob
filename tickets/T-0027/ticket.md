---
id: T-0027
title: gob-git test delete_via_none_and_local_edit_refusal fails in the primary checkout
state: queued
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
points: 2
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
- crates/gob-git/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the primary checkout and any ticket worktree on this host, when cargo
    nextest run -p gob-git runs, then every test passes in both
  evidence: []
threat: null
component: gob-git
anchor: false
anchor_reason: null
land_commit: null
---
After landing T-0010 the test gob-git::ledger delete_via_none_and_local_edit_refusal passes in the ticket worktree but fails in the primary checkout (crates/gob-git/tests/ledger.rs line 163). The difference is environmental (the primary is the main checkout; global git config on this host sets autocrlf, and the test creates temp repos). Find the real cause, make the test independent of the host git configuration and checkout kind, and keep the LocalEdits behaviour correct.