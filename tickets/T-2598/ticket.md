---
id: T-2598
title: 'stale AFFECT001 waiver hides cycle_runner doc drift: the follow-up ticket
  its reason promised was never filed'
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- docs/modules/app.md
- src/frob/app/cycle_runner.py
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
## What happened

T-2588 changed `frob.app.cycle_runner.run`'s contract in two user-visible
ways: it now resolves the import root by walking up to the nearest
`pyproject.toml` (rather than trusting whatever directory the CLI was
pointed at), and it now sets a real exit code -- 1 on findings, 2 on an
unresolvable path, where it previously always exited 0.

`docs/modules/app.md#runners` still describes the OLD behavior. The
affects()-closure doc edge was flagged by AFFECT001, and rather than update
the doc, T-2588 waived it:

    src/frob/app/cycle_runner.py:32
    # frob:waive AFFECT001 reason="docs/modules/app.md is under T-2582's LIVE
    # cross-worktree lease for the duration of T-2588 -- cannot touch its
    # affects()-closure doc without colliding ... a doc-update follow-up
    # ticket updates the cycle_runner.run bullet's root-resolution/exit-code
    # text once that lease clears"

The lease reasoning was CORRECT at the time -- `docs/modules/app.md` was
genuinely under T-2582's live lease, and not forcing the edit was the right
call. But the promised follow-up ticket was never filed. This is it.

## Two things are now stale

1. **T-2582 is `done`.** The lease has cleared, so the waiver's stated
   justification is no longer true. A waiver whose reason has expired is
   worse than no waiver: it reads as a considered decision while actually
   suppressing a live finding nobody owns.
2. **The doc is wrong**, not merely incomplete. It describes an
   always-exit-0 command whose exit code is now load-bearing -- anyone
   wiring `frob cycle` into a hook or gate from the current docs gets it
   wrong in the silent direction.

## Fix

- Update `docs/modules/app.md#runners`' `cycle_runner.run` bullet to
  describe root resolution (nearest enclosing `pyproject.toml`, falling
  back to the git repo root) and the real exit codes (0 clean, 1 findings,
  2 unresolvable).
- REMOVE the AFFECT001 waiver at `src/frob/app/cycle_runner.py:32`. Once
  the doc is updated the finding does not exist, so the waiver must go --
  leaving it would suppress a future genuine drift on this same edge.
- Leave the ARCH103 waiver directly above it ALONE. That one is a
  standing, still-valid architectural justification about the runner's
  role, unrelated to this.

## The general point, worth stating in the Done report

A waiver reason that promises a follow-up ticket is only as good as the
ticket. Here the promise was written and the ticket was not filed, so the
only record of owed work lived inside the comment suppressing the finding
that would have surfaced it. If a waiver's reason names future work, that
work needs a ticket id in the reason at the time the waiver is written --
consider whether a check should enforce that, and file it separately if so
rather than widening this ticket.

## Positive controls, both directions

- after the fix, AFFECT001 does NOT fire for `cycle_runner.run` with the
  waiver REMOVED -- that is the proof the doc actually closed the edge,
  rather than the waiver having hidden it
- deliberately reverting the doc bullet makes AFFECT001 fire again. Without
  this case there is no evidence the detector was ever watching this edge
- the ARCH103 waiver above it still binds and still suppresses its own
  finding
