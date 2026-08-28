---
id: T-3101
title: Move native-rebuild sub-stage after land's publish, out of the pre-publish
  transaction
state: dropped
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
land_commit: 4ba98f3b606604531ae6098bde97532938fa7aee
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

## Drop reason
- 2026-08-27: FALSE PREMISE, already delivered. Re-read src/frob/tickets/_land_compose.py
and _land_squash.py as they exist on main NOW (as briefed) before concluding
this: T-3111 (landed 7fad6e96c, BEFORE this ticket was filed) moved the
native-rebuild call out of _land_squash_apply_finish into a dedicated
_post_publish_native_rebuild, called AFTER _seal_squash_apply succeeds --
not hardcoded to the old in-root _commit_squash_apply. T-3089 (landed
1e9020107) and T-3121 (landed 53d06fb16, flip onto the disposable
worktree + CAS publish) then generalized _seal_squash_apply itself to
branch on squash_precomposed: True -> _publish_squash_apply (which calls
publish_ref_cas), False -> the legacy in-root _commit_squash_apply. Because
_post_publish_native_rebuild sits structurally AFTER that branch, not
inside either arm, the native rebuild already runs after publish_ref_cas
for every land that takes the default out-of-tree path (squash_precomposed
=True, set at both call sites in _land.py -- the disposable-worktree path
and the warm-stage path; the in-root False path only remains for a warm
sweep-stage-unavailable rapid-profile fallback). No ticket ever needed to
"re-point the call site" the way this ticket's own body predicted -- T-3121
generalized the seal step for an unrelated reason (CAS publish) and the
rebuild's position after it came along for free.

Verified, not inferred: tests/test_ticket_land.py::TestRebuildNatives (all
4 tests, including test_rebuild_runs_after_the_landing_commit_is_durable,
T-3111's own must-fire regression) pass on CURRENT main and in this
ticket's own fresh worktree, exercising land()'s real default path (which
this session's own T-3104/T-3131 lands moments ago also went through --
disposable-stage compose + CAS publish, confirmed by their own log output).

T-3163 (landed 31ecab73b, the ledger-splice regression this briefing named)
is orthogonal: it made ledger_lock(root) span the whole compose+publish
transaction for the disposed-stage path specifically (a concurrent-sibling-
write data-loss window between the two lock windows), and does not touch
_post_publish_native_rebuild's position at all -- confirmed by reading its
landed diff area; the rebuild still runs after _seal_squash_apply, after
the ledger_lock's own span, unchanged by T-3163.

No code change is needed for this ticket's stated WANT. Verified: no
frob:waive/frob:todo anywhere in _land_squash.py or _land_compose.py
defers this specific work, and grep of both files for "publish_ref_cas"/
"_maybe_rebuild_natives"/"_post_publish_native_rebuild" shows exactly the
call graph described above, not a stub or partial wiring.
