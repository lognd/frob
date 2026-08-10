---
id: T-2007
title: A lease recorded against the shared root can never be holder-dead, so it is
  un-reclaimable by any command
state: in-progress
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
