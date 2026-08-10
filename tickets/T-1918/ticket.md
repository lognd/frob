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