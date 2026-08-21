---
id: T-2779
title: agent-playbook documents a superseded landing rule that stranded four agents
  and permitted the concurrent-land kill
state: done
kind: docs
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:grep -n wait_for_land_slot.py docs/guides/agent-playbook.md exit=0 sha256=4b77a4fcc956
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: dbff5b288334606c080de7079711b8c5f580e901
---
## Problem

`docs/guides/agent-playbook.md` documents a landing precondition that is now
wrong in both directions, and agents follow it literally.

Line 141 and line 1232 both state the threshold as "FEWER THAN 2 lands in
flight, not zero". Measured consequences on 2026-08-20/21:

- Read as "wait for the fleet to go quiet", four agents parked on a Monitor
  that never fired, stranding committed work in their worktrees.
- Read literally, it permits a second concurrent land. Before T-2774 the
  loser of the lock race burned its entire `timeout 540` budget waiting and
  was SIGKILLed having produced nothing. T-2753, T-2762 and T-2359's early
  land attempts all died this way -- no commit, ticket stranded
  `in-progress`, no diagnostic beyond exit 143. T-2762 then succeeded
  UNCHANGED on a retry that ran alone, which is the proof.

The guidance also predates two things that now exist and supersede it.

## What is now true

`scripts/wait_for_land_slot.py` (T-2775) is the shared primitive. It is quiet
by default (one summary line), reuses `fleet_status.py`'s own definition of a
land rather than a second one, and returns three DISTINCT documented exit
codes: 0 slot free, 1 timed out, 2 could-not-measure. Exit 2 must never be
treated as a free slot -- that is the silent-zero failure the script exists
to prevent. It takes `--max-in-flight` and `--timeout`.

`FROB_LAND_DEADLINE_S` (T-2774) bounds the lock wait as
`min(_LAND_LOCK_TIMEOUT_S, deadline - estimated_work_s)`, where
estimated_work_s comes from `_derive_post_land_sweep_budget_s`. Measured on
this repo: estimated_work_s = 300, so a declared deadline of 540 yields a
240s wait ceiling. A land that cannot finish now returns a clean typed
`Err(LandError.LandLockTimeout)` immediately instead of dying mid-work.
Absent the env var, behavior is unchanged.

Together these make bounded concurrency safe, which the old text could not
express because neither existed when it was written.

## Required change

Replace the rule at both sites (and anywhere else it appears -- grep, do not
assume two) with the current procedure:

    export FROB_LAND_DEADLINE_S=540
    uv run python scripts/wait_for_land_slot.py --max-in-flight 1 --timeout 480
    # land only on exit 0
    timeout 540 uv run frob ticket land <ticket> --worktree <wt>

State explicitly, because agents have gotten each of these wrong:
- exit 2 is UNMEASURED and must be retried, never read as a free slot
- a "declined-early ... NOT a died-mid-land timeout" Err is CORRECT; retry,
  the worktree work is intact
- do NOT hand-roll a poll loop; a hand-rolled loop that echoes per tick is a
  real context cost, and one that ignores exit code turns a failed probe
  into a fake zero
- never park on a Monitor waiting for a land slot -- nothing wakes you and
  the work strands
- the deadline guard bounds the WAIT, not your own work; an oversized diff
  can still hit the cap, so batch large changes

Also correct `docs/guides/agent-playbook.md:969`, which still instructs
agents to register the `frob ticket merge-driver` once per clone. That
predates the ledger v2 migration and now contradicts `.gitattributes`
(T-1258/T-2356 retired it for this repo); an agent following it today
re-enables retired machinery.

## Verification

This is a docs change, so the control is that the documented commands
actually work as described. Run each one and confirm: the script's three
exit codes are reachable (use `--fleet-status-cmd false` to force exit 2),
and `FROB_LAND_DEADLINE_S` absent vs set produces the two documented
behaviors. Do not document a flag without running it -- a command that
exists but does not work on a real input has shipped in this repo before.