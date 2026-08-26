---
id: T-2950
title: 'frob status takes 5m41s: an adoption surface nobody will wait for, and it
  exceeds the 200s foreground budget'
state: in-progress
kind: ux
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/status_runner.py
- src/frob/tickets/*ticket_flow*
- tests/test_status.py
- docs/modules/cli.md
- src/frob/app/config.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/status_runner.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/*ticket_flow*
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_status.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/cli.md
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/status_runner.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/*ticket_flow*
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_status.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/cli.md
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/config.py
  reason: CLI-flag forwarding for --tickets/status_tickets requires touching AppConfig
    and its external-forwarding field list
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/_config_external.py
  reason: CLI-flag forwarding for --tickets/status_tickets requires touching AppConfig
    and its external-forwarding field list
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
