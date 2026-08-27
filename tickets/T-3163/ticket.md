---
id: T-3163
title: 'T-1036 ledger-splice regression under T-3121 disposable-stage: concurrent
  sibling write can silently drop the just-landed ticket''s own record'
state: in-progress
kind: bug
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
- src/frob/tickets/_land_compose.py
- docs/modules/tickets-landing.md
- tests/unit/test_land_compose.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: T-3163 root cause spans _land_compose.py's CAS-publish/resync sequence and
    _leases.py's commit_ticket_ledger_change -- the concurrent sibling write races
    the land window at the git-commit layer, not inside _land_squash.py's own splice;
    confirmed by repro before widening
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/tickets/_land_compose.py
  reason: T-3163 root cause spans _land_compose.py's CAS-publish/resync sequence and
    _leases.py's commit_ticket_ledger_change -- the concurrent sibling write races
    the land window at the git-commit layer, not inside _land_squash.py's own splice;
    confirmed by repro before widening
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-3163: scope-closure warning -- widened files carry frob:doc targets in
    this doc; add it so the doc-edge check is satisfied rather than waived'
  actor: logan
  at: '2026-08-27'
- op: remove
  glob: src/frob/tickets/_leases.py
  reason: 'T-3163: root cause and fix both live entirely in _land_compose.py (ledger_lock
    now spans the whole compose-through-resync window) and _land_squash.py; _leases.py''s
    commit_ticket_ledger_change needed no change once the lock is held earlier --
    releasing the unused lease'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_land_compose.py
  reason: 'T-3163: the ledger_lock fix in compose_squash_in_disposable_worktree creates
    .frob/tickets.lock as a side effect; this module''s scratch_repo/conflicting_repo
    fixtures never gitignore .frob/ (T-1393''s own established pattern elsewhere in
    this test suite), so 2 must-stay-quiet porcelain-equality tests regress -- fixing
    the fixtures, not the production lock scope'
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: append
  reason: 'T-3163: BUG002 flagged the confirmatory-only evidence bound at close; documenting
    why the real repro (which does fail at parent) cannot be bound, per BUG002''s
    own remedy (3)'
  actor: logan
  at: '2026-08-27'
  old_length: 2723
  new_length: 4314
evidence:
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_clean_squash_reports_no_conflicts
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_conflicting_squash_reports_the_conflicted_paths
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_clean_squash
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_conflicted_squash
- tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_folded_commit_contains_both_sides
- tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_fold_refuses_while_paths_are_unmerged
- tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_racing_publish_surfaces_dirtymain
- tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_blocked_resync_is_not_a_land_failure
- tests/unit/test_land_stage_flip.py::TestPublishSquashApply::test_clean_publish_advances_root_and_resyncs
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27, while fixing T-3144's stale test-infra (tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land).

That test's own monkeypatch was stale (patched _land_squash_mod.run_argv,
but T-3121's disposable-stage flip moved the actual `git merge --squash`
call into _land_compose's own module-level run_argv, called directly
from _land.py -- the old patch target never fired the test's injection
hook at all). After retargeting the patch to _land_compose_mod.run_argv
(the genuinely correct call site) and fixing a second, related test-infra
gap (the forked child inherits the parent test process's os.environ,
which by fork time already carries FROB_WORKTREE set by land()'s own
in-process evidence re-verify -- popped in the child to mirror a real
independent process), the test's land() call itself now succeeds
(result.is_ok), but the FINAL ledger on root after land contains ONLY
the concurrent sibling's own new ticket -- the just-landed ticket's OWN
record (finalized as result.danger_ok.final_id) is completely absent
from load_all(repo).danger_ok, not merely stale.

This is exactly the class of defect T-1036 was filed to prevent (a
concurrent single-ticket write racing the land window must never silently
clobber ledger content), just manifesting as the INVERSE of the original
symptom: instead of the concurrent write being discarded, the just-landed
ticket's own entry is discarded and the concurrent write survives alone.

REPRO: fix the test's monkeypatch target as described above and run
tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
-- landed.danger_ok contains only the sibling id, result.danger_ok.final_id
(the original ticket) raises KeyError.

HYPOTHESIS (unconfirmed, needs investigation): the concurrent sibling's own
new_ticket() call, once it acquires the ticket ledger lock after land()
releases it, may read/merge against a STALE in-memory or on-disk base
snapshot of root's tickets.md that predates the squash-fold's CAS
publish, then writes back a REPLACEMENT tickets.md rather than an
appending merge -- losing the freshly-published squash content. This
needs tracing through new_ticket's own ledger-write path and/or the
splice/fold pipeline (_squash_and_splice_ledger_v2 under
merge_already_composed=True) to confirm.

NOT fixed by T-3144: T-3144's scope is tests/test_ticket_land.py only, and
this is a genuine production correctness bug (silent ledger data loss)
requiring its own investigation and fix in src/frob/tickets/_land_squash.py
and/or wherever new_ticket's ledger merge lives -- out of proportion for a
test-file ticket to absorb.

frob:waive BUG002 reason="the genuine designated repro (tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land, retargeted by T-3144's in-flight test-infra fix) DOES fail at the parent commit (110990225eae4796c4763f7f1e6ceb5cb4c3bb83) and reproduces the exact defect (confirmed directly, --runxfail, before any production change) -- but it cannot currently be bound as evidence because it ALSO fails against the fix, for an unrelated, newly-exposed test-construction artifact: its own T-2114 concurrent-writer simulation forks the sibling process, and once ledger_lock is genuinely held across most of the injected-hook window (required for the fix to be correct), the forked child inherits the parent's already-acquired flock fd plus _lock_local's thread-local reentrancy bookkeeping, so it spuriously skips real lock contention instead of blocking like a genuinely independent process would. Filed as T-draft-075f47f9 (blocked_by T-3144, same file's write lease -- cannot fix it here without colliding with T-3144's in-progress lease on tests/test_ticket_land.py). Verified the FIX itself is correct with a standalone script (multiprocessing.get_context('spawn'), immune to the fork artifact) reproducing the identical scenario against the fixed code: land() succeeds, resync succeeds cleanly, the sibling correctly blocks until land finishes, reads the freshly-published ledger, and both tickets survive -- PASS. This is the ledger/test-infra-blocked case BUG002's own remedy (3) describes, not a fix without a real repro."