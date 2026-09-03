---
id: T-3635
title: 'post-land sweep regression from T-3591: 17 new (rule, file) identit(ies),
  827 finding(s) (DOC006, DRIFT002, F401, SEC110)'
state: done
kind: bug
origin: agent
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land.py
- tests/ticket_land_suite/test_archive.py
- tests/ticket_land_suite/test_claim_close.py
- tests/ticket_land_suite/test_dirt_ownership.py
- tests/ticket_land_suite/test_land_core.py
- tests/ticket_land_suite/test_land_lock.py
- tests/ticket_land_suite/test_land_plan.py
- tests/ticket_land_suite/test_ledger_splice.py
- tests/ticket_land_suite/test_push.py
- tests/ticket_land_suite/test_release.py
- tests/ticket_land_suite/test_verify_intent.py
- tests/ticket_land_suite/test_verify_reset.py
- tests/ticket_land_suite/test_waive_deletion.py
- tests/ticket_land_suite/test_wip.py
- tickets/T-3628/ticket.md
- tickets/T-3629/ticket.md
findings:
- - DOC006
  - tickets/T-3628/ticket.md
- - DOC006
  - tickets/T-3629/ticket.md
- - DRIFT002
  - tests/ticket_land_suite/test_archive.py
- - DRIFT002
  - tests/ticket_land_suite/test_claim_close.py
- - DRIFT002
  - tests/ticket_land_suite/test_dirt_ownership.py
- - DRIFT002
  - tests/ticket_land_suite/test_land_core.py
- - DRIFT002
  - tests/ticket_land_suite/test_land_lock.py
- - DRIFT002
  - tests/ticket_land_suite/test_land_plan.py
- - DRIFT002
  - tests/ticket_land_suite/test_ledger_splice.py
- - DRIFT002
  - tests/ticket_land_suite/test_push.py
- - DRIFT002
  - tests/ticket_land_suite/test_release.py
- - DRIFT002
  - tests/ticket_land_suite/test_verify_intent.py
- - DRIFT002
  - tests/ticket_land_suite/test_verify_reset.py
- - DRIFT002
  - tests/ticket_land_suite/test_waive_deletion.py
- - DRIFT002
  - tests/ticket_land_suite/test_wip.py
- - F401
  - /home/logan/projects/frob/tests/test_ticket_land.py
- - SEC110
  - tests/ticket_land_suite/test_wip.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 no-behavior-change for a doc/import-hygiene fix
  actor: logan
  at: '2026-09-01'
  old_length: 5337
  new_length: 5646
evidence:
- tests/ticket_land_suite/test_archive.py::TestArchiveV2::test_v2_draft_survives_a_concurrent_worktree_restore
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3591 at commit a719e2602dab54f7a8c3884bc98fc66873ae39bf found 17 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (17), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 827 actual finding(s) across those 17 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-3628/ticket.md
- DOC006  tickets/T-3629/ticket.md
- DRIFT002  tests/ticket_land_suite/test_archive.py
- DRIFT002  tests/ticket_land_suite/test_claim_close.py
- DRIFT002  tests/ticket_land_suite/test_dirt_ownership.py
- DRIFT002  tests/ticket_land_suite/test_land_core.py
- DRIFT002  tests/ticket_land_suite/test_land_lock.py
- DRIFT002  tests/ticket_land_suite/test_land_plan.py
- DRIFT002  tests/ticket_land_suite/test_ledger_splice.py
- DRIFT002  tests/ticket_land_suite/test_push.py
- DRIFT002  tests/ticket_land_suite/test_release.py
- DRIFT002  tests/ticket_land_suite/test_verify_intent.py
- DRIFT002  tests/ticket_land_suite/test_verify_reset.py
- DRIFT002  tests/ticket_land_suite/test_waive_deletion.py
- DRIFT002  tests/ticket_land_suite/test_wip.py
- F401  /home/logan/projects/frob/tests/test_ticket_land.py
- SEC110  tests/ticket_land_suite/test_wip.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-3628/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-3629/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  tests/ticket_land_suite/test_archive.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_archive.py::TestArchiveResurrection
- DRIFT002  tests/ticket_land_suite/test_claim_close.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder
- DRIFT002  tests/ticket_land_suite/test_dirt_ownership.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_dirt_ownership.py::TestDescribeRootDirtNamesStagedState
- DRIFT002  tests/ticket_land_suite/test_land_core.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_land_core.py::TestCloseFailAfterMerge
- DRIFT002  tests/ticket_land_suite/test_land_lock.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout
- DRIFT002  tests/ticket_land_suite/test_land_plan.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_land_plan.py::TestLandPlan
- DRIFT002  tests/ticket_land_suite/test_ledger_splice.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_ledger_splice.py::TestCarryForwardOrRefuseSiblingEdits
- DRIFT002  tests/ticket_land_suite/test_push.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_push.py::TestLandPushCliWiring
- DRIFT002  tests/ticket_land_suite/test_release.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_release.py::TestLandReleaseMonotonicityHelpers
- DRIFT002  tests/ticket_land_suite/test_verify_intent.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_verify_intent.py::TestPrintLandProofSurfacesBudgetDeferred
- DRIFT002  tests/ticket_land_suite/test_verify_reset.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_verify_reset.py::TestCommitSquashApplyUnwindsOnCommitFailure
- DRIFT002  tests/ticket_land_suite/test_waive_deletion.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_waive_deletion.py::TestCommittedWaiveDeletionRefusal
- DRIFT002  tests/ticket_land_suite/test_wip.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_wip.py::TestWipAddIgnoredPathFallback
- F401  /home/logan/projects/frob/tests/test_ticket_land.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  tests/ticket_land_suite/test_wip.py  -> attributed to T-3591 (commit a719e2602dab, already closed/dropped -- filed below) via tests/ticket_land_suite/test_wip.py::TestWipAddIgnoredPathFallback

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="pure metadata/import-hygiene fix: repoints self-referential frob:tests directives to their post-split file, prunes a now-unused import block, and waives 2 pre-existing future-facing DOC006 findings in another ticket's planning text -- no gate logic or test behavior changes."