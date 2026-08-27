---
id: T-3101
title: Move native-rebuild sub-stage after land's publish, out of the pre-publish
  transaction
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_release.py
- src/frob/tickets/_land_squash.py
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
T-3095 (isolate land's post-squash file-mutating stages so the whole
transaction is invisible in the shared tree) chose NOT to fold the
native-rebuild sub-stage (_maybe_rebuild_natives, src/frob/tickets/
_land_release.py) into the out-of-tree transaction: it is a minutes-long
cargo/maturin build with no bearing on the correctness of the commit
being composed, and the concurrent-`git status --porcelain`-clean
acceptance criterion only needs to hold UNTIL the final publish -- not
after.

WANTED: move `_maybe_rebuild_natives`'s call out of the pre-publish
transaction and run it AFTER `publish_ref_cas` succeeds, against the now-
public root (which is genuinely fine to mutate at that point -- the
land is already durable). Confirm root truly stays clean for the whole
pre-publish span with this change in place (the T-3095 concurrent-poll
demonstration technique).

Depends on T-3089's re-scoped wiring (the out-of-tree pipeline needs to
exist end-to-end before this can be measured against a real land).
