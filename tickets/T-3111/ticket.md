---
id: T-3111
title: Move land's native rebuild after the landing commit, out of the dirty-root
  window
state: done
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
- src/frob/tickets/_land_squash.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_land.py::TestRebuildNatives::test_rebuild_runs_after_the_landing_commit_is_durable
- tests/test_ticket_land.py::TestRebuildNatives::test_invoked_when_native_source_touched
- tests/test_ticket_land.py::TestRebuildNatives::test_skipped_when_no_native_source_touched
- tests/test_ticket_land.py::TestRebuildNatives::test_rebuild_failure_does_not_block_land
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7fad6e96c0ee509b23e0e6bd5147f298fb72864b
---
T-3101 asks for the native rebuild to move AFTER `publish_ref_cas`. That
call site does not exist yet and is blocked behind T-3089's re-scoped
wiring (see T-3089's RE-SCOPE NOTICE and T-3107). But T-3101's actual WANT
-- a minutes-long cargo/maturin build must not run inside the window where
root's shared working tree is staged-but-uncommitted -- is satisfiable
TODAY, against the in-root architecture, and the fix survives T-3089's
rewrite unchanged.

TODAY'S DEFECT: `_land_squash_apply_finish`
(src/frob/tickets/_land_squash.py) calls `_warn_if_native_stale` +
`_maybe_rebuild_natives` BETWEEN `_assert_land_complete` and
`_commit_squash_apply`. At that moment root holds the entire squashed
changeset staged with nothing committed. Every second the rebuild takes is
a second a sibling `frob ticket land` sees DirtyMain, `frob ticket new`
refuses with LandInProgress, and an unrelated agent cannot start work. A
measured land of an ordinary ticket showed a ~1.5s dirty window; a land
that touches frob-core/strata-core puts a full native build inside that
same window.

WANTED: move both calls to AFTER `_commit_squash_apply` succeeds. The
rebuild's output is gitignored build artifacts, never commit content
(`_maybe_rebuild_natives` is already documented best-effort and already
never unwinds), so nothing about the landing commit's content changes --
only when the build runs relative to it.

POST-PUBLISH FAILURE SEMANTICS (the design question, answered): if the
rebuild fails after the commit is durable, the land MUST report the
failure loudly and MUST NOT unwind. The commit is already public and a
sibling may already have stacked on it; reverting it is the
"reset --hard a real commit" hazard T-1456/T-1740 exist to prevent, and
it would be traded for a strictly smaller problem -- a stale local `.so`,
which `_warn_if_native_stale`/NATIVE001 already detect and a local
`frob natives build` already fixes. `LandReport.natives_rebuilt` stays
`False` and the existing warning stands. This is the same posture the
code already takes; moving the call must not change it.

ACCEPTANCE
- must-fire: a land whose changeset touches a native source tree invokes
  the callback only once root's HEAD is ALREADY the landing commit and
  root is clean -- i.e. the callback observes a durable, committed root.
- must-stay-quiet: the three existing `TestRebuildNatives` fixtures
  (invoked-when-native-touched, skipped-when-not, failure-does-not-block)
  pass with zero edits to their assertions.