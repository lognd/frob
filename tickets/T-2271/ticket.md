---
id: T-2271
title: 'An in-progress ticket can hold NO cross-worktree lease: T-2259 worked by a
  live agent with no lease file, so its scope reads unclaimed to T-2225''s collision
  check'
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
- src/frob/tickets/_evidence.py
evidence_scope:
- tests/test_ticket_leases_cross_worktree.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_scope_change_while_queued_then_start_leases_with_post_change_scope
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_local_close_releases_the_lease_before_a_second_worktree_sees_done
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_release_on_close_removes_the_lease
designated_repro_test: null
acceptance:
- text: 'A ticket driven to in-progress after a scope change in the same worktree
    session holds a recorded lease (fails today: T-2259)'
  evidence:
  - tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_scope_change_while_queued_then_start_leases_with_post_change_scope
- text: The recorded scope reflects the post-change scope, not a stale pre-change
    snapshot
  evidence:
  - tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_scope_change_while_queued_then_start_leases_with_post_change_scope
- text: 'MUST-STILL-PASS: ordinary start records exactly one lease; transition out
    of in-progress still releases it; --steal still behaves per _lifecycle.py:193-211;
    no lease resurrection for terminal tickets'
  evidence:
  - tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_release_on_close_removes_the_lease
- text: State the actual mechanism found -- 'it works now' is not a diagnosis
  evidence:
  - tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_local_close_releases_the_lease_before_a_second_worktree_sees_done
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# An in-progress ticket can hold NO cross-worktree lease, leaving its scope files unprotected and invisible to the collision check

## Measured evidence (2026-08-17)

T-2259 has an agent actively working it, `state: in-progress` on main, a
populated worktree -- and no lease anywhere:

    $ ls .git/frob-leases/
    T-1686.json T-2213.json T-2255.json T-2264.json T-2268.json T-2270.json
                                      (no T-2259.json)

    $ git show main:tickets/T-2259/ticket.md | grep '^state:'
    state: in-progress

Confirmed across two observations ~5 minutes apart, so not a transient
mid-write window.

**Not systemic -- one of two.** Of the in-progress tickets checked, T-2255 IS
leased and T-2259 is not. So the recorder works in the normal case.

**The one distinguishing detail:** T-2259's worktree history shows a `scope`
change immediately before the start transition, which the other does not:

    8 minutes ago | chore(tickets): record T-2259 start transition
    8 minutes ago | chore(tickets): scope T-2259

(git log is newest-first, so the scope change came FIRST.) That is the obvious
lead, not a proven cause -- I did not isolate the mechanism.

**Where the recording happens:** `_sync_cross_worktree_lease`
(`src/frob/tickets/_evidence.py:899`), called from `:804`:

    if to_state is TicketState.IN_PROGRESS:
        record_lease(root, ticket_id, scope)
    elif from_state is TicketState.IN_PROGRESS:
        release_lease(...)

T-2259 reached IN_PROGRESS, so that branch should have fired. Either it did not
run, or something released afterwards. Note `_start`'s own
`_auto_plan_if_queued` writes the ticket (queued -> planned) BEFORE the
IN_PROGRESS transition, so there are two writes in this window; the docstring at
`_lifecycle.py:193-211` describes that ordering being load-bearing for
`--steal`.

## Why it matters now

T-2225 (landed today) added SCOPE COLLISION detection so a ticket whose scope
files are held by another live lease reports `dispatchable: False`. That check
reads leases. An in-progress ticket with NO lease is therefore invisible to it:
`src/frob/app/agent_runner.py` and `docs/guides/agent-playbook.md` currently
read as unclaimed, and dispatching another agent onto them would collide with
live work. The coordinator avoided that only by holding dispatch for unrelated
reasons.

It also silently understates fleet concurrency: `fleet_status` reported
"5 live lease(s)" while six agents were working.

## Do NOT fix it this way

- **Do NOT have `fleet_status` or `doable` infer occupancy from ticket STATE
  instead of leases.** State and lease answer different questions -- a
  terminal-state ticket can still hold a stale lease (T-2048) and, as here, an
  in-progress one can hold none. Papering over the display leaves the lease
  store wrong for `release-lease`, the sweep, and `enforce_ticket_ownership`.
- **Do NOT make `record_lease` fire on every ticket write.** It is deliberately
  tied to the state transition; recording on unrelated writes would resurrect
  leases for terminal tickets, which is the T-2048/T-2007 class.
- **Do NOT "fix" it by having the agent re-run `frob ticket start`.** That is a
  manual workaround, and a second start against a now-foreign lease is exactly
  the `--steal` path `_lifecycle.py:193` warns about.
- **Do NOT infer the lease from the worktree directory name.** A series agent
  works several tickets from ONE worktree, so the mapping is not one-to-one.
  Read the record.

## Acceptance criteria

1. (MUST FAIL FIRST) A ticket driven to `in-progress` after a `scope` change in
   the same worktree session holds a recorded lease. Reproduce with the real
   sequence: `frob ticket scope <id> --add <path> --reason ...` then
   `frob ticket start <id>` from a linked worktree, then assert
   `.git/frob-leases/<id>.json` exists with the post-change scope.
2. The recorded scope reflects the POST-change scope, not a stale pre-change
   snapshot -- if the lease is recorded with the old scope, that is a second
   defect and should be stated.
3. MUST-STILL-PASS CONTROLS: the ordinary start path (no scope change) still
   records exactly one lease; a transition OUT of in-progress still releases
   it; and `--steal` still behaves per `_lifecycle.py:193-211`. A fix that
   records more eagerly must not resurrect leases for terminal tickets
   (T-2048's class).
4. State the actual mechanism found. "It works now" is not a diagnosis -- if
   the cause is an ordering interaction between `_auto_plan_if_queued`'s write
   and the IN_PROGRESS transition, say so.

## Scope note

`src/frob/tickets/_evidence.py` owns `_sync_cross_worktree_lease`.
`src/frob/app/ticket_runner/_lifecycle.py` owns `_start`/`_auto_plan_if_queued`
and is currently UNLEASED but is also T-2258's declared scope -- coordinate
rather than colliding if both are dispatched.

<!-- frob:no-behavior-change reason="this ticket's own audit found no defect in _sync_cross_worktree_lease/_evidence.py to fix -- both regression tests added prove the recorder already works correctly for the suspected sequence, and identify the real (different, out-of-scope) mechanism. No production code path changed." -->