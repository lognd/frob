## Done report

The sweep already computed both halves of the diff (fresh vs baseline)
but only ever used one direction (new_findings = fresh - baseline). This
adds the mirror: vanished = baseline - fresh, and a
_close_resolved_sweep_tickets pass that auto-DROPS (never closes -- no
work was done, no evidence exists) every QUEUED/PLANNED sweep-filed
ticket whose full recorded (rule, file) identity set is a subset of
vanished. IN_PROGRESS tickets are never touched. A partially-resolved
ticket (some but not all identities vanished) is left alone entirely --
no partial drop, matching the acceptance bar that a false drop is worse
than a stale ticket.

_parse_sweep_ticket_identities recovers the exact identity set
_file_regression_ticket already writes into the ticket body (scanning
from the same heading, now a shared constant _REGRESSION_IDENTITY_HEADING,
and stopping before the attribution section which reuses the same "-
rule  file" shape for a different purpose) rather than re-deriving a
second notion of what the ticket is about.

Wired into run_deferred_post_land_sweep unconditionally (runs whether
this sweep is itself clean or red -- a resolved regression and a new one
are independent outcomes of the same measurement), right after the
existing new_findings computation.

### Changed
```
 tickets/T-1983/done-report.md | 42 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1983/ticket.md      | 20 ++++++++++++++++++--
 2 files changed, 60 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions::test_resolved_finding_is_dropped_by_the_next_sweep` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions::test_still_reproducing_finding_is_left_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_drops_a_fully_resolved_sweep_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_leaves_a_partially_resolved_ticket_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_in_progress_sweep_ticket_is_never_touched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/queue-hygiene/tests/unit/test_tickets_evidence_only_scope.py
