---
id: T-1806
title: 'Generalize lease staleness: path-gone, ticket-gone, and holder-dead are all
  the same check'
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
- tests/test_ticket_leases.py
- design/frob.strata
- tickets/T-1806/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: add unit tests for the unified lease-staleness predicate
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes design/frob.strata for the new public symbol;
    the v2 ledger's own ticket file needs to be in scope for SCOPE001 (LEDGER_PATH's
    implicit-scope rule only covers legacy tickets.md, not v2 per-ticket files)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1806/ticket.md
  reason: sys sync-interface writes design/frob.strata for the new public symbol;
    the v2 ledger's own ticket file needs to be in scope for SCOPE001 (LEDGER_PATH's
    implicit-scope rule only covers legacy tickets.md, not v2 per-ticket files)
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_path_gone
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_ticket_gone
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_holder_dead
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_live_lease_is_not_stale
- tests/test_ticket_leases.py::TestOrphanedLeases::test_finds_a_ticket_gone_lease
- tests/test_ticket_leases.py::TestOrphanedLeases::test_finds_a_holder_dead_lease
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_ticket_gone_lease
- tests/test_ticket_leases.py::TestReleaseOrphanedLease::test_releases_a_holder_dead_lease
designated_repro_test: null
threat: null
component: null
---
A third orphaned-lease shape, found live while clearing
`.git/frob-leases/T-draft-30ce107e.json` (a retired agent's worktree):
the ticket id it named did not exist in main's ledger at all (a DRAFT
that lived only in that worktree's own local ledger, never promoted),
its worktree PATH still existed on disk, but no live process owned it.

All three supported recovery paths refused, each correctly by its own
narrow rule, producing a genuine deadlock:
- `frob worktree remove <path>` -> `kept:lease(T-draft-30ce107e 7643s)`
  (correct: never remove a worktree still holding a lease)
- `frob worktree release-lease` -> not applicable (T-1789's detector only
  covers a lease whose recorded WORKTREE PATH no longer exists; this
  path still existed)
- `frob ticket drop T-draft-30ce107e` -> `NotFound` (the draft never
  existed in main's ledger to drop -- it lived only in the dead
  worktree's own local view)

Recovered by hand: `rm .git/frob-leases/T-draft-30ce107e.json`, the
exact "no scoped verb exists, so raw filesystem work it is" pattern that
ran through all seven T-1779 incidents.

GENERALIZATION (the actual ask, not a fourth special case): a lease is
STALE if ANY of three independent conditions holds, not just the one
T-1789 currently checks:

1. Path gone (T-1789's `orphaned_leases`/`release_orphaned_lease`,
   already shipped).
2. Ticket gone -- the lease names an id absent from main's authoritative
   ledger. Trivially checkable (load_queue + membership test), currently
   UNCHECKED, and it is what hard-deadlocked this exact incident: the
   verb that would release it (`ticket drop`) cannot find the ticket to
   drop in the first place.
3. Holder dead -- path and ticket both exist, but no live process
   occupies the worktree (T-1739's own liveness probe,
   `scan_for_live_worktree_process`, already exists and is exactly the
   right check -- it is just never run against a HELD lease today, only
   against a worktree during `sweep`/`remove`).

Prefer ONE check ("is this lease still valid, for any reason") over
three special cases bolted together -- this is the third time in one
session lease-lifetime and ticket-lifetime have come apart differently;
a fourth shape is likely, and each new one should not need its own new
verb.

TWO DESIGN POINTS from the incident, not prescriptions:

- `frob worktree remove` should be able to SAY WHY it refused and name
  the specific release path, not just print `kept:lease(...)` with no
  next step. It already knows the ticket id at that moment -- it can
  check whether that id exists in the ledger and whether its holder
  process is alive, and suggest the right verb instead of sending the
  operator to the filesystem.
- Drafts should not be able to hold a GLOBAL lease (`.git/frob-leases/`,
  visible from every worktree) for a ticket that exists only in ONE
  worktree's LOCAL ledger. That asymmetry is the actual root cause
  behind shape 2 -- the lease outlives the only place its ticket is
  recorded, so nothing global can ever resolve it by id. Either promote
  the draft at lease-record time, or scope the lease to the same place
  the ticket actually lives.

Cross-references: T-1789 (path-orphan detection/release, the mechanism
this generalizes); T-1779 (the root-checkout-write-guard family this is
the same "no scoped verb" pattern from).

## Done report

Unified the three orphaned-lease shapes into one predicate,
`lease_staleness_reason(root, record) -> str | None`
(`src/frob/tickets/_leases.py`): `"path-gone"` (T-1789's original
check), `"ticket-gone"` (the recorded ticket id is absent from `root`'s
authoritative ledger -- the exact shape that hard-deadlocked the
incident this ticket documents, since `frob ticket drop` cannot find
the ticket to drop it), and `"holder-dead"` (worktree and ticket both
exist, the lease has passed `is_lease_ttl_expired`'s horizon, AND no
live process is cwd'd into the worktree -- gated on TTL, not the
process scan alone, because a dispatched agent's worktree has no
persistent process sitting in it between tool calls; an ungated check
would misjudge every actively-worked ticket as stale).

`orphaned_leases` and `release_orphaned_lease` (both pre-existing,
T-1789) now build on this single predicate instead of `orphaned_leases`'
own `Path(...).exists()`-only check, so both cover all three shapes with
no divergence between "report" and "release" logic. `frob worktree
release-lease TICKET-ID`'s CLI messaging (`src/frob/app/
worktree_runner.py`) updated to match the generalized "not stale"
refusal wording.

Regression-tested the exact hard-deadlock the coordinator's fresh
incident named: `TestReleaseOrphanedLease.test_releases_a_ticket_gone_lease`
first asserts `frob ticket drop` on the ticket-gone id fails (SystemExit,
lease file untouched), THEN asserts `release_orphaned_lease` clears it --
demonstrating the CLI-drop path is a genuine dead end and the new
predicate is the only resolution.

`scan_for_live_worktree_process` (pre-existing, T-1715/T-1739) already
avoids the `pgrep -f` self-match trap flagged by the coordinator -- it
walks `/proc` directly, explicitly excludes `os.getpid()`, and matches
on `/proc/<pid>/cwd` resolution, never a command-line substring.

Merged main before landing (2 commits behind: T-1479/T-1508 daemon-proxy
work). Reset `pyproject.toml`/`uv.lock` to main's version per the
coordinator's note (neither is in this ticket's scope).

### Changed
```
 design/frob.strata              |  35 ++++----
 src/frob/app/worktree_runner.py |  16 ++--
 src/frob/tickets/_leases.py     | 148 ++++++++++++++++++++++++-------
 tests/test_ticket_leases.py     | 192 ++++++++++++++++++++++++++++++++++++++--
 tickets/T-1806/ticket.md        |  25 +++++-
 5 files changed, 354 insertions(+), 62 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 760 warning(s), 735 waived
- error-findings: none (measured, zero errors)
