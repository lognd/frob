---
id: T-2264
title: 'Lease liveness misses in-flight lands: frob ticket land runs from the ROOT
  with --worktree, so a lease 454s into a live land is classified reclaimable'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
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
  glob: tests/test_ticket_leases.py
  reason: T-2264 fix requires new regression tests for the land-in-flight lease-liveness
    fix; test file is the required evidence location for _leases.py changes
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_land_shields_lease
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_holder_dead
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_in_progress_lease_on_a_live_worktree_is_not_stale
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_other_land_no_shield
designated_repro_test: tests/test_ticket_leases.py::TestLeaseStalenessReason::test_land_shields_lease
acceptance:
- text: 'A lease whose ticket has a land in flight is not classified reclaimable and
    is not reclaimable by release-lease (fails today: measured at 454s into a live
    land)'
  evidence:
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_land_shields_lease
- text: 'MUST-STILL-PASS: a genuinely dead holder is still reclaimable, and a live
    in-worktree agent is still live'
  evidence:
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_holder_dead
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_in_progress_lease_on_a_live_worktree_is_not_stale
- text: fleet_status's classifier and _leases.py staleness give the same verdict for
    the same lease; state how they are kept in sync
  evidence:
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_land_shields_lease
- text: Detection derives from structured land state, never from text-matching process
    arguments
  evidence:
  - tests/test_ticket_leases.py::TestLeaseStalenessReason::test_other_land_no_shield
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 71ff94b4e72ee5a98ff728c0b2898bf0356e01d0
---
# Lease liveness misses a land: `frob ticket land` runs from the ROOT with `--worktree <path>`, so a lease with an in-flight land is classified RECLAIMABLE

## Measured evidence (2026-08-17)

One `fleet_status` run contradicted itself:

    LANDS IN FLIGHT: 3
      T-2220 ... elapsed=20s
      T-2242 ... elapsed=147s
      T-2254 pids=2240749,2240772,2240774,2240781 elapsed=454s cpu=69s
    ...
      T-2254 -> t-2254  [reclaimable]        <-- same output, same run

T-2254's land had been running for 454 seconds and the same report called its
lease reclaimable.

Why: the land runs entirely from the repo root and names its target with a
flag.

    pid=2240749  cwd=<root>
    pid=2240772  cwd=<root>   timeout 540 uv run frob ticket land T-2254 \
                                --worktree .claude/worktrees/t-2254
    pid=2240774  cwd=<root>

    processes cwd'd INSIDE .claude/worktrees/t-2254: 0

Liveness is decided by "is any process cwd'd into the worktree"
(`scan_for_live_worktree_process`). A land satisfies that for ZERO of its
processes, so the busiest possible worktree reads as abandoned.

## Blast radius: this is not only the coordinator script

The same signal backs two consumers:

    scripts/fleet_status.py:266   _scan_for_live_worktree_process   (T-2222's classifier)
    src/frob/tickets/_leases.py:706  scan_for_live_worktree_process (lease staleness)

So `frob worktree release-lease` and the staleness logic behind
`frob worktree sweep` inherit the same blind spot. Acting on a "reclaimable"
verdict during a land means releasing a lease, or removing a worktree, out from
under a running land. I was about to run `frob worktree sweep` (107 worktrees /
67GB / 95 idle, filed as T-2261) and deferred it only because lands were
visibly in flight -- not because any guard told me to.

## The information already exists in the same process

`fleet_status` computes LANDS IN FLIGHT, keyed on ticket id, in the SAME run
that then calls the lease reclaimable. Nothing needs to be discovered; the two
facts simply are not joined. That makes this a self-consistency defect, not a
detection gap.

## Do NOT fix it this way

- **Do NOT grep `ps` output for the ticket id.** Process-counting by text has
  already produced a 4x miscount here ("15-16 concurrent lands" when there were
  four). Standing user directive: token/grammar, never lexical. Use the
  structured in-flight-land set that already exists.
- **Do NOT remove or weaken the cwd check.** It is correct for the case it was
  built for -- an agent working inside its worktree -- and it is what makes
  holder-death detectable at all. This is an ADDITIONAL liveness source, not a
  replacement.
- **Do NOT treat every root-cwd process as blocking.** The coordinator, hooks,
  and every `git -C <root>` invocation live at the root; that would make every
  lease permanently live and disable reclamation entirely -- the mirror-image
  failure of T-2007's unreclaimable root lease.
- **Do NOT fix only `scripts/fleet_status.py`.** The script duplicates this
  logic under its deliberate no-frob-import contract, but `_leases.py` is the
  authoritative copy and backs `release-lease`. Fixing the display while
  leaving the reclamation path wrong is the more dangerous half.

## Acceptance criteria

1. (MUST FAIL FIRST) A lease whose ticket has a land in flight is NOT
   classified reclaimable, and is not reclaimable by `release-lease`. Fails
   today: measured above at 454s into a live land.
2. MUST-STILL-PASS CONTROLS: a genuinely dead holder (no processes, no land) is
   STILL reclaimable -- T-1382's stale lease was cleared this way and that must
   keep working; and a live in-worktree agent is still live. A fix that makes
   everything look live re-creates T-2007's unreclaimable-lease class.
3. The two consumers agree: `fleet_status`'s classifier and `_leases.py`'s
   staleness give the same verdict for the same lease. State how you kept them
   in sync given the script's no-import contract.
4. Detection derives from structured land state, never from text-matching
   process arguments.

## Scope note

`src/frob/tickets/_leases.py` is the authoritative primitive and the dangerous
consumer (`release-lease`). `scripts/fleet_status.py` carries the duplicate and
already has several queued tickets against it (T-2213, T-2229, T-2236, T-2249,
T-2261) -- dispatch this WITH that series rather than separately, or it will
serialize behind them anyway.