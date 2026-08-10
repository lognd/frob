---
id: T-2076
title: check_gates() land-time spawn reads root's PRE-land tree, not the merged tree
  (T-2064 confirmed)
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
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2064 confirmed by live instrumentation (root-tip probe in `_land_locked`,
see T-2064's own ticket body for the log line) that `check_gates()`'s
land-time spawn (`_shared_check_spawn_fn(root, ...)`, cwd=root) evaluates
root's PRE-land tree, not the merged tree -- because it is triggered from
`_reverify_done_report_claims_post_merge` inside `_land_locked`, which runs
BEFORE `_land_squash_apply` (the module's own documented "ONLY step that
mutates root"). The T-0754 ClaimDivergence check is therefore not checking
what its own docstring in `_verify.py` claims it checks ("always runs
against a FRESHLY MERGED tree").

Independent corroboration: T-1584's Done report claimed a clean
`--land-parity` (0 unscoped errors), yet a throwaway detached worktree at
T-1584's own landed commit (99ecae11dff1) shows 3 DOC005 + 6 SELFAUDIT001
findings deterministically. A pre-land-tree read at land time explains the
gap directly -- this is a silent, general escape hatch for every land whose
Done report captures a gate-state claim, not a one-off bad report.

Needs a real fix, spanning both `src/frob/tickets/_land.py` (the trigger
ordering inside `_land_locked`) and `src/frob/app/ticket_runner/_verify.py`
(`_shared_check_spawn_fn`'s own contract/docstring) -- out of a single-file
`_land.py`-scoped ticket's reach, and needs a decision on how the T-0754
staleness guarantee is preserved across the reorder (moving the spawn to
run after `_land_squash_apply` means it now checks the SQUASHED commit,
which may need its own care around dry-run unwind semantics). Not a
mechanical fix -- read T-2064's full body and `_shared_check_spawn_fn`'s
docstring before starting.
