---
id: T-4653
title: 'Lease kernel: explicit acquire/release lifecycle, append-shared registry files,
  lease store independent of land and gates'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4651
tier: story
sprint: null
runs_last: false
milestone: 0.535.0
flavour: user_story
due: null
rank: null
points: null
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic/story rollup for the kernel-decoupling epic:
  all file work lives in the leaf children; this ticket carries no write lease by
  design'
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LEASES concern of the kernel-decoupling epic (T-4651).

Today scope conflates a WRITE LEASE with EVIDENCE COVERAGE (T-3927), the lease has no lifecycle at all, and .git/frob-leases/<id>.json is a whole-file claim. Measured consequence this week: `frob ticket drop` leaves its lease in place, so a dropped ticket keeps blocking sibling `scope --add` and PassengerTickets until someone deletes the file by hand; whole-file leases on shared registry files (design/frob.strata, docs/design/registry/capability-via-ratchet.lock.json, docs/modules/gates.md, the frob.toml severity zone) block every sibling land with CrossTicketLeakage; and `frob ticket doable`/`new` take 5+ minutes because every call rescans every lease quadratically.

Target shape:
- explicit lifecycle: ACQUIRE on `start`, RELEASE on EVERY terminal transition -- close, drop, fail, requeue -- with each transition logged.
- append-shared registry files: a declared set of files where two tickets may hold concurrent append-only claims.
- the lease store is a standalone module that neither land nor gates reach around; land and gates consume it through its API.
