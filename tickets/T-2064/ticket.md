---
id: T-2064
title: Confirm whether check_gates()'s land-time spawn (cwd=root) actually sees the
  merged tree, or root's stale pre-land state
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Surfaced while measuring T-2055 (_land_gate_claims_fn's spawn cost), NOT
confirmed by live instrumentation -- needs dedicated verification before
being treated as a real defect.

In src/frob/tickets/_land.py's `_land_locked`, the ordering is:

1. merge/finalize happen in `worktree` only
2. `claims_check = _reverify_done_report_claims_post_merge(worktree,
   ticket_id, passing_ids, check_gates, check_gate_findings)` runs --
   `check_gates`/`check_gate_findings` are zero-arg closures built earlier
   by the CLI (`_check_gates_summary_fn(root, ticket_id, ...)`,
   `_land_cmd.py:3355`) that spawn `frob check` with `cwd=root`, NOT
   `cwd=worktree`.
3. `check_gate_claims(reloaded)` runs next, spawning `frob check --only
   gates` with `cwd=worktree` (T-2055's own measured second spawn).
4. `_land_finalize_and_close` runs.
5. `_land_squash_apply(root, worktree, ...)` runs -- an inline comment a
   few lines above this call in `_land.py` names it explicitly as "the
   ONLY step that mutates root".

If that comment is literally true, step 2's `check_gates()` spawn (cwd=
root) runs BEFORE anything in this land has touched `root`'s own working
tree/branch at all -- meaning it evaluates `root`'s PRE-land state, not
the "just-merged tree" its own docstring in `_verify.py`'s
`_shared_check_spawn_fn` describes. If true, the T-0754 ClaimDivergence
check may not actually be checking what it claims to check, which would
be a significant, independently-discovered defect (or the comment/my
reading is wrong and something else keeps `root` in sync -- also worth
confirming).

This needs live instrumentation (a temporary log line recording `git rev-
parse HEAD` in `root` immediately before the `check_gates()` spawn during
a real land, or an equivalent test) to confirm or refute, not more
static reading -- filed rather than asserted as fact.
