---
id: T-1979
title: 'Post-land floor regression from T-1946/T-1944: ARCH001 x2, COV001, TEST001'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_scope.py
- docs/modules/tickets.md
evidence_scope:
- tests/unit/test_land_orphaned_evidence.py
- tests/unit/test_tickets_evidence_only_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: T-1944's doc section, deferred at land time, is added here as part of fixing
    the COV001 finding for demote_to_evidence_only's frob:doc anchor
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test
- tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Immediately post-land measurement of `frob check --only gates` after
landing T-1946 and T-1944 found the unscoped floor at 5, not the
expected 0. Of those 5, 4 trace directly to this session's own two
lands (the 5th, DOCENUM001 SYS110, traces to T-1629's unrelated land and
is already tracked by T-1974):

  ARCH001  src/frob/tickets/_land.py::_check_orphaned_evidence_deletion
           (97 lines, threshold 60)
  ARCH001  src/frob/tickets/_scope.py::demote_to_evidence_only
           (84 lines, threshold 60)
  COV001   src/frob/tickets/_scope.py::demote_to_evidence_only
           is public with no frob:doc edge
  TEST001  src/frob/tickets/_scope.py::demote_to_evidence_only
           is public with no frob:tests directive bound (tests exist,
           the directive binding them was never added)

Fix: split both functions under the ARCH001 threshold, add a frob:doc
anchor for demote_to_evidence_only (docs/modules/tickets.md's existing
"Evidence-only scope (T-1944)" section, itself still pending its own
follow-up T-1973/T-1975 due to a lease conflict at the time), and add
the missing frob:tests directive binding its existing test coverage in
tests/unit/test_tickets_evidence_only_scope.py.