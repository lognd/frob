---
id: T-2913
title: Rapid land still runs a full inline frob check on the land critical path, serialized
  under land.lock
state: queued
kind: bug
origin: human
created: '2026-08-25'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/tickets/_land.py
- tests/unit/test_ticket_runner_gate_findings.py
- tests/test_ticket_land.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'T-2913: skip the inline post-merge full frob-check ClaimDivergence reverification
    under rapid profile (the ~144-209s critical-path cost); defer to the already-existing
    T-1684 post-land sweep + T-1690 attribution + quarantine pipeline, which already
    runs unconditionally under rapid regardless of check_gates'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-2913: skip the inline post-merge full frob-check ClaimDivergence reverification
    under rapid profile (the ~144-209s critical-path cost); defer to the already-existing
    T-1684 post-land sweep + T-1690 attribution + quarantine pipeline, which already
    runs unconditionally under rapid regardless of check_gates'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'T-2913: skip the inline post-merge full frob-check ClaimDivergence reverification
    under rapid profile (the ~144-209s critical-path cost); defer to the already-existing
    T-1684 post-land sweep + T-1690 attribution + quarantine pipeline, which already
    runs unconditionally under rapid regardless of check_gates'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2913: skip the inline post-merge full frob-check ClaimDivergence reverification
    under rapid profile (the ~144-209s critical-path cost); defer to the already-existing
    T-1684 post-land sweep + T-1690 attribution + quarantine pipeline, which already
    runs unconditionally under rapid regardless of check_gates'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-2913: touched symbols in _verify.py/_land.py doc into tickets-landing.md'
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
