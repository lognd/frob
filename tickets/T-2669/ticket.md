---
id: T-2669
title: rapid-profile land fails to commit its own rapid-debt.jsonl, dirtying the shared
  root and DirtyMain-blocking the fleet (70x today)
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

    git log --since="20 hours ago" | grep -icE "rapid-debt|deferred post-land sweep"
    -> 70

Seventy hand-commits in one day, with messages like the land's own
suggested text:

    chore: commit rapid-debt.jsonl (land-side commit failed)
    chore(rapid): record T-2620's deferred post-land sweep

The land itself emits the diagnosis and the remedy:

    ERROR: rapid sweep: T-XXXX could not commit rapid-debt.jsonl in
    /home/logan/projects/frob -- root is now DIRTY and the next land from
    any agent will refuse with DirtyMain; commit it by hand

One agent hit it on two consecutive lands and reported it looks systemic to
the rapid-profile land path rather than incidental. The commit count agrees.

## Why this is expensive out of proportion to its size

`rapid-debt.jsonl` is the land pipeline's OWN machinery file. When the
land-side commit of it fails, the shared root is left dirty, and a dirty
root makes `frob ticket land` refuse with DirtyMain for EVERY other agent
in the fleet. So a failure in the land's own bookkeeping blocks unrelated
agents' work until a human or the coordinator commits it by hand.

Observed costs today, all repeated many times over:
- agents pausing mid-series to diagnose a dirty root that was not theirs
- agents committing another ticket's sweep record to unblock themselves,
  which is correct but means routine hand-edits to the shared root
- the coordinator doing the same, repeatedly, as an interrupt

It also trains exactly the wrong reflex. "Root is dirty, commit it" is
correct for THIS file and dangerous in general -- a live land stages its
merge in the root, and committing that mid-flight would corrupt it. A
papercut that fires seventy times a day teaches people to reach for a
command that is wrong in a neighbouring case.

## Investigate before fixing

Determine WHY the land-side commit fails. Candidates worth checking, not
assumptions:
- a pre-commit hook refusing non-ledger writes in the root without
  `FROB_LAND_INTERNAL=1` (agents reported needing exactly that env var to
  commit it by hand, which points here)
- lock contention with a concurrent land or a detached sweep child
- the detached post-land sweep child racing the parent land's own commit

The fix is whatever makes the land commit its own machinery file reliably.
If the pre-commit hook is the cause, the land path should be setting the
same internal flag agents are told to set by hand -- that is a one-line
class of fix, and the fact that the error message TELLS the operator to use
`FROB_LAND_INTERNAL=1` is strong evidence the land itself should have.

## Do NOT

- Do NOT make the sweep skip writing `rapid-debt.jsonl`. That record is the
  deferred-verification debt ledger; dropping it would be a silent zero.
- Do NOT add `rapid-debt.jsonl` to `.gitignore`. It is tracked on purpose
  and carries `merge=union` in `.gitattributes`.
- Do NOT weaken the DirtyMain guard. It is correct and has caught real
  problems today, including an agent editing the shared root by mistake.

## Positive controls, both directions

- a land under the rapid profile commits `rapid-debt.jsonl` itself and
  leaves the root CLEAN, verified across several consecutive lands
- the DirtyMain guard still fires for genuinely unexpected root content --
  e.g. an untracked file, or an edit to a source file the land does not own.
  Without this the fix is indistinguishable from disabling the guard
- the sweep record is still WRITTEN, with the same content it has today;
  verify by diffing a record produced before and after the fix
