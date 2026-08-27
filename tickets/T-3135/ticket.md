---
id: T-3135
title: A persistent warm sweep stage is the only shape that can make the T-1514 unscoped
  sweep stage-capable
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: confirming lease availability before start
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/tickets/_land.py
  reason: T-1514 sweep engagement for a non-rapid profile is decided in _land.py's
    disposable-stage carve-out, not _land_cmd.py; the persistent stage must be wired
    in there to satisfy T-3135's own acceptance criteria
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3127 tried to make the T-1514 pre-commit unscoped sweep run against
T-3121's disposable stage and could not, measurably. See T-3127's own
failure log for the four-arm measurement; the short version is that a
FRESHLY CUT stage can never satisfy the sweep cheaply, because every
provisioning shortcut trades one silent-unmeasurable for the next:

  bare stage                                   spawn timeout, 371.2s, None
  + root .venv symlink + copied cache.db       4 stage groups deferred, 0.9s, None
  + cache meta.root retargeted to the stage    1 group (static) deferred, 91.7s, None
  + its own warm cache, budget 480             pre-gate abort, no gate-summary, 79.5s, None
  CONTROL: the real root, same probe           MEASURED, 78 identities, 257.4s / 130.3s

The two surviving blockers are structural rather than budgetary:

1. The chunk planner's per-stage timing model has no headroom in a tree
   it has never measured, so it DEFERS groups up front -- and a deferred
   group makes the whole result `None` by T-1703's rule.
2. Native staleness aborts before the gates stage ever runs whenever the
   spawned interpreter's built natives came from a different checkout
   than the tree being checked, which is exactly what a symlinked venv
   guarantees.

Both of those are properties of a COLD, never-before-measured tree, and
both go away for a tree that is kept warm. So the shape that could work
is a PERSISTENT sweep stage rather than a per-land disposable one: one
long-lived worktree, kept at (or fast-forwarded to) main, with its own
venv, its own built natives and its own `.frob` cache maintained across
lands, into which a land's composed changeset is applied for the duration
of the sweep and then reverted. It pays the warm-up once instead of every
land, it decouples the sweep from root's state instead of symlinking to
it, and -- unlike every arm measured above -- its steady state is a tree
the chunker already has real timings for.

Not attempted here because it is a different unit of work from "hand the
existing sweep a different directory": it needs a lifecycle (creation,
staleness, reuse under concurrent lands, disposal), and getting that
wrong reintroduces exactly the silent-unmeasurable class this ticket
exists to avoid.

Acceptance: with a non-rapid profile configured, a land engages the
disposable stage AND the T-1514 sweep returns a MEASURED result about the
staged changeset -- a must-fire fixture where a genuine new unscoped error
in the staged tree refuses the land, a must-stay-quiet fixture where a
clean staged tree does not, and a third proving an unmeasurable result is
reported as unmeasurable rather than as clean.