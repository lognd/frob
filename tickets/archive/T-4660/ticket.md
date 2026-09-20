---
id: T-4660
title: post-publish never holds .frob/derived.lock across a full check
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4654
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_post_publish_lock_window.py
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_post_publish_lock_window.py::test_post_publish_never_holds_derived_lock_across_a_check
- tests/unit/test_post_publish_lock_window.py::test_next_land_not_blocked_by_previous_sweep
- tests/unit/test_post_publish_lock_window.py::TestSnapshotWorktree::test_yields_a_detached_checkout_of_the_commit
designated_repro_test: null
acceptance:
- text: Given a land that has just published, when post-publish runs, then no single
    .frob/derived.lock hold exceeds a bounded ceiling and no hold spans a full check
    invocation.
  evidence:
  - tests/unit/test_post_publish_lock_window.py::test_post_publish_never_holds_derived_lock_across_a_check
- text: 'POSITIVE CONTROL: tests/unit/test_post_publish_lock_window.py::test_post_publish_never_holds_derived_lock_across_a_check
    instruments the lock and asserts that the set of operations performed under any
    one hold excludes a check run, and that the longest hold is under the declared
    ceiling. It FAILS on dev today (a single hold spans the whole check) and passes
    after this leaf.'
  evidence:
  - tests/unit/test_post_publish_lock_window.py::test_post_publish_never_holds_derived_lock_across_a_check
- text: Given post-publish completes, when the next land starts, then it acquires
    derived.lock without waiting on the previous land's sweep; tests/unit/test_post_publish_lock_window.py::test_next_land_not_blocked_by_previous_sweep
    proves it.
  evidence:
  - tests/unit/test_post_publish_lock_window.py::test_next_land_not_blocked_by_previous_sweep
- text: docs/modules/tickets-verify-sweep.md documents the bounded-hold rule and the
    ceiling, and is updated in this same change.
  evidence:
  - tests/unit/test_post_publish_lock_window.py::TestSnapshotWorktree::test_yields_a_detached_checkout_of_the_commit
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Kernel decoupling leaf (LAND story). ~3 points. Sibling of T-4634 (which removes the snapshot rebuild); this leaf removes the LOCK HOLD.

Measured this week: after a land publishes its commit, the post-publish sweep holds .frob/derived.lock READ for up to 30 minutes while it runs a full check. The serial land queue is the fleet's bottleneck, so every one of those minutes idles the next land.

Make post-publish a bounded phase in src/frob/app/ticket_runner/_rapid_sweep.py: it may acquire derived.lock only for the short, bounded writes it actually needs, never across a full `frob check`. Anything expensive is handed to the async sweep, which acquires its own lock independently. Log each acquire and release with the phase name and the hold duration.