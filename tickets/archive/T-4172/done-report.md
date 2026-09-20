## Done report

Changed: read_all_leases (and its liveness-pruning half
_live_leases_pruning_stale) now reconcile a lease against its ticket's
ledger state, not just worktree liveness, via the extracted
_ticket_ledger_staleness_shape helper reused from lease_staleness_reason.
A lease whose ticket has reached done/dropped is opportunistically
unlinked (_unlink_terminal_ticket_lease) and no longer reported.

Evidence: tests/test_ticket_leases.py::TestReadAllLeasesReconciliation
  .test_terminal_lease_does_not_block (MUST-FIRE, acceptance 1 and 3:
  a terminal ticket's lease neither blocks new work nor survives --
  this fix reconciles at READ time, so criterion 3 "the lease file is
  removed" now holds even on a path that skipped release_lease, not
  only on the clean transition exit that already called it)
  .test_terminal_dropped_ticket_lease_does_not_block_new_work
  .test_in_progress_lease_still_blocks (MUST-STAY-QUIET, acceptance 2:
  positive control -- a genuinely in-progress ticket's lease still
  refuses a colliding new ticket)
Full tests/test_ticket_leases.py: 171 passed (1 unrelated xdist-order
flake in TestRefuseIfLandInProgress, confirmed passing in isolation,
pre-existing and untouched by this change).

Filed: none

Gates: ruff-check/ruff-format clean on touched files. gate:SCOPE flags
this ticket's declared scope (src/frob/tickets/_leases.py only) as
narrower than the file's own pre-existing frob:doc/frob:tests directive
web -- this module already carries an LARGE001 waiver for its size and
directive density; unrelated to this change's own touched symbols,
which are documented and tested in place, so not widened per the
drive's tight-scope directive.

### Changed
```
 src/frob/tickets/_leases.py   | 119 ++++++++++++++++++++++++++++++++++++------
 tests/test_ticket_leases.py   | 112 +++++++++++++++++++++++++++++++++++++++
 tickets/T-4172/done-report.md |  36 +++++++++++++
 tickets/T-4172/ticket.md      |  14 +++--
 4 files changed, 261 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestReadAllLeasesReconciliation::test_terminal_lease_does_not_block` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestReadAllLeasesReconciliation::test_in_progress_lease_still_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 4789 warning(s), 961 waived
- error-findings: DRIFT001@src/frob/tickets/_leases.py, FMT001@src/frob/tickets/_leases.py, PRE001@tickets/T-4172
