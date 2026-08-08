---
id: T-1789
title: Orphaned-lease detection gate + targeted lease-release verb (T-1779 finding
  7)
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/app/worktree_runner.py
- docs/modules/tickets.md
- tests/test_ticket_leases.py
- tickets/T-1789/ticket.md
- tickets/T-1790/ticket.md
- design/frob.strata
- tickets/T-1789/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: docs section for the new orphaned-lease primitives; tests/test_ticket_leases.py
    for the new coverage; v2-store per-ticket ledger files for this draft and the
    sibling nested-worktree draft it references; design/frob.strata for SELFAUDIT001/SYS104's
    interface-list requirement on the two new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ticket_leases.py
  reason: docs section for the new orphaned-lease primitives; tests/test_ticket_leases.py
    for the new coverage; v2-store per-ticket ledger files for this draft and the
    sibling nested-worktree draft it references; design/frob.strata for SELFAUDIT001/SYS104's
    interface-list requirement on the two new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1789/ticket.md
  reason: docs section for the new orphaned-lease primitives; tests/test_ticket_leases.py
    for the new coverage; v2-store per-ticket ledger files for this draft and the
    sibling nested-worktree draft it references; design/frob.strata for SELFAUDIT001/SYS104's
    interface-list requirement on the two new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1790/ticket.md
  reason: docs section for the new orphaned-lease primitives; tests/test_ticket_leases.py
    for the new coverage; v2-store per-ticket ledger files for this draft and the
    sibling nested-worktree draft it references; design/frob.strata for SELFAUDIT001/SYS104's
    interface-list requirement on the two new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: docs section for the new orphaned-lease primitives; tests/test_ticket_leases.py
    for the new coverage; v2-store per-ticket ledger files for this draft and the
    sibling nested-worktree draft it references; design/frob.strata for SELFAUDIT001/SYS104's
    interface-list requirement on the two new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1789/done-report.md
  reason: v2-store Done report file for this ticket itself
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_leases.py::TestOrphanedLeases::test_finds_a_lease_pointing_at_a_gone_worktree
- tests/test_ticket_leases.py::TestOrphanedLeases::test_live_worktree_lease_is_not_orphaned
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_genuinely_orphaned_lease
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_a_live_worktree_lease
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_refuses_an_unknown_ticket_id
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_an_orphaned_lease
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_exits_1_for_a_live_worktree
designated_repro_test: null
threat: null
component: null
---
T-1779 follow-up (finding 7, reported live): `.git/frob-leases/T-1766.json`
named a worktree path that no longer existed (a NESTED worktree under an
agent that had already been retired and removed) -- `frob ticket doable`
correctly refused to offer T-1766 forever, held by a ghost lease, and
nothing in the system ever reported it. The coordinator had to clear it
by hand (`rm .git/frob-leases/T-1766.json`) with five live agents running,
because no scoped verb existed to release one stale lease safely.

TWO requirements, both small and both needed to actually unblock a
coordinator holding several live agents without quiescing the fleet:

1. **Orphaned-lease detection, as a gate finding, not just a cleanup
   action.** For each file under `.git/frob-leases/`, check whether its
   recorded `worktree` path still exists (`Path.exists()` -- cheap, no
   process scan needed, a different and cheaper check than T-1739's
   worktree-liveness scan which reasons worktree-outward instead of
   lease-outward). A lease naming a nonexistent path silently removes a
   ticket from `doable` forever with no diagnostic anywhere -- this is
   "a gate that lies by omission", the class this repo's own priority
   order treats as critical (`frob.tickets._leases` already has
   `_probe_worktree_liveness`'s confirmed_absent/ambiguous split for a
   RELATED question; this is the narrower, cheaper "does the path exist
   at all" check that specific split does not currently drive a
   standalone finding from).

2. **A targeted lease-release verb**, so a coordinator can release ONE
   stale lease without a fleet-wide `frob worktree sweep` (unsafe with
   live agents -- T-1779's own gap-3 fix, `frob worktree remove <path>`,
   only handles a worktree that still exists on disk; a GHOST lease with
   no worktree left to point `remove` at needs its own release path).
   `frob worktree remove <ticket-id-or-path>` recognizing a bare ticket
   id as "release this ticket's lease, worktree gone or not" and/or a
   dedicated `frob ticket release-lease <id>` verb are both reasonable
   shapes -- pick whichever fits `frob.tickets._leases`'s existing
   `release_lease`/`record_lease` primitives most directly (the
   mechanism to remove a lease FILE already exists internally;  this is
   about exposing a SAFE, scoped, discoverable CLI path to it instead of
   `rm` on the leases directory by hand).

Every incident across T-1779's whole finding set (all seven) ends the
same way: a coordinator doing raw filesystem or git work because no
scoped verb existed for the specific narrow thing that needed doing.
This ticket is that pattern's most direct instance yet -- the FIX is a
missing verb, not a missing guard.

Deliberately does NOT include "refuse nested worktree creation at the
source" (T-1766's own worktree was nested under another worktree, which
is why it died when its parent was retired) -- filed as its own separate
ticket per the analysis that produced this one, since it may be larger
than a small guard and this ticket's own two items are what unblock work
today.