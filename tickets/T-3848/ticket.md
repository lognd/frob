---
id: T-3848
title: 'land unwind failure is discarded: a failed merge whose unwind also fails leaves
  main half-unwound and reports the wrong error'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Found by typani 0.1's own linter (rule TYP003, discarded Result) run over frob
0.530.0 src/, reported as typani FROBLEMS T-013. VERIFIED against the source
2026-09-05.

src/frob/tickets/_land.py:2216

    merged_finalized, own_commits = _land_plan_merge_and_finalize(root, worktree)
    if merged_finalized.is_err:
        _land_plan_unwind_after_merge(root, pre_merge_sha, own_commits, dry_run=dry_run)
        return Err(merged_finalized.danger_err)

`_land_plan_unwind_after_merge` returns a `Result` (its signature is at
_land.py:2101). Here the return value is DISCARDED.

WHAT THAT MEANS CONCRETELY. This is the failure path of a land: the merge or
finalize step already failed, and the unwind is the compensating action that
puts main back where it was. If the UNWIND ITSELF FAILS, that error is thrown
away and the caller receives only the ORIGINAL merge error. So main is left
HALF-UNWOUND, and the error message names the merge failure rather than the
unwind failure that actually determines the repository's state. The operator is
told the wrong thing about the wrong step, at the moment the repo is in its
least consistent state.

THE STRONGEST EVIDENCE THAT THIS IS AN OVERSIGHT, NOT A CHOICE: the SAME
function is handled correctly 33 lines earlier.

    _land.py:2183   return _land_plan_unwind_after_merge(
    _land.py:2216   _land_plan_unwind_after_merge(...)      <- discarded

One call site propagates, the other drops it. If the discard were deliberate
there would be a comment saying why, as there is elsewhere in this file for the
T-1522 vs T-2189 unwind policy.

WHY THIS RANKS ABOVE THE OTHER TWO DISCARDS TYP003 FOUND. The land path is the
most safety-critical code in this repo -- it is the only thing that mutates
main -- and this specific discard is on the error path, which is by definition
the path that runs when something has already gone wrong. A silent failure
there is compounding: the first failure is reported, the second is invisible,
and the repository state reflects the second.

DO NOT "FIX" THIS BY JUST PROPAGATING THE UNWIND ERROR AND DROPPING THE MERGE
ERROR. Both errors matter and they mean different things: the merge error says
why the land failed, the unwind error says what state main is in now. Decide how
to surface both -- an error that carries the original as context, a logged
CRITICAL for the unwind plus the propagated merge error, or a distinct
error type meaning "land failed AND cleanup failed, main may be inconsistent".
The third is probably right because it is the only one an automated caller can
branch on, but state the reasoning.

CHECK THE SIBLING PATHS IN THE SAME FUNCTION while you are here. Line 2220's
`_land_plan_tick_gate_dirty` assigns its result to `unwound` -- confirm that one
is actually inspected and not just bound to a name. Enumerate every compensating
/ cleanup call on a land failure path and report which propagate and which do
not. That enumeration is worth more than the single-line fix.

MUST-FIRE FIXTURE:   a land whose merge fails AND whose unwind then fails
                     surfaces the unwind failure, not only the merge failure,
                     and says main may be inconsistent.
MUST-STAY-QUIET:     a land whose merge fails and whose unwind SUCCEEDS still
                     reports exactly the merge error, unchanged.

ACCEPTANCE
- The both-errors surfacing decision stated with reasoning.
- The enumeration of cleanup calls on land failure paths, with a verdict each.
- Both fixtures committed. The must-fire one needs a real injected unwind
  failure, not a mocked-out assertion that the return value is read.
