---
id: T-2274
title: Land bookkeeping commit (T-2256's 'record land commit') absorbed an unrelated
  bystander's dirty _land.py edit -- 32-line stranger diff, zero ticket/evidence trail
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land.py
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
designated_repro_test: tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
acceptance:
- text: The land-time step that produces a 'record land commit'/bookkeeping commit
    is identified and, if it stages more than its own owned paths, narrowed to stage
    only those
  evidence:
  - tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
- text: A regression test seeds an unrelated dirty tracked file in the shared root
    before the bookkeeping-commit step and asserts the resulting commit never contains
    it
  evidence:
  - tests/test_ticket_land.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d08758024e749f47b80131abbf83a9c4afbb6972
---
MEASURED (2026-08-17, during T-2255): editing `src/frob/tickets/_land.py`
directly in the shared primary checkout (`/home/logan/projects/frob`,
against the playbook's own standing rule -- confirmed as my own mistake,
not filed to excuse it) produced an unexpected result: the edit did not
sit as a dirty working-tree file. `git status`/`git diff` reported the
tree CLEAN throughout, yet the file's on-disk content kept the edit.

Tracing it: commit `9a7bf279657b8b15543079f6a11a0d4abb7aeb98`
("chore(tickets): record land commit for T-2256") -- which by its own
message should be a pure ledger-bookkeeping commit recording T-2256's
land SHA -- actually contains a 32-line diff to `src/frob/tickets/
_land.py` that has nothing to do with T-2256. Confirmed via `git show
--stat`: exactly 2 files changed, `src/frob/tickets/_land.py` (+32) and
`tickets/T-2256/ticket.md` (+2/-1). The `_land.py` hunk is an
IN-PROGRESS, PARTIAL edit -- it references `_OrphanEvidenceCheckOutcome`
and `_LAST_ORPHAN_EVIDENCE_OUTCOME` at their use sites but never defines
either, which is a `NameError` waiting to happen the moment that code
path executes (T-2255's own orphaned-evidence check, exercised on every
real land).

Best working theory (not fully isolated -- filing so it doesn't get
lost, not claiming a proven root cause): T-2256's own concurrent `frob
ticket land` process, at its "record land commit" bookkeeping step, did
something equivalent to `git add -A && git commit` (or an internal
squash step that stages the FULL working tree rather than a specific
tracked diff) against the SAME shared checkout a dirty, unrelated edit
was sitting in at that moment -- scooping the stranger's uncommitted
change into its own commit. If so, this is a second, distinct incident
from the family already on record (`agents-edit-the-shared-root`,
`coordinator-never-dirties-root`): those describe a dirty root BLOCKING
a land (DirtyMain); this one describes a dirty root being SILENTLY
ABSORBED into an unrelated ticket's commit instead.

## Consequence
Main's history briefly carried broken code (a guaranteed `NameError` in
`_check_orphaned_evidence_deletion` on any land that reaches its
`_LAST_ORPHAN_EVIDENCE_OUTCOME` write) attributed to a bookkeeping commit
with zero ticket/evidence/test trail -- not because T-2256 introduced it,
but because a bystander's mid-edit dirty file was standing in the shared
root at the wrong moment. T-2255 repairs the actual code (adds the
missing definitions, now correct and tested) as part of its own land, so
main will not carry the broken half-state once T-2255 lands. This ticket
is about the MECHANISM, not the repaired symptom.

## Do NOT
- Do not rewrite `9a7bf279657b8b15543079f6a11a0d4abb7aeb98` or any commit
  after it -- many other worktrees/commits already build on that history;
  a rewrite here is a bigger hazard than the (now-repaired) content bug.

## Acceptance
1. Identify the actual land-time step that produced this (or confirm/
   refute the `git add -A`-at-bookkeeping-commit theory with the real
   code path in `frob.tickets._land`/`_land_squash`/`_land_finalize`).
2. Whatever writes a "record land commit" / similar bookkeeping commit
   during `frob ticket land` stages ONLY the paths that commit's own
   purpose owns (the ticket ledger / land-record file), never `git add
   -A` or an equivalent full-tree stage, so a bystander's unrelated dirty
   file in the shared root can never ride along.
3. A regression test: seed an unrelated dirty tracked file in the shared
   root before running the bookkeeping-commit step under test; assert
   the resulting commit's diff touches only the paths that step owns.