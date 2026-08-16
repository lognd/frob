---
id: T-2225
title: fleet_status --ticket reports dispatchable=True when the ticket's SCOPE FILES
  are held by another agent's live lease (two mis-dispatches measured)
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
blocked_by:
- T-2222
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: '--ticket on a ticket whose scope files are held by another live lease reports
    the collision and names the holding ticket (fails today: prints lease=none, dispatchable=True)'
  evidence: []
- text: A glob scope entry colliding only after expansion is detected (src/frob/**
    vs a live lease on src/frob/tickets/_land.py) -- resolved paths, never string
    comparison
  evidence: []
- text: A ticket with no colliding lease MUST STILL report dispatchable (must-still-pass
    control against flagging everything)
  evidence: []
- text: A reclaimable or residual lease does not count as a collision -- reuse T-2222's
    classification, do not re-implement it
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# `fleet_status --ticket` reports "dispatchable: True" for a ticket whose scope files are held by another agent's live lease

## Measured evidence (2026-08-16)

Dispatched T-2217 and T-2220 to an agent. Both were immediately unworkable:

- **T-2217** needs `src/frob/app/config.py` -> `ScopeLeaseConflict`, held by a
  LIVE T-2221 lease (`.claude/worktrees/t-2221`, real commits, not stale).
- **T-2220** needs `src/frob/tickets/_land.py` -> `frob ticket work` refused,
  held by a LIVE T-2215 lease. That is the exact function region
  (`merge_commit`, `_land.py:1383-1384`) the fix must edit, so this is a real
  content collision, not merely a ledger one.

The pre-dispatch readiness check reported, for both:

    lease: none
    dispatchable: True

Which is TRUE as written and useless as advice. It answers "does this ticket
hold a lease?" -- the question a coordinator asks is "can an agent start this
right now?" Those differ exactly when another ticket leases the files.

The agent burned a full startup, a premise check, and two refused
`scope`/`work` attempts before reporting back, on two tickets that could not
have been started. That is the cost per mis-dispatch.

## Why the existing tooling did not prevent it

`frob ticket wave --agents N` exists and groups scope-disjoint tickets. The
operating notes already say to use it. It was not used -- so the rule exists
and did not fire. Per the standing audit duty, a rule that was not followed is
not the fix; the check must live where the dispatch decision is actually made,
which is `fleet_status --ticket`.

## Do NOT fix it this way

- **Do NOT tell the coordinator to remember `frob ticket wave`.** That is the
  rule that already failed. The readiness command must answer the question.
- **Do NOT compare scopes as strings.** Scope entries are globs
  (`src/frob/**`); a live lease on `src/frob/tickets/_land.py` collides with
  it, and no substring comparison of those two texts reports that. Expand
  globs and compare resolved PATHS. Standing directive: token/grammar, never
  lexical.
- **Do NOT key the collision on the ticket id or the worktree directory
  NAME.** A series agent works several tickets from ONE worktree, so
  `T-2203`'s lease legitimately pointed at `t2201-series`. Read each lease
  record's own fields.
- **Do NOT make it refuse or auto-release.** This is a REPORTING fix. The
  authoritative refusal already exists and works correctly -- `frob ticket
  work` and `frob ticket scope` both refused properly here. This only surfaces
  that verdict BEFORE an agent is spawned instead of after.

## Acceptance criteria

1. (MUST FAIL FIRST) `--ticket T-####` on a ticket whose scope files are held
   by another ticket's live lease reports the collision and names the holding
   ticket. Fails today: it prints `lease: none` / `dispatchable: True`.
   Confirm `--check-repro` reads FAILED_AT_PARENT before the fix commit.
2. A glob scope entry that collides only after expansion is detected -- e.g.
   scope `src/frob/**` vs a live lease on `src/frob/tickets/_land.py`.
3. A ticket with NO colliding lease MUST STILL report dispatchable
   (must-still-pass control). A change that flags everything as colliding
   would satisfy 1-2 and stop all dispatch.
4. A lease that is itself reclaimable/residual does NOT count as a collision
   (this is why it is blocked_by T-2222, which establishes live-vs-reclaimable
   classification -- reuse that, do not re-implement it).

## Scope note

Blocked on T-2222 deliberately: both edit `scripts/fleet_status.py`, and
T-2222 builds the live-vs-reclaimable lease classification this needs. Filing
them as concurrent tickets would reproduce the exact collision this ticket is
about.
