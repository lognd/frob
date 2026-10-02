---
id: T-0030
title: gob-git LocalEdits check refuses after git checkout under core.autocrlf=true
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
- text: Given a repo with core.autocrlf=true and a checked-out ledger ref, when commit_paths
    writes a ticket twice with a checkout in between, then the second write succeeds
    and a genuine local content edit still refuses
  evidence: []
threat: null
component: gob-git
anchor: false
anchor_reason: null
land_commit: null
---
check_local_edits in crates/gob-git/src/ledger.rs hashes raw disk bytes. With core.autocrlf=true (this host's global git config) git checkout rewrites tracked text files as CRLF, so the next commit_paths on a checked-out ref refuses with E-GIT-LOCAL-EDITS although nothing changed. Compare after applying the worktree-to-index filters (gix pipeline for the path's attributes and autocrlf) or compare normalized content, so a pure line-ending difference is never a local edit. Add a test that sets core.autocrlf=true in the temp repo config, checks out, then commits again successfully, while a real content change still refuses.