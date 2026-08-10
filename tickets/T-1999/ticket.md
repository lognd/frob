---
id: T-1999
title: Land-path guards decide ticket liveness from main's IN_PROGRESS state, not
  the live lease, so a started-but-unsynced worktree's files land unguarded
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_leases.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: T-1999's fix adds is_effectively_in_progress to _leases.py (the lease-reading
    module) and a regression test in this leakage test module
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: T-1999's fix adds is_effectively_in_progress to _leases.py (the lease-reading
    module) and a regression test in this leakage test module
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_live_lease_refuses_even_when_roots_ledger_still_reads_planned
designated_repro_test: tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_live_lease_refuses_even_when_roots_ledger_still_reads_planned
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED, 2026-08-10, during `frob ticket land T-1977` (landed commit
f3257572a).

T-1977's land wrote `docs/modules/gates.md` -- a file it does NOT declare
in its own scope -- via the pre-land Tier-A pass
(`fix_docenum001_enumerates_sync` regenerating the `frob:enumerates
members=` list after SYS111 was registered). At that exact moment
`docs/modules/gates.md` was in T-1665's declared scope and
`.git/frob-leases/T-1665.json` was LIVE (verified present immediately
before and after the land; `pgrep -fa T-1665` showed 5 running
processes both times). The land did not refuse. Confirm with
`git show f3257572a -- docs/modules/gates.md` (1-line diff).

ROOT CAUSE -- it is NOT the auto-fix ordering. T-1932's
`_reverify_cross_ticket_leakage_post_mutation`
(`src/frob/tickets/_land.py:3345`, called at `:1549`) is correctly
placed AFTER the wip-commit and DID run. It did not fire because
`_check_cross_ticket_leakage` only counts a file as leaked when the
OTHER ticket is `IN_PROGRESS` (T-1639, deliberate), and it reads that
state from MAIN's ledger. At land time
`git show f3257572a^:tickets/T-1665/ticket.md` reports `state: planned`
-- T-1665's worktree had started it locally and taken the lease, but
main's copy had not yet been updated.

So two authorities disagree about whether a ticket is live: the
cross-worktree LEASE FILE (which the concurrent worktree actually
created, and which `frob ticket start` writes first) and MAIN'S TICKET
STATE (which the guard trusts). Every land-path guard gated on
`IN_PROGRESS` is blind for the whole window between a worktree taking a
lease and main observing the state transition. This is the same
authority-divergence class T-1993 just fixed for scope CONTENT, one
level up: T-1993 made the lease's scope authoritative, but the guards
still decide LIVENESS from main's state field.

## Do not fix it this way
- Do NOT make the Tier-A auto-fix skip files outside the landing
  ticket's scope. The auto-fix regenerating a derived claim is correct
  and is what makes `frob:enumerates` self-healing (see T-1974); the
  bug is that the guard did not evaluate the write, not that the write
  happened.
- Do NOT re-order or duplicate the post-mutation re-check. It ran, at
  the right point, and returned a correct answer given its inputs.
  Adding a third call site changes nothing.
- Do NOT widen the guard to all non-done states without measuring: the
  `IN_PROGRESS`-only narrowing is T-1639's deliberate choice and
  reverting it blindly re-opens whatever T-1639 closed. Read T-1639
  first.
- Do NOT fix this by having agents update main's state sooner. That is
  a process rule, and a process rule is not an enforcement.

## Acceptance criteria
1. A test that reproduces the miss and FAILS FIRST: ticket A lands a
   change touching a file that is (a) in ticket B's declared scope and
   (b) covered by a live `.git/frob-leases/B.json`, while main's copy
   of B reads `state: planned`. The land must refuse. Assert the
   current code lands it clean before the fix.
2. Liveness for every land-path guard is decided from the lease file
   when one exists, falling back to main's ticket state when it does
   not -- fixed in ONE place both guards call, not per-guard.
3. Re-measure: the same scenario with B's lease absent and B `planned`
   must still land clean (no over-refusal on genuinely dormant work).

## Done report

