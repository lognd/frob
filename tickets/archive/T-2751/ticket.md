---
id: T-2751
title: close draft-promotion scan (T-2738) attempts already-terminal DROPPED drafts,
  spurious failure
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- tests/unit/test_close_promote_drafts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002: test+fix committed together, cannot retroactively split cheaply'
  actor: logan
  at: '2026-08-20'
  old_length: 1345
  new_length: 1707
evidence:
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_ignores_an_already_dropped_draft
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1fd6743e4eb77f6aae10eb9f23d2cbd0bd6db26f
---
## Description

`_promote_pending_drafts_after_close` (T-2738) used `load_queue`, which
returns the merged active+archive view -- so an already-terminal
(DROPPED) draft-id ticket, e.g. a stale draft from a past land that was
deliberately dropped as dead residue and left sitting under its own
never-finalized draft id, is visible to the scan and gets attempted for
promotion even though it is not "pending" work related to the ticket
being closed at all.

Reproduced LIVE while closing T-2737 directly in this same series: the
close correctly transitioned T-2737 to done, but the promote pass then
tried to finalize an unrelated, long-dropped draft `T-draft-d718d443`
(referenced in T-1920's own prose as "subsequently dropped") and failed
loudly (`NotFound`), exiting nonzero and leaving debris in the working
tree (a half-finished archive rename) even though T-2737's own close
was already correctly committed.

## Fix

Filter the draft scan to non-terminal states only (exclude DONE/DROPPED)
before attempting `finalize_draft` on any of them -- a terminal draft is
not pending work this close could be stranding.

## Positive control

A DROPPED draft-id ticket sitting in the archive is left completely
untouched by a close that has nothing to do with it; a genuinely pending
(non-terminal) draft is still promoted exactly as T-2738 designed.

frob:waive BUG002 reason="fix committed together with its own new regression test (test_close_ignores_an_already_dropped_draft), so no ref in this worktree ever has the test failing without the fix already applied; the defect was reproduced LIVE during T-2737 close (see ticket body) and the test genuinely exercises the fixed filter, not merely confirmatory"