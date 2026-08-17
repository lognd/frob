---
id: T-2048
title: frob worktree release-lease cannot reclaim a lease held by a terminal (dropped/done)
  ticket -- staleness check never asks whether the holder is finished
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
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrow to the staleness-reason guard and its unit tests
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_ticket_leases.py
  reason: narrow to the staleness-reason guard and its unit tests
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_dropped_ticket_lease_on_a_live_worktree
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_done_ticket_lease_on_a_live_worktree
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_an_in_progress_ticket_lease_on_a_live_worktree
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done
designated_repro_test: tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done
acceptance:
- text: A test where a dropped ticket holds a lease on a LIVE worktree, and release-lease
    succeeds and releases it. This test must fail before the fix.
  evidence:
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_dropped_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_done_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_an_in_progress_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done
- text: The same for a done ticket.
  evidence:
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_dropped_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_done_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_an_in_progress_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done
- text: A test that a lease held by an in-progress ticket on a live worktree is still
    refused -- the existing protection must not weaken.
  evidence:
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_dropped_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_done_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_an_in_progress_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done
- text: A new distinct staleness reason (ticket-terminal) surfaced in the log line,
    so the reclaim is attributable rather than indistinguishable from holder-dead.
  evidence:
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_dropped_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_done_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_an_in_progress_ticket_lease_on_a_live_worktree
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done
- text: Report how many currently-held leases in this repo belong to terminal tickets.
    Use scripts/fleet_status.py plus each ticket's state; state the denominator.
  evidence:
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_terminal_done
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

`frob worktree release-lease` refuses to reclaim a lease held by a TERMINAL
ticket (`dropped` / `done`). Its staleness check asks three questions --
does the worktree path exist, is the ticket in the ledger, does a process
hold it -- and never asks whether the ticket is in a state that is allowed
to hold a lease at all. A dropped ticket is in the ledger, so the check
reports "still live" and refuses.

## Measured evidence (2026-08-10)

T-2031 was dropped (in error, by the coordinator) and its successor T-2033
filed. T-2031 is terminal, yet:

    $ uv run frob worktree release-lease T-2031
    WARNING: tickets: /home/logan/projects/frob refused to release lease for
      T-2031 -- it is still live (worktree exists, ticket is in the ledger,
      and a process holds it); not orphaned
    ERROR: frob worktree release-lease: T-2031's lease is not stale -- its
      worktree exists, its ticket is in the ledger, and a process holds it;
      use `frob worktree remove` (and the ordinary ticket-close path) instead

Hit twice in one session, roughly an hour apart, both times on T-2031.
`fleet_status.py` still lists the lease:

    LEASES 8
      ...
      T-2031 -> frob-suggest-scripts
      T-2033 -> frob-suggest-scripts

Both ids leasing the same worktree, one of them terminal.

## Why it matters

A terminal ticket holding a scope lease suppresses the doable queue: any
other ticket declaring those files is refused with `ScopeLeaseConflict` and
reports as not-doable, for work that can never resume. The standing
coordinator duty is to reclaim holder-dead leases specifically so the queue
is not artificially suppressed, and this is a class the reclaim verb cannot
reach.

The suggested remedy in the error text (`frob worktree remove`) is wrong
here: the worktree is legitimately live and another ticket is actively
working in it. Removing it would destroy that agent's checkout.

## Root cause

`lease_staleness_reason` (`src/frob/tickets/_leases.py`) has three shapes --
`path-gone`, `ticket-gone`, `holder-dead`. There is no `ticket-terminal`
shape. "In the ledger" is treated as proof of liveness, but a ticket can be
in the ledger and permanently finished.

## Do NOT fix it this way

- Do NOT make `release-lease` unconditional or add a `--force` that skips the
  staleness check. The check exists because releasing a genuinely live lease
  lets two agents write the same files; that failure is worse than a
  suppressed queue entry.
- Do NOT resolve it by removing the worktree, as the current error text
  suggests. Terminal-ticket-with-live-worktree is exactly the case where
  another ticket is legitimately working there.
- Do NOT auto-release on every ledger read. The release should be an
  explicit, logged action, not a silent side effect of an unrelated command.
- Do NOT make `drop`/`close` the only fix by releasing at transition time and
  leaving the reclaim path broken. That helps future drops but cannot recover
  a lease already stranded, and a process killed between the state change and
  the release recreates the problem.

## Acceptance criteria

1. A test where a `dropped` ticket holds a lease on a LIVE worktree, and
   `release-lease` succeeds and releases it. THIS TEST MUST FAIL BEFORE THE
   FIX -- watch it fail and record the observed output.
2. The same for a `done` ticket.
3. A test that a lease held by an `in-progress` ticket on a live worktree is
   still REFUSED -- the existing protection must not weaken.
4. A new distinct staleness reason (e.g. `ticket-terminal`) surfaced in the
   log line, so the reclaim is attributable rather than indistinguishable
   from `holder-dead`.
5. Report how many currently-held leases in this repo belong to terminal
   tickets. Use `scripts/fleet_status.py` plus each ticket's state; state the
   denominator.

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
T-2024, T-2033, T-2041, T-2048 itself). 3 of 13 (T-2086,
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
