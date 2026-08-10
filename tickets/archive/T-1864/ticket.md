---
id: T-1864
title: 'post-land sweep regression from T-1843: 2 new error(s) (DOCENUM001, E501)'
state: dropped
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- src/frob/gates/_policy_weakening_gate.py
- docs/strata/policy.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_policy_weakening_gate.py
  reason: sweep filed an absolute-path scope entry that never matches from a worktree
    checkout; add the correct worktree-relative path for the same file
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: /home/logan/projects/frob/src/frob/gates/_policy_weakening_gate.py
  reason: absolute path from root checkout never matches worktree-relative scope checks;
    superseded by relative path added above
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/policy.md
  reason: 'AFFECT001: policy_weakening_gate''s affects()-closure doc is docs/strata/policy.md#refinement-monotonicity-inv-051-t-1482;
    touching the gate function requires touching this anchor in the same diff'
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1843 at commit cb1cc57f5589d6ffe9ace4563a249265e8e4a145 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- DOCENUM001  docs/modules/gates.md
- E501  /home/logan/projects/frob/src/frob/gates/_policy_weakening_gate.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOCENUM001  docs/modules/gates.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/gates/_policy_weakening_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-08: Both findings already resolved on main before this drop: DOCENUM001 was fixed by two independent commits -- my own 44a1ef61f563d16799d608d827b4a00febe79d52 (bundled with T-1839's land: added INV051 to the frob:enumerates member list + a matching table row) and the coordinator-confirmed 848917622149bb69716a86d90116c9ff48a33131 (T-1842, WAIVE008 member list repair); E501 was fixed in the same 44a1ef61f commit (wrapped the Module(...) call in _policy_weakening_gate.py). 'uv run frob check --ticket T-1864 --json' on the current merged worktree tree shows zero severity=error diagnostics of any code. My earlier done-report on this ticket predates confirming main already carried the fix through T-1839's land; this ticket itself was never separately worked to closure, so drop (not close) is correct.