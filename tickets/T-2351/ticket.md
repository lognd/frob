---
id: T-2351
title: frob ticket land's pre-land WIP-commit path silently discards uncommitted in-scope
  edits (T-2328 follow-up, narrower root cause)
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Narrower, coordinator-confirmed root cause for the class of defect T-2328
was originally filed against. T-2328 itself fixed a REAL, reproduced bug
(a stale declared-scope read in the Tier-A auto-fix scope/lease filter,
frob.gates._fix_engine_scope._other_ticket_holding_live_lease, landed as
d0e6b5644e11c782859fb39431becd9cfc60f4a3) but three further
reproductions (T-2194, a repeat on T-2329, and a discriminating case on
T-2323) now show that fix does not close the original T-2194 incident:

    T-2194  design/frob.strata grant, uncommitted at land time -> dropped
    T-2329  re-apply of the same grant, uncommitted            -> dropped again
    T-2323  same edit, git-committed in the worktree FIRST     -> SURVIVED

The discriminating experiment is the third case: `frob ticket land`'s
pre-land WIP-commit handling discards UNCOMMITTED working-tree state for
an in-scope file, but never touches a real commit already on the
ticket's own branch. This is a land-path bug independent of the
scope/lease read T-2328 already fixed -- it reproduces even when the
lease/scope check would correctly classify the file as in-scope and not
under any live lease.

WANTED:
1. Root-cause the pre-land WIP-commit path in src/frob/tickets/_land.py
   (and/or src/frob/app/ticket_runner/_land_cmd.py) that captures
   worktree changes into the "wip: pre-land snapshot" commit: find where
   an in-scope file's uncommitted edit can be dropped rather than
   captured.
2. Fix it so a file in the ticket's own declared scope ALWAYS reaches
   the land commit, whether it was committed by the agent beforehand or
   left as an uncommitted working-tree edit at land time -- OR, if that
   path genuinely cannot safely capture certain uncommitted state,
   REFUSE the land loudly (never silently discard) rather than reporting
   verified=True over lost content.

Positive controls required (non-negotiable, per the T-2328 dispatch):
(1) a file in the declared scope always reaches the land commit; (2)
must-still-pass: a file genuinely OUTSIDE the declared scope is still
excluded -- do not "fix" this by landing everything; (3) reproduce
against a REAL uncommitted in-scope edit (a pre-committed one already
survives and would be a false-green repro, per the T-2323 discriminating
case above).

CAUTION at dispatch time: src/frob/app/ticket_runner/_land_cmd.py may be
under another ticket's live lease -- check read-only before starting;
src/frob/tickets/_land.py may be the freer half. If the needed file is
locked, report and stop rather than forcing it.

Filed as the direct, coordinator-identified follow-up to T-2328 (which
fixed a real but INSUFFICIENT root cause -- the actual mechanism is the
WIP-commit path, not the scope/lease read). Two investigation notes
referenced by the coordinator are said to be attached to T-2328 itself;
read those before starting, this ticket does not duplicate their
content.
