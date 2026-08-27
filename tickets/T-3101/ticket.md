---
id: T-3101
title: Move native-rebuild sub-stage after land's publish, out of the pre-publish
  transaction
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
blocked_by:
- T-3089
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
body_changes:
- mode: append
  reason: 'series BM: record the answer to this ticket''s post-publish-failure design
    question and point at T-3111, which delivers the same WANT against today''s in-root
    architecture'
  actor: logan
  at: '2026-08-27'
  old_length: 1009
  new_length: 2191
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


SERIES BM NOTE (2026-08-27). This ticket is blocked on T-3089, whose plan
was found under-scoped and rewritten (see its RE-SCOPE NOTICE); T-3089 is
in turn blocked on T-3107, which landed the missing primitive.

The design question this ticket poses -- what happens if the rebuild fails
AFTER a successful publish -- is answered in T-3111's body: report loudly,
never unwind. The commit is public and a sibling may already have stacked
on it, so reverting it is the "reset --hard a real commit" hazard
T-1456/T-1740 exist to prevent, traded for a strictly smaller problem (a
stale local .so, already covered by `_warn_if_native_stale`/NATIVE001 and
fixed by a local `frob natives build`).

T-3111 delivers this ticket's WANT against TODAY's in-root architecture:
the rebuild currently sits between `_assert_land_complete` and
`_commit_squash_apply`, i.e. squarely inside the staged-but-uncommitted
window, and moving it after the commit is a strict improvement that needs
no out-of-tree pipeline and survives T-3089's rewrite unchanged. When
T-3089 lands, what remains here is only re-pointing that same call site
from "after `_commit_squash_apply`" to "after `publish_ref_cas`".
