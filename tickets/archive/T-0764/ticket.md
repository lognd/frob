---
id: T-0764
title: 'friction: archive/concurrent-ledger-rewrite silently reverts in-flight tickets
  start+evidence+acceptance (recovered T-0753 by hand)'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: high
parent: T-0577
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets*.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-0764 also needs regression tests in tests/test_ticket_land.py for splice_ledger
    richness/id-drop guards; test_tickets*.py glob doesn't match this filename
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_force_overrides_the_live_lease_refusal
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_stale_lease_from_a_removed_worktree
- tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie
- tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_a_side_only_id_missing_from_theirs_survives_the_splice
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_malformed_side_is_refused_not_silently_treated_as_empty
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused
designated_repro_test: null
acceptance:
- text: GIVEN a live non-stale lease WHEN frob ticket archive runs THEN it refuses
    without --force; GIVEN an in-flight ticket WHEN main ledger is rewritten under
    it THEN its start/evidence/acceptance survive the finalize
  evidence:
  - tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists
  - tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie::test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie
threat: null
component: null
---
Coordinator friction 2026-07-22: frob ticket archive (and any concurrent land that rewrites main tickets.md) causes in-flight worktree tickets to LOSE their start/evidence/acceptance-binding when the worktree next runs the 10b restore (git checkout main -- tickets.md picks up the archived/rewritten ledger where the in-flight ticket is back to queued with empty evidence). Recovered T-0753 by hand (re-start, re-record 6 evidence ids, re-bind acceptance). Fixes: (1) archive should REFUSE (or warn-and-require --force) when live non-stale leases exist -- archiving during in-flight work is the hazard; the TICK003 remediation text already says run in a quiet window, make it enforced. (2) the 10b restore recipe is fragile against a rewritten-ledger main; the real fix is the single-writer done-report/evidence path never needing a full restore -- coordinate with T-0577/T-0637 land machinery so an agent NEVER git-checkout-main-tickets.md (the land --path replay the coordinator already does is the safe pattern).