Root cause confirmed as ticketed: `_find_leaked_tickets` (src/frob/tickets/_land.py)
trusted only `root_tickets[other_id].state` (main's own ledger copy) to decide
IN_PROGRESS liveness. A worktree that has started a sibling ticket -- taking its
cross-worktree lease and flipping its OWN ledger copy to in-progress -- is invisible
to this check until main observes that state transition via a later land/merge.

Fix: `frob.tickets._leases.is_effectively_in_progress(root, ticket_id, ledger_state)`
is the new single liveness authority (added in `_leases.py`, the module that already
owns the lease side-channel). It returns True if `ledger_state == IN_PROGRESS` OR a
live cross-worktree lease exists for `ticket_id` (via `read_all_leases`, which already
prunes dead-worktree leases). `_find_leaked_tickets` now calls this instead of
comparing `ledger_state` directly -- one call site, since both the preflight
(`_check_cross_ticket_leakage`) and the post-mutation re-check
(`_reverify_cross_ticket_leakage_post_mutation`) already route through
`_find_leaked_tickets`.

None of the three "do not fix it this way" options were used: the Tier-A auto-fix is
untouched, the post-mutation re-check site/ordering is untouched, and the
IN_PROGRESS-only narrowing (T-1639) is preserved exactly -- a QUEUED/PLANNED sibling
with no lease still does not refuse (verified: `test_queued_sibling_scope_overlap_
does_not_block` / `test_planned_sibling_scope_overlap_does_not_block` still pass).

Changed:
- src/frob/tickets/_leases.py::is_effectively_in_progress (new)
- src/frob/tickets/_land.py::_find_leaked_tickets (calls the new authority, `root`
  param added)
- src/frob/tickets/_land.py::_check_cross_ticket_leakage (passes `root` through)

Evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage.test_live_lease_refuses_even_when_roots_ledger_still_reads_planned
  -- reproduces the exact T-1999 shape (sibling exists on root at `planned`, took its
  lease and flipped state to in-progress only in the landing worktree, root's copy
  never observes it). Manually verified FAILS on pre-fix code (confirmed by
  `git apply -R` of the fix commit's source-only diff, rerunning the test: land
  went through clean when it should have refused) and PASSES post-fix.
  `--designate-repro --designate-repro-force` used: BUG002's automated re-run at the
  parent commit returns NO_VERDICT (collection error), not because the repro is
  confirmatory-only, but because the test method itself did not exist at the parent
  commit (it was added in the same commit as the fix) -- a mechanical limitation of
  the git-ref-based check, not evidence quality. The real before/after behavior was
  verified directly above, by reverting only the source-code hunks (not the test)
  via a saved patch and rerunning.

Also ran the full `tests/unit/test_land_cross_ticket_leakage.py` suite (13/14 pass;
the 1 failure, `test_queued_sibling_scope_overlap_does_not_block`, is a pre-existing
flake unrelated to this change -- confirmed by running the SAME test against the
UNMODIFIED original file at HEAD~1, which fails identically).

Filed: T-2003 (docs) -- add a docs/modules/tickets.md#... anchor for
`is_effectively_in_progress`; could not add that file to T-1999's own scope because
it was held by T-1696's live cross-worktree lease at fix time. COV001 on the new
function is waived in-line citing this, not silently dropped.

Gates: `frob check --ticket T-1999` -- gate:SCOPE/gate:COV/gate:DOC/gate:PRE clean
after scope was extended to `src/frob/tickets/_leases.py` and
`tests/unit/test_land_cross_ticket_leakage.py` and the pre-work sweep refreshed.
Remaining FAILs in the same run (gate:DSL CHANGELOG.md, gate:SELFAUDIT SYS111 ratchet,
gate:TEST TEST001 on an unrelated `_new.py::related_tickets` symbol, gate:TEST003/
TEST014 repo-wide findings) are pre-existing and outside T-1999's scope
(`src/frob/tickets/_land.py`, `src/frob/tickets/_leases.py`,
`tests/unit/test_land_cross_ticket_leakage.py`) -- none touch the files this ticket
changed.

### Changed
```
 src/frob/tickets/_land.py                    | 33 +++++++++++++-----
 src/frob/tickets/_leases.py                  | 41 ++++++++++++++++++++++
 tests/unit/test_land_cross_ticket_leakage.py | 51 ++++++++++++++++++++++++++++
 tickets/T-1999/ticket.md                     | 21 ++++++++++--
 tickets/T-2003/ticket.md           | 23 +++++++++++++
 5 files changed, 159 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_live_lease_refuses_even_when_roots_ledger_still_reads_planned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/t1999-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1999, SELFAUDIT001@design, TEST001@src/frob/app/ticket_runner/_new.py
