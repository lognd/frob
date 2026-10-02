---
id: T-0029
title: Reconcile design docs with milestone-1 implementation decisions
state: queued
kind: docs
origin: agent
created: '2026-10-02'
priority: medium
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
worktree: null
branch: null
scope:
- docs/design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the design set after the change, when grepped for each item in the body,
    then the text matches the landed code and the README log has one row per decision
  evidence: []
threat: null
component: docs
anchor: false
anchor_reason: null
land_commit: null
---
Collect the deviations recorded in the done-reports of T-0003 through T-0027 and fold them into docs/design plus the README decision log: cache file name cache.sqlite (architecture.md says cache.db); [check] fail_on default error; cas_retries under [git]; [tickets] ref default refs/heads/main; envelope carries verb and already (and whether they move into gob-diagnostics); tree-sitter core pinned 0.27.0 with ast-grep-core 0.45.3 compatible; gix 0.87.1; gob-text owns TextSize/TextRange; impl member symref forms Type.method and Type[Trait].method; whitespace-collapsed facet normalization; PROC001 allow list includes the frob binary crate; FacetDigest vs gob-walk Digest; mdtest one nextest case per corpus. Each becomes a decision-log row or a corrected sentence; nothing is left contradicting the code.