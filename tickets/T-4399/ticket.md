---
id: T-4399
title: 'DRIFT002 on src/frob/gates/_tickets_gate.py: the acked doc digest moved when
  T-4393 introduced the _utc_today seam; re-read the doc section and ack'
state: in-progress
kind: docs
origin: human
created: '2026-09-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- docs/modules/gates.md
- docs/modules/tickets-lifecycle.md
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/*.md
  reason: narrow to the three doc files that mention TICK004 severity
  actor: logan
  at: '2026-09-10'
- op: add
  glob: docs/modules/gates.md
  reason: narrow to the three doc files that mention TICK004 severity
  actor: logan
  at: '2026-09-10'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: narrow to the three doc files that mention TICK004 severity
  actor: logan
  at: '2026-09-10'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: narrow to the three doc files that mention TICK004 severity
  actor: logan
  at: '2026-09-10'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found by the post-land verify sweep after T-4393 landed (c5b3ffeb3); quarantined and disposed by the coordinator on 2026-09-10 with --file-ticket pointing at T-4393. The TICK004 fix replaced date.today() with an injectable _utc_today() and the acked doc section describing TICK004 severity now has a stale digest. Re-read the section, update the prose to say severity is computed from the UTC date, then frob ack the ref. Do not ack without reading.