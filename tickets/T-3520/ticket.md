---
id: T-3520
title: 'INV003/INV004 WARN burn-down: 12 doc files, unbound normative claims'
state: in-progress
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
- docs/modules/ci_report.md
- docs/modules/ci_validity.md
- docs/modules/docstrings.md
- docs/modules/ghio.md
- docs/modules/tickets-data-storage.md
- docs/modules/tickets-landing.md
- docs/modules/tickets-merge-driver.md
- docs/modules/tickets-verify-sweep.md
- docs/modules/tickets.md
- docs/strata/entity_architecture.md
- docs/strata/graph.md
- docs/strata/vmodel.md
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
Remainder from T-3483's WARN family burn-down. Measured 2026-08-30 via
uv run frob check --only invariant --json, filtering severity=warning:

INV003 (exclusivity/normative claim with no bound frob:invariant marker): 12
INV004 (describes behavior but anchors zero frob:invariant markers in the
whole file): 12

Both codes fire on the SAME 12 doc files (one file, one INV003 + one
INV004 each):
  docs/modules/ci_report.md
  docs/modules/ci_validity.md
  docs/modules/docstrings.md
  docs/modules/ghio.md
  docs/modules/tickets-data-storage.md
  docs/modules/tickets-landing.md
  docs/modules/tickets-merge-driver.md
  docs/modules/tickets-verify-sweep.md
  docs/modules/tickets.md
  docs/strata/entity_architecture.md
  docs/strata/graph.md
  docs/strata/vmodel.md

Per T-2368's own review standard (do not assume a shared fix): each file
needs its own read -- either bind a real `<!-- frob:invariant INV-### -->`
marker at the code site the claim actually describes, or reword the doc
to drop the exclusivity/behavior-normative language if no such invariant
is provable today. Do not add a marker that does not correspond to a real,
checked invariant just to silence the gate. Promote INV003/INV004 WARN ->
ERROR only once both codes are at genuine (unwaived) zero across the repo.
