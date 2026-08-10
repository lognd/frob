## Done report

Added a fourth staleness shape, "ticket-terminal", to
`lease_staleness_reason` (src/frob/tickets/_leases.py): when the ticket
resolves in the ledger (queue or archive, `load_queue`) and its `state` is
`done` or `dropped`, the lease is reported stale regardless of TTL or live
worktree process -- unlike `"holder-dead"`, which infers deadness from
absence of evidence and stays gated on TTL+process, a terminal ticket's
state is a positive, authoritative signal from the ledger itself, so no
"give it more time" case applies. `in-progress`/`queued`/`planned`/
`blocked` tickets are untouched -- they still go through the unchanged
`"holder-dead"` TTL+process gate. `release_orphaned_lease` (the
`frob worktree release-lease` entrypoint) needed no changes -- it already
treats any non-None reason uniformly, so the new shape flows through for
free; only its docstring's "three shapes" count was corrected to four.

Repro technique used (playbook 7b): committed 6 new tests alone first
(6328fdd1a) against the still-unfixed guard, ran them, confirmed the 4
tests exercising the terminal-ticket shape (2 in TestLeaseStalenessReason,
2 in TestReleaseOrphanedLease) FAILED (assert None == 'ticket-terminal';
assert result.is_ok on an Err(LeaseWorktreeMismatch)) while the 2 tests
covering the still-live in-progress case already passed unchanged, then
committed the fix separately (36a21c384) and designated
TestLeaseStalenessReason::test_ticket_terminal_done as repro against
6328fdd1a -- `frob ticket evidence --check-repro` reports FAILED_AT_PARENT,
a genuine repro.

Verification: `pytest tests/test_ticket_leases.py::TestLeaseStalenessReason
tests/test_ticket_leases.py::TestReleaseOrphanedLease` -- 15 passed (was 9
before this ticket; 6 new tests added, all pass post-fix, 4 of the 6
genuinely repro pre-fix). A full-file run of tests/test_ticket_leases.py
hit a pytest-xdist INTERNALERROR (worker KeyError under this session's
heavy concurrent load, ~12+ simultaneous land processes) and separately
surfaced one unrelated pre-existing failure
(TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for,
failing because a real 'anchor' verb is not yet accounted for in that
test's own enumeration -- confirmed unrelated by running it in isolation,
same failure, nothing in this ticket's scope touches verb dispatch
tables).

Acceptance criterion 5 (report how many currently-held leases in this repo
belong to terminal tickets, denominator stated): measured via
scripts/fleet_status.py plus `frob ticket show` on every leased id, at
this session's live state. 13 leases held. 1 of 13 (T-2031, state
"dropped") is confirmed terminal -- the exact ticket this ticket's own
Problem section cites, still holding its lease in this same session. 9 of
13 belong to in-progress tickets (T-1686, T-1959, T-2003, T-2011, T-2016,
T-2024, T-2033, T-2041, T-2048 itself). 3 of 13 (T-draft-4aa27f0c,
T-draft-5e282a76, T-draft-ce9b8ee4) are local drafts that do not resolve
against this root's own ledger at all -- a different, already-known shape
(T-1806's "ticket-gone"), not "ticket-terminal", so they are excluded from
the terminal count rather than miscounted into it.

### Changed
```
 src/frob/tickets/_leases.py |  87 +++++++++++++++--------
 tests/test_ticket_leases.py | 164 ++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2048/ticket.md    |  55 ++++++++++++++-
 3 files changed, 275 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_dropped_ticket_lease_on_a_live_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_done_ticket_lease_on_a_live_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_an_in_progress_ticket_lease_on_a_live_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2048
