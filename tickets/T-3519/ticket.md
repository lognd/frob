---
id: T-3519
title: 'NEGEXIST001 WARN burn-down: 18 unbound negative-existence claims'
state: queued
kind: docs
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-landing.md
- docs/commands/sys.md
- docs/guides/coordinator-scripts.md
- docs/modules/tickets-verify-sweep.md
- docs/design/macos-portability.md
- docs/modules/process.md
- docs/modules/testing.md
- docs/strata/entity_architecture.md
- docs/strata/reliability.md
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: collides with in-progress T-3492's lease; drop from this burn-down, NEGEXIST001
    finding there stays unaddressed for now
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: docs/modules/lang.md
  reason: collides with in-progress T-3492's lease; drop from this burn-down
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Remainder from T-3483's WARN family burn-down. Measured 2026-08-30 via
uv run frob check --only docblocks --json, filtering severity=warning:

NEGEXIST001 (frob:until-bound negative-existence claim, T-1229): 18 findings
  docs/modules/tickets-landing.md: 4
  docs/commands/sys.md: 2
  docs/guides/coordinator-scripts.md: 2
  docs/modules/tickets-verify-sweep.md: 2
  docs/design/macos-portability.md: 1
  docs/modules/gates.md: 1
  docs/modules/lang.md: 1
  docs/modules/process.md: 1
  docs/modules/testing.md: 1
  docs/strata/entity_architecture.md: 1
  docs/strata/reliability.md: 1
  docs/strata/surface.md: 1

Per T-2368's own review standard (do not assume a shared fix), each file
needs its own read: read docs/modules/gates.md's NEGEXIST001 section for
the exact claim shape it flags (a negative-existence claim -- "nothing
does X", "X never happens" -- with no `frob:until` bound naming what
would falsify it), then either bind a real `frob:until` condition, or
reword to drop the unbounded negative claim if none is provable today.
Do not add a placeholder bound just to silence the gate. Promote
NEGEXIST001 WARN -> ERROR only once it is at genuine (unwaived) zero.
