---
id: T-1585
title: 'rapid profile: evidence/done-report leniency for docs/chore, REL001 off, baseline-thread-free
  land'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_tickets.py
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/**
  reason: verified all 3 described relaxations already implemented by T-1681/T-1705/T-1684;
    this ticket's own remaining work is regression coverage for item 1's backstop,
    narrowing to the one test file touched
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_tickets.py
  reason: verified all 3 described relaxations already implemented by T-1681/T-1705/T-1684;
    this ticket's own remaining work is regression coverage for item 1's backstop,
    narrowing to the one test file touched
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/tickets/**
  reason: narrow to the read-only-verified file plus the test file touched; no production
    code changed
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: narrow to the read-only-verified file plus the test file touched; no production
    code changed
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_missing_evidence_and_done_report_proceeds_with_debt_recorded
- tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_non_rapid_missing_evidence_and_done_report_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed while working T-1575: rapid profile's TEST016-skip and pre-commit-sweep-skip seams landed; three remaining rapid semantics from T-1575's body are still open: (1) evidence/done-report requirements light for kind=docs/chore, (2) REL001 off under rapid, (3) no baseline snapshot worktree at all -- today rapid still runs the T-1463 baseline thread because _land_cmd.py's post-land sweep reads the same result. Ledger integrity and LAND-PROOF stay non-negotiable in every profile.