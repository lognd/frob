---
id: T-1868
title: 'Two in-progress tickets held the same path: scope --add bypasses the lease-conflict
  check that start enforces'
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_mutate.py
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Two live leases held the SAME path at the same time, in two different
worktrees. Mutual exclusion is the entire purpose of the lease, so this
is a correctness failure, not a nuisance.

MEASURED, 2026-08-08, straight from `.git/frob-leases/`:

    T-1863  worktree .claude/worktrees/sweep-regress   recorded 14:28:39Z
    T-1822  worktree .claude/worktrees/runner-wiring   recorded 14:29:15Z

Both scopes contain `design/frob.strata`. Both tickets were in-progress
simultaneously. Thirty-six seconds apart, and nothing refused the
second.

SUSPECTED MECHANISM -- CONFIRM BEFORE FIXING. The conflict check appears
to run at `frob ticket start`, when the lease is first taken, but NOT on
`frob ticket scope --add`. T-1863 declared `design/frob.strata` in its
original scope and started first. T-1822 did not; the path was added to
it AFTER it had already started. There is a very plausible route for
that: T-1856's agent reported this same session that `sys sync-interface`
AUTO-UPDATES `design/frob.strata` when a store interface gains a symbol,
which then trips COV002 and pushes the implementer to scope-add the file
to satisfy the gate. So the widening is not even a mistake an agent
chooses to make -- another frob verb steers them into it.

Verify that route (`_mutate.py`'s scope-add path versus `_leases.py`'s
acquisition check) before writing the fix. If the real mechanism is
different, fix what is actually there and correct this description.

REQUIRED:

1. `frob ticket scope --add` must run the SAME lease-conflict check that
   `frob ticket start` runs, and refuse with the same named refusal when
   the path is already leased by another in-progress ticket, naming the
   holder and its worktree. Widening a scope after start is exactly as
   dangerous as declaring it broad up front -- more so, because nobody
   is watching by then.
2. Audit every other path that can mutate a ticket's scope for the same
   gap. `sys sync-interface`, any Tier-A/Tier-B auto-fix that edits a
   ticket, and land-time scope adjustments all qualify. A check that
   guards one entry point and not its siblings is the shape this repo
   has already been bitten by repeatedly (T-1740's staged residue,
   T-1775's stale auto-fix, T-1817's by-construction firing).
3. Decide what to do about the `sys sync-interface` -> COV002 ->
   scope-add pipeline that generates this pressure. Refusing the
   scope-add without addressing the pressure just relocates the
   deadlock. Prefer a route where the auto-update does not force a
   contended shared file into an unrelated ticket's scope.

RELATED, FOUND IN THE SAME SWEEP: T-1556 is queued with a COMPLETELY
EMPTY scope (`scope=[]`). A ticket with no scope can lease nothing and
be gated by nothing -- `frob check --ticket T-1556` cannot mean anything.
That is the opposite failure from the mega-glob problem T-1866 addresses
and it deserves the same treatment: an empty scope on a non-epic ticket
should be refused at `start`, not silently accepted. Fold it in here or
file it separately, but do not let it drop.

frob:ticket -- this is a data-integrity fix on the lease system; it must
land with a regression test that actually reproduces the double-hold
(two in-progress tickets, one scope-add, assert the refusal), not merely
a unit test of the check function in isolation.
