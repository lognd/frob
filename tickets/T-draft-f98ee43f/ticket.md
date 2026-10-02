---
id: T-draft-f98ee43f
title: 'frob-ack: frob.lock via gob-lock, ack verb, graph why and affects, DRIFT and
  AFFECT rules'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0013
- T-0014
- T-0017
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
- crates/gob-lock/**
- crates/frob-ack/**
- crates/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given an acked symbol whose signature changes, when check runs, then DRIFT003
    fires and frob ack clears it
  evidence: []
- text: Given a frob:doc directive pointing at a missing heading, when check runs,
    then DRIFT002 fires with the nearest heading
  evidence: []
threat: null
component: frob-ack
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-lock and crates/frob-ack per code-model.md sections 2 and 6 and D28. gob-lock: lock file format (TOML, sorted, one entry per symref with the three facet digests and the ack actor/date/reason), load/save/diff, product-parametric file name. frob-ack: frob.lock at the repo root; frob ack <symref|path> [--all] [--reason] records current digests through a ledger-style commit (gob-git commit_paths on the current branch, since frob.lock is code-adjacent, not ledger); DRIFT001 symbol whose doc-bound target (frob:doc) changed since ack, DRIFT002 bound doc anchor missing, DRIFT003 ack stale (sig digest changed), AFFECT001 dependent public symbol changed without its own ack; frob graph why <symref> (why a finding fires, path through the graph) and frob graph affects <symref>. Rules use the persisted findings cache keyed by graph digest. Dogfood against this repository.