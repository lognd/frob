---
id: T-1893
title: Document T-1886 WAIVE004 proportional-check sample-size floor in gates.md
state: queued
kind: docs
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1886 added a minimum-sample-size floor (_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT = 2)
to the T-1620 proportional mass-invalidation check in
src/frob/gates/_fix_engine_sync.py (_mass_invalidation_rules): a rule with
exactly one live frob:waive directive can no longer trip the proportional
guard on its own (N=1 carries no proportional signal; mirrors the
_DEFLATION_MIN_KNOWN_MODULES precedent in frob.gates._coverage).

docs/modules/gates.md's T-1620 mass-invalidation writeup needs a short
addendum describing this floor -- could not be done as part of T-1886
itself because docs/modules/gates.md was under T-1877's live cross-worktree
scope lease at the time (ScopeLeaseConflict on `frob ticket scope T-1886
--add docs/modules/gates.md`). Add the doc update once T-1877's lease is
free, then `frob ack` the touched anchor.
