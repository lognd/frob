## Done report

`frob ticket fail` records a `## Failure log` entry and returns the
ticket to QUEUED (no legal `queued -> done` edge in `_TRANSITIONS`), so
`_close_finalized_ticket`'s unconditional DONE-transition attempt always
refused with `InvalidTransition: queued -> done`, stranding the one
artifact a dead-end attempt produces on the worktree branch (the T-1478
incident this ticket cites).

Fix mirrors the T-1701 DROPPED precedent exactly: `_has_failure_log`
(`frob.tickets._land_merge`, the QUEUED-side twin of `_has_drop_reason`)
detects a genuine `frob ticket fail` record; `_skip_close_for_legitimate_
fail` (`frob.tickets._land_finalize`, folded together with the existing
drop-skip behind one `_skip_close_for_terminal_shortcut` call to keep
`_close_finalized_ticket` under ARCH001's 60-line threshold) publishes
that ledger state to main as-is instead of forcing the DONE transition.
`_validate_closeable` gained the matching QUEUED-with-failure-log
pre-merge branch so the preflight (before any git mutation) agrees with
the close-time behavior.

Gated on `_has_failure_log`, not merely `state == QUEUED`: a ticket that
is QUEUED for any OTHER reason (never started, `frob ticket requeue`
with no fail-log) still falls through to the ordinary DONE-precondition
path and refuses loudly if land is forced against it -- verified by
`test_queued_ticket_with_no_failure_log_still_refuses`.

Requirement 2 (name the remedy): substantially addressed by ELIMINATING
the `InvalidTransition` path for the legitimate case entirely -- an
honestly-failed ticket now lands cleanly with no refusal to explain. The
residual forced-land case (QUEUED, no failure log, evidence/Done-report
missing) already falls through to `_validate_closeable`'s existing
DONE-precondition error, which already names its own remedy ("record
evidence... add a '## Done report' section... retry `frob ticket land`
").

Requirement 3 (structured scope-mismatch data on `fail`) was NOT
attempted -- outside this ticket's declared scope
(`_land_finalize.py`/`_land_merge.py`, the land-side half only) and a
separate, larger change to `frob ticket fail`'s own write path and the
`doable` query; left for a follow-up if wanted.

### Changed
```
 tickets/T-1818/ticket.md | 38 +++++++++++++++++++++++++++++++++++++-
 1 file changed, 37 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandFailedTicket::test_failed_ticket_with_a_failure_log_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandFailedTicket::test_queued_ticket_with_no_failure_log_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 866 warning(s), 736 waived
- error-findings: none (measured, zero errors)
