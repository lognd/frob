---
id: T-2318
title: 'T-1238 epic ledger state is stale: reads queued but all tracked slices (T-1271
  explore, T-1567..T-1571) are already done'
state: done
kind: docs
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-1238/**
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 69fd92288e201ccf5f944d97b6f36dc60dd7ac2c
---
Found while working T-2288 (recovery of three branches `frob ticket reconcile`
misattributed as stranded work under T-1238).

T-1238's `tickets/T-1238/ticket.md` on main still reads `state: queued`,
but every real deliverable it tracks is already done:

- Its own acceptance[1] (the `frob explore` first slice: un-deprecating
  map/outline/xref/docs, `docs/design/cli-regrouping.md`) landed under a
  DIFFERENT ticket id, T-1271 (commit bb7f37766), not under T-1238 itself.
  Commit 532799aca ("feat(cli): frob explore verb group + regrouping
  design (T-1238)") on the stale `t-1238`-adjacent branch investigated by
  T-2288 is NOT an ancestor of main and is superseded by T-1271's landed
  content -- verified: `frob explore --help` on main already lists
  map/outline/xref/docs-search.
- Its acceptance[0] (help-surface rework across every other verb group)
  was explicitly deferred to five child tickets (T-1567 quality group,
  T-1568 design group, T-1569 ops group, T-1570 ticket/debt/deprecated
  naming, T-1571 help-surface rework) -- all five are `state: done` on
  main today (verified via `frob ticket show`).

So the epic's own tracked work is complete, but the epic ticket itself
was never transitioned to reflect it -- likely because T-1238's actual
close attempt happened on the now-stale/superseded branch and was never
re-applied to main after T-1271 landed the same slice under its own id.

Fix: reconcile T-1238's ledger state on main (via `frob ticket start` +
`frob ticket close`, or whatever the epic-tier closure convention is) so
`state:` matches reality -- done, with a Done report citing T-1271 (not
532799aca) as the acceptance[1] evidence and T-1567..T-1571 as the
acceptance[0] evidence. Scope this narrowly to `tickets/T-1238/**` (a
ledger-only change) to avoid colliding with T-1238's own broad epic-tier
scope declaration.