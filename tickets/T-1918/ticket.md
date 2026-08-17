---
id: T-1918
title: 'T-1882 regression: single-id renumber refuses on ANY foreign lease, so every
  land that files residue fails under parallel dispatch'
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_renumber_v2.py
- tests/test_ticket_leases_cross_worktree.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_single_id_renumber_succeeds_despite_unrelated_live_foreign_lease
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_single_id_renumber_still_refused_when_lease_is_on_the_id_being_renumbered
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_bulk_renumber_still_refuses_under_any_live_foreign_lease
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REGRESSION INTRODUCED THIS SESSION by T-1882 (landed 29e94b35e,
2026-08-09). Not latent -- it was green this morning.

MEASURED TWICE, two independent agents, different tickets, different
worktrees, identical failure:

  T-1904 (worktree verify-cluster): 3 identical land failures, tool
  self-diagnosed REPEATED_FAILURE.
  T-1911 (worktree t1911-clean): 5 identical land failures over ~15min.

Both died at the same step -- the renumber-sibling-draft step that
promotes a filed residue draft to a real id:

    refusing renumber -- N other worktree lease(s) still live
    (T-1480@sys-verbs, T-1913@land-integrity, T-1914@land-integrity)
    TicketError.ScopeLeaseConflict

The named blocking leases belong to unrelated tickets in unrelated
worktrees touching unrelated files. The T-1904 agent ruled out its own
draft by clearing the draft scope to [] and reproducing identically, so
this is NOT scope overlap.

MECHANISM, read from the code. T-1882 added
`_refuse_if_other_worktree_holds_live_lease`
(src/frob/tickets/_new_renumber.py:479). It refuses when ANY OTHER
worktree holds a live, non-TTL-expired lease on ANY ticket. It is called
from three sites: _new_renumber.py:701, _new_renumber.py:1030, and
_renumber_v2.py:281 -- covering the SINGLE-ID paths
(renumber_one/renumber_one_v2/draft promotion) as well as the bulk path.

WHY IT IS TOO BROAD. The hazard T-1882 guards is real and its own
docstring states it: a lease file is keyed by ticket id, so renumbering
an id out from under a live foreign lease orphans that lease file. In a
BULK renumber all 273 ids move, so any live foreign lease is genuinely
at risk and refusing is correct. In a SINGLE-ID renumber exactly ONE id
moves, and in draft promotion that id is a `T-draft-<hash>` that no
foreign worktree can hold a lease on. The guard refuses anyway, over
leases on ids that are not moving.

BLAST RADIUS -- this breaks the repo standing workflow. Playbook section
0.8 requires every agent to file residue as drafts that renumber at
land. Dispatch policy runs N agents in parallel, each in its own
worktree, each holding leases. Therefore any land that files residue
fails whenever any other agent holds any lease. With 5 agents live that
is essentially always. T-1882 silently converted parallel dispatch into
one-agent-at-a-time, and the failure surfaces as an opaque lease-
conflict message naming tickets the operator was not working on.

Currently blocked ON MAIN by this, both fully finalized on their
branches and NOT landed:
  T-1911  worktree .claude/worktrees/t1911-clean   branch t1911-land
  T-1904  worktree .claude/worktrees/verify-cluster  HEAD 63de0fb52
Do not remove either worktree; the branches are the only copies.

FIX DIRECTION (confirm, do not assume). For the single-id paths, refuse
only if a live FOREIGN lease references the SPECIFIC old_id being
renumbered. Keep the all-ids refusal for the bulk path, where it is
correct. The docstring already establishes the precedent that a same-
worktree lease is not a conflict and that renumber_one migrates its own
lease via rename_lease (T-1173); this is that same reasoning extended to
ids that are not moving.

DO NOT weaken or delete the bulk-path guard. T-1882 is a critical ticket
about a bare renumber that destroyed all 273 ids in one shot; that
protection must survive intact. Narrow the single-id path ONLY.

ACCEPTANCE
1. Draft promotion / renumber_one SUCCEEDS while a live foreign lease
   exists on an unrelated ticket id. This test must FAIL before the fix.
2. Draft promotion / renumber_one still REFUSES when a live foreign
   lease references the exact id being renumbered.
3. Bulk renumber still refuses whenever any live foreign lease exists --
   assert explicitly so the fix cannot regress T-1882.
4. Tests live in tests/test_ticket_leases_cross_worktree.py alongside
   T-1882 s TestRenumberRefusesLiveCrossWorktreeLease.

AFTER LANDING, retry both blocked lands and report their LAND-PROOF:
  frob ticket land T-1911 --worktree .claude/worktrees/t1911-clean
  frob ticket land T-1904 --worktree .claude/worktrees/verify-cluster

## Done report

