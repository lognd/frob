---
id: T-1178
title: 'tickets: complete the auto-commit family -- close/done-report/evidence/requeue
  transitions commit like start/new/drop/fail'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_leases.py
- src/frob/app/ticket_runner/**
- src/frob/_cli_parsers/_ticket.py
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/**
  reason: close/evidence/done-report/requeue auto-commit wiring lives in the CLI runner
    + parser, needs tests/test_ticket_leases.py + docs/design sync
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: close/evidence/done-report/requeue auto-commit wiring lives in the CLI runner
    + parser, needs tests/test_ticket_leases.py + docs/design sync
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_leases.py
  reason: close/evidence/done-report/requeue auto-commit wiring lives in the CLI runner
    + parser, needs tests/test_ticket_leases.py + docs/design sync
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: close/evidence/done-report/requeue auto-commit wiring lives in the CLI runner
    + parser, needs tests/test_ticket_leases.py + docs/design sync
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: close/evidence/done-report/requeue auto-commit wiring lives in the CLI runner
    + parser, needs tests/test_ticket_leases.py + docs/design sync
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_auto_commits
- tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_no_commit_leaves_ledger_dirty
- tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_done_report_auto_commits
- tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_close_auto_commits
- tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_requeue_auto_commits
- tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_requeue_no_commit_leaves_ledger_dirty
designated_repro_test: null
acceptance:
- text: GIVEN any ledger-writing ticket verb run on main WHEN it completes THEN its
    transition is committed automatically (T-1130's commit_ticket_ledger_change, --no-commit
    opt-out), so no concurrent land preflight reset can ever discard a completed verb's
    write
  evidence:
  - tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_auto_commits
  - tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_no_commit_leaves_ledger_dirty
  - tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_done_report_auto_commits
  - tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_close_auto_commits
  - tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_requeue_auto_commits
  - tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_requeue_no_commit_leaves_ledger_dirty
threat: null
component: null
---
REFILE: the original filing (commit 46a115c4, first allocated id clobbered by a concurrent land's renumber -- see the sibling id-allocation bug ticket) recorded the 2026-07-29 incident: the coordinator's T-0329 epic close wrote the ledger uncommitted (close is not in T-1130's new/drop/fail set), a concurrent agent land preflight ran git reset --hard in root, and the close silently vanished -- caught only by T-1131's doctor stale-lease scan. Extend commit_ticket_ledger_change to every remaining ledger-writing verb: close, done-report, evidence add, requeue, and any mutation verbs still uncommitted. Closes the reset-eats-uncommitted-coordinator-work class (T-0948 lineage) at the verb layer.