---
id: T-draft-ff65ecc5
title: per-module leases and per-module via-ratchet locks (D-M7), replacing the whole-file
  lease and lock
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-draft-6e70e293
- T-draft-a379c28b
- T-draft-dd69498c
- T-draft-e51e8f8d
- T-draft-5b9f1e10
- T-draft-f78b975b
- T-draft-54ccb3cd
- T-draft-d97a3de1
- T-draft-d4a0057c
- T-draft-5cac4632
- T-draft-22cc8b71
parent: T-draft-0a0c7b43
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/capability-via-ratchet.lock.json
- src/frob/strata/_scope_config.py
- src/frob/gates/_sys_selfaudit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: 'Given two tickets scoped to design/a.strata and design/b.strata, when both
    are started, then both leases are granted -- positive control: before this leaf
    the same pair is refused on the whole-file lease.'
  evidence: []
- text: Given a `via` addition to a node in module M, when the ratchet check runs,
    then only design/M.via.lock.json needs its accepted_count bump, and the other
    modules' locks are untouched.
  evidence: []
- text: Given the split locks, when the SYS gates run, then the SELFAUDIT001 radius
    for a touched module file is that module's nodes only.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Per-module leases and per-module via-ratchet locks (owner decision D-M7: LAST,
after isolation is real -- per-module leases over a still-entangled design move
the conflict rather than removing it). Until this leaf, grants and the ratchet
lock stay WHOLE-FILE.

Split docs/design/registry/capability-via-ratchet.lock.json into per-module
locks (design/<module>.via.lock.json, surface.md:418-452), and make the lease
and SCOPE002 radius per module file (design/<module>.strata) instead of the
whole monolith. This is the payoff for SF-06 (ratchet churn) and SF-18 (whole-
file lease contention): two agents touching different modules must no longer
serialize on one file or one lock.
