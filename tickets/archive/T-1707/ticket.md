---
id: T-1707
title: 'frob ticket land cannot land a dropped ticket: forces illegal dropped->done
  transition'
state: dropped
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_finalize.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while landing T-1683 (a `drop`-only ticket -- investigation found
its premise already resolved elsewhere, no code changed, `frob ticket
drop --reason ...` used instead of `close`).

`frob ticket land T-1683 --worktree <path> --finish` failed with:

    WARNING: tickets: T-1683 illegal transition dropped -> done
    ERROR: land: T-1683 close failed (InvalidTransition: State change not
    allowed by the state machine) after the merge already landed in the
    worktree (main untouched) -- fix evidence/Done report in <worktree>
    and retry `frob ticket land T-1683 --worktree <worktree>`, or
    `git -C <worktree> reset --hard HEAD~1` to undo the merge commit first
    ERROR: ticket land failed: CloseFailed: closing the ticket after merge
    failed

Root cause: `_finalize_and_close_ticket` (src/frob/tickets/_land_finalize.py)
unconditionally calls `_close_finalized_ticket`, which drives a DONE
transition regardless of the ticket's actual terminal state in the
worktree ledger. A ticket already `dropped` in the worktree (via `frob
ticket drop`, not `close`) cannot reach DONE from DROPPED (not a legal
transition), so land always fails for a dropped ticket -- there is no
way to land a `drop`-only disposition through `frob ticket land` today.
Retrying (as the error message itself suggests) cannot help: the ticket
state does not change between attempts, so the same InvalidTransition
recurs every time (confirmed: 3 identical failures in a row, `[REPEATED_
FAILURE]` fired).

The error message's own suggested remedies do not actually resolve
this either: "fix evidence/Done report and retry" -- evidence/Done
report were already present and correct; the failure is the DONE
transition attempt itself, not missing evidence. `git reset --hard
HEAD~1` would undo the merge commit but does not change the underlying
gap -- landing would fail identically on the next attempt.

Suggested fix: `_finalize_and_close_ticket`/`_close_finalized_ticket`
should recognize a ticket already in a terminal state (DONE or DROPPED)
in the worktree ledger and skip the forced DONE transition -- publish
the existing terminal state's ledger entry (with its evidence/Done
report/drop-reason intact) to main instead of trying to re-close it as
done.

## Drop reason
- 2026-08-06: duplicate: an agent hit the dropped->done wall independently and filed this draft; T-1701 was filed first for the same defect and has been corrected with this draft's more precise root cause (_finalize_and_close_ticket forcing the illegal transition, not _validate_closeable) (absorbed by T-1701)