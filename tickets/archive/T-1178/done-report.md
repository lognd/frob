## Done report

Extended T-1130's commit_ticket_ledger_change auto-commit family (already
covering new/drop/fail, plus start's own T-1054 commit_start_transition) to
the remaining ledger-writing CLI verbs: close, evidence, done-report, and
requeue. This closes the T-0329 epic-close incident lineage documented in
the ticket body: a coordinator's close wrote tickets.md UNCOMMITTED (close
was outside T-1130's new/drop/fail set), a concurrent land preflight ran
git reset --hard in root, and the close silently vanished, caught only by a
doctor stale-lease scan.

Wiring, each with its own --no-commit opt-out (parity with new/drop/fail):

- frob.app.ticket_runner._close_cmd._close: commits LAST, after any
  --evidence/--evidence-cmd applied at close time plus the DONE transition
  -- "chore(tickets): close <id>".
- frob.app.ticket_runner._verify._evidence: commits the appended evidence
  id(s)/cmd-evidence entry -- "chore(tickets): record evidence for <id>".
- frob.app.ticket_runner._verify._done_report: commits the composed
  Done-report section -- "chore(tickets): <id> Done report".
- frob.app.ticket_runner._lifecycle._requeue: commits the QUEUED transition
  -- "chore(tickets): requeue <id>".

New CLI parser flags (src/frob/_cli_parsers/_ticket.py): --no-commit added
to close/evidence/done-report/requeue, reusing the existing shared
AppConfig.ticket_no_commit field (no new config plumbing needed).

Every ledger-writing verb dispatched through the CLI now auto-commits by
default: new/start/drop/fail/close/evidence/done-report/requeue. Direct
frob.tickets library calls bypassing the CLI are unaffected, same as
before.

docs/modules/tickets.md's "New/drop/fail auto-commit (T-1130)" section
gained a T-1178 subsection documenting the extension and per-verb commit
messages; design/frob.strata synced (SYS104) for the new test class.

### Changed
```
 tickets.md | 53 ++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 50 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_auto_commits` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_no_commit_leaves_ledger_dirty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_done_report_auto_commits` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_close_auto_commits` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_requeue_auto_commits` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_requeue_no_commit_leaves_ledger_dirty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 958 warning(s), 573 waived
- error-findings: none (measured, zero errors)