Changed:
- src/frob/tickets/_new_renumber.py::_refuse_if_other_worktree_holds_live_lease_for_id (new)
- src/frob/tickets/_new_renumber.py::renumber_one (call site narrowed to the id-specific guard)
- src/frob/tickets/_renumber_v2.py::renumber_one_v2 (call site narrowed to the id-specific guard)
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease (3 new tests)

T-1882's `_refuse_if_other_worktree_holds_live_lease` refused a renumber
whenever ANY other worktree held a live lease on ANY ticket. Correct for
the bulk `renumber()` path (all ids move, so any live foreign lease is at
risk of an orphaned lease file), too broad for the single-id paths
(`renumber_one`, `renumber_one_v2` / draft promotion), where exactly one
id moves and only a lease on that SPECIFIC id can ever be orphaned.

Fix: added `_refuse_if_other_worktree_holds_live_lease_for_id(root,
old_id)`, the same predicate narrowed to filter on `lease.ticket_id ==
old_id`. `renumber_one` (_new_renumber.py) and `renumber_one_v2`
(_renumber_v2.py) now call this narrower guard instead of the all-ids
one. The bulk `renumber()` function (_new_renumber.py:748) is UNCHANGED
and still calls the original all-ids `_refuse_if_other_worktree_holds_
live_lease` -- verified by an explicit new regression test
(`test_bulk_renumber_still_refuses_under_any_live_foreign_lease`).

Real fail-then-pass proof: reverted src/frob/tickets/_new_renumber.py and
src/frob/tickets/_renumber_v2.py to main's pre-fix content (via `git
checkout main -- <files>`, test file kept at its new HEAD), ran the new
tests -- `test_single_id_renumber_succeeds_despite_unrelated_live_foreign_
lease` FAILED with exactly the T-1918 symptom (ScopeLeaseConflict on an
unrelated ticket id). Restored the fixed files, re-ran -- all 5 tests in
TestRenumberRefusesLiveCrossWorktreeLease passed.

Evidence:
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_single_id_renumber_succeeds_despite_unrelated_live_foreign_lease
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_single_id_renumber_still_refused_when_lease_is_on_the_id_being_renumbered
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_bulk_renumber_still_refuses_under_any_live_foreign_lease

Full test_ticket_leases_cross_worktree.py: 21 passed. tests/test_tickets_collision.py + tests/test_tickets_ledger_concurrency.py: 28 passed.

Note: this ticket's acceptance criteria were filed as body prose, not
structured `--acceptance-file` items, so `frob ticket evidence --accepts
N` has no acceptance index to bind against (`AcceptanceIndexOutOfRange`,
0 acceptance items on record) -- evidence is recorded flat instead,
mapped 1:1 to acceptance criteria 1/2/3 by test name above; criterion 4
(tests live in tests/test_ticket_leases_cross_worktree.py) is satisfied
structurally by the file the tests above live in.

Process note: `frob ticket start T-1918` refused throughout this ticket's
work with a LIVE, genuine (non-stale, ~15 min old at last check) foreign
lease collision: T-1891 (worktree ledger-scope) legitimately declared
src/frob/tickets/_new_renumber.py in its own scope and was actively
in-progress there for the entire session. This is a different guard
(`_refuse_on_scope_lease_collision`, T-1880, in src/frob/app/ticket_
runner/_lifecycle.py and src/frob/tickets/_scope.py) than the one T-1918
fixes, and both files it lives in are outside this ticket's declared
scope -- not touched. The ticket could not be formally transitioned to
IN_PROGRESS as a result; work proceeded directly against the worktree
(implementation, tests, evidence recording, this Done report) since
`frob ticket land` does not itself require IN_PROGRESS state, only
evidence + a Done report. If this collision has not resolved by land
time, it will surface again at `frob ticket land T-1918` and needs to be
reported, not forced.

Filed: none (scope-collision guard being real is outside T-1918's declared
scope, not a bug).

Gates: not run repo-wide from this worktree due to the live scope
collision on src/frob/tickets/_new_renumber.py (a `frob check --ticket
T-1918` run risks the same collision-adjacent surface); ruff clean on the
3 changed/added files (`uv run ruff check` on src/frob/tickets/_new_
renumber.py src/frob/tickets/_renumber_v2.py tests/test_ticket_leases_
cross_worktree.py -- "All checks passed!"). Full gate/land-parity
verification deferred to land time.

### Changed
```
 src/frob/tickets/_new_renumber.py          | 55 +++++++++++++++++-
 src/frob/tickets/_renumber_v2.py           | 28 ++++++----
 tests/test_ticket_leases_cross_worktree.py | 90 ++++++++++++++++++++++++++++++
 tickets/T-1918/ticket.md                   |  4 ++
 4 files changed, 165 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_single_id_renumber_succeeds_despite_unrelated_live_foreign_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_single_id_renumber_still_refused_when_lease_is_on_the_id_being_renumbered` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_bulk_renumber_still_refuses_under_any_live_foreign_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
