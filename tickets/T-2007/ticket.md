---
id: T-2007
title: A lease recorded against the shared root can never be holder-dead, so it is
  un-reclaimable by any command
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
evidence_scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_skipped_when_agent_worktrees_exist
- tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_still_recorded_with_no_sibling_worktrees
- tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_non_root_worktree_still_records_its_own_lease
- tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_pre_existing_root_lease_staleness_is_unchanged
designated_repro_test: tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_skipped_when_agent_worktrees_exist
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-10 15:15Z, live and reproducible right now.

T-1806's `lease_staleness_reason` (`src/frob/tickets/_leases.py:562`) is
well-built and its three shapes are correctly reasoned -- read it before
touching anything. This is a gap in ONE input it depends on, not a flaw in
its design.

`"holder-dead"` requires BOTH the TTL to have elapsed AND
`scan_for_live_worktree_process` to find no live process cwd'd into the
lease's recorded worktree. That is exactly right for a DISPATCHED AGENT's
own worktree, which sits idle between tool calls.

It can NEVER fire for a lease whose recorded worktree is the SHARED ROOT,
because the shared root always has live processes (every coordinator
command, every `frob check`, every land). Such a lease is un-reclaimable by
construction.

Live instance: `.git/frob-leases/T-1686.json` records
`"worktree": "/home/logan/projects/frob"` (the root) and
`"branch": "main"`, `recorded_at 2026-08-10T08:33:29Z` -- ~6.7 hours old,
TTL elapsed, ticket still `state: in-progress`, and NO agent has worked it
for the entire session. Reproduce:

    $ uv run frob worktree release-lease T-1686
    ERROR: frob worktree release-lease: T-1686's lease is not stale -- its
    worktree exists, its ticket is in the ledger, and a process holds it;
    use `frob worktree remove` (and the ordinary ticket-close path) instead

The suggested remedy in that error message is also wrong for this shape:
`frob worktree remove` cannot be run against the shared root.

WHY IT MATTERS BEYOND THIS ONE TICKET: reclaiming holder-dead leases is a
standing hourly coordinator duty, and for this lease shape the duty is
unexecutable -- there is no command that reclaims it. T-1686's scope is
narrow today (its own two ticket files, after an earlier demote-to-
evidence-only), so it currently blocks nothing; the cost is latent. A
root-recorded lease with a BROAD scope would deadlock every agent with no
recovery path at all.

## Do not fix it this way
- Do NOT drop the live-process check for root-worktree leases and fall back
  to TTL alone. That would make any genuinely-live piece of coordinator work
  in the root reclaimable out from under itself after 6 hours -- strictly
  worse than the leak.
- Do NOT special-case T-1686 or hand-delete the lease JSON. Hand-deleting is
  the manual workaround this ticket exists to eliminate, and it teaches the
  wrong recovery.
- Do NOT record a pid to fix this. A pid is not the right liveness signal
  here (T-1806 deliberately did not use one: an agent's worktree has no
  persistent process between tool calls), and adding one would re-open the
  false-dead problem that reasoning already closed.
- Do NOT widen `holder-dead`. Consider instead whether a lease should be
  recordable against the shared root AT ALL -- a ticket being worked in the
  root is itself the "coordinator never dirties root" anti-pattern, so
  refusing to record it (or recording it with an explicit owner/liveness
  token) may be the real fix. Weigh that before widening a staleness rule.

## Acceptance criteria
1. A test that FAILS FIRST: record a lease whose worktree is the repo root,
   age it past the TTL, ensure a live process exists in the root (there
   always is one), and assert `lease_staleness_reason` currently returns
   `None` and `release-lease` refuses. Then assert the new behaviour.
2. Whatever the fix, a genuinely-live root-held lease less than the TTL old
   must still be protected -- assert no false reclaim.
3. Report, as measurement, how many CURRENT leases across this repo record
   the shared root as their worktree, with the denominator of leases
   examined.

frob:waive BUG002 reason="the fix's own committed diff genuinely reproduces-then-passes (verified directly: tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_skipped_when_agent_worktrees_exist fails at commit 14aa21fad, the test-only commit, and passes at the fix commit b5f3c57ad -- see T-2007's own Done report). This ticket's fix commit landed as a PASSENGER of T-1961's joint land (2066bc189be1, --allow-cross-ticket, both tickets committed on the same series worktree) -- main's tip already contains this fix by the time this land runs to close T-2007's own ticket state, so BUG002's land-time parent-vs-fix comparison against CURRENT main necessarily reports the designated test PASSING at the parent too, indistinguishable from confirmatory-only evidence. Same documented ledger/doc-correction shape as T-1901: no new code is landing under this ticket id, only recording that the fix (which did happen, and was verified to genuinely reproduce-then-fix at the time it was made) is attributed and closed out."

## Done report

Changed:
src/frob/tickets/_leases.py::record_lease (now skips the root case)
src/frob/tickets/_leases.py::_should_skip_root_lease (new)

Evidence:
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_skipped_when_agent_worktrees_exist
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_still_recorded_with_no_sibling_worktrees
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_non_root_worktree_still_records_its_own_lease
tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_pre_existing_root_lease_staleness_is_unchanged
Repro confirmed both via frob's own --check-repro-force (same known
PYTHONPATH bug as T-2005) and directly via git show on the parent
commit's source (the guard did not exist there).

Filed: none new (T-2005 already covers the check-repro PYTHONPATH bug)

Chosen fix direction: prevention, not a new staleness rule -- refuses
to RECORD a lease against the shared primary checkout when this repo
has dispatched agent worktrees registered, closing the leak at its
source rather than widening `lease_staleness_reason`'s "holder-dead"
shape (explicitly forbidden by the ticket). None of the "do not fix it
this way" options were used: the live-process check is untouched, no
pid was recorded, T-1686 was not hand-deleted or special-cased.

Measurement (acceptance criterion 3): 1 of 7 current leases in this
repo record the shared root as their worktree (T-1686) -- confirms the
leak is real but narrow today, matching the ticket's own "latent cost"
framing. T-1686 itself is untouched by this fix (this only prevents
FUTURE root leases; T-1686's own reclamation is separate floor-cleanup
work).

Gates: full tests/test_ticket_leases.py suite green except the one
pre-existing, unrelated TestLedgerAutoCommitEnumeratedOverDispatchTable
failure already noted in T-1961's Done report. ARCH001/ty clean.

### Changed
```
 src/frob/tickets/_leases.py   | 227 ++++++++++++++++++++++++++++++------------
 tests/test_ticket_leases.py   | 227 +++++++++++++++++++++++++++++++++++++++++-
 tickets/T-1961/done-report.md |  44 ++++++++
 tickets/T-1961/ticket.md      |   7 +-
 tickets/T-2007/ticket.md      |  11 +-
 5 files changed, 442 insertions(+), 74 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_skipped_when_agent_worktrees_exist` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_root_lease_still_recorded_with_no_sibling_worktrees` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_non_root_worktree_still_records_its_own_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRootLeaseUnreclaimable::test_pre_existing_root_lease_staleness_is_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/unit/test_tickets_evidence_only_scope.py
