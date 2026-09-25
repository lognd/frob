---
id: T-draft-8dc841a4
title: 'land: run ty/pre-checks on the merged tree, not the stale worktree tip; retire
  dead landing markers'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: high
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_queue.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/tickets/test_land_premerge_checks.py
- docs/modules/tickets-landing.md
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
Measured 2026-09-25 (drain log for T-5785, worktree t-draft-90b33f19):
the land's ty pre-check runs against the WORKTREE's own tip ("checked
against the WORKTREE ... at commit 4f4cca52") BEFORE the merge of dev,
so a worktree enqueued hours earlier fails on symbols that dev has
since added to a native stub:

  ty check found 1 NEW error(s) in this ticket's own touched file(s):
  src/frob/gates/_strata_milestone_closure.py:168:25 unresolved-attribute
  Module `strata_core` has no member `milestone_closure_check`

The T-1213 auto-rebuild ran and "succeeded" first, which proves the
compiled native was not the problem: the worktree's strata_core.pyi stub
(and the source file the finding names) predate dev. T-draft-42b1e188
(landed) fixed ordering vs the natives rebuild; this is the remaining
half. Same refusal hit T-5469 and T-5366 earlier the same night; every
queued worktree older than the stub change fails the same way, and the
coordinator had to run a merge-dev hygiene pass over every queued
worktree by hand (scratchpad hygiene-queued.sh).

Second finding in the same log: after that refusal the drain process
EXITED with rc=0 leaving T-5785 in status `landing` with a dead pid, so
the entry could neither be re-enqueued ("already has a queued/landing
entry") nor picked up by the next drain -- the T-5637 stale-marker shape
again, this time on a refusal path, not a duplicate key.

Deliver:
1. In `--drain` (and single land), merge `dev` into the worktree (or
   compute the merge preview) BEFORE the ty/Tier-A/scope pre-checks, so
   they measure the tree that would actually land. If the merge
   conflicts, refuse with the conflict list (a real reason), not a
   phantom type error.
2. On ANY refusal or exception, the drain must set the entry to `failed`
   with the reason before moving on or exiting; a `landing` entry whose
   pid is dead is reported by `frob coord status` as stale and retired
   automatically on the next drain start (guaranteed safe: the pid is
   gone).
3. Positive control: a queued worktree whose tip lacks a stub symbol dev
   has; without the fix the land refuses on ty, with it the land passes;
   and a drain that is killed mid-land leaves no `landing` marker after
   the next drain starts.
