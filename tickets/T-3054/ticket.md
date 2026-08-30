---
id: T-3054
title: 'Land: every designed wait exceeds the 540s shell cap, so the designed worst
  case is SIGKILL mid-saga rather than clean refusal'
state: queued
kind: bug
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
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'surgical fix: extend the existing T-2913 _land_should_skip_inline_claims_reverify
    skip-under-rapid logic to also skip the expensive inline check_gates re-verification
    spawn when FROB_LAND_DEADLINE_S is declared and cannot plausibly cover it (reusing
    the SAME T-2774 estimator/pattern already used for the land-lock wait), converting
    a designed-but-oversized synchronous cost into a clean skip instead of a SIGKILL
    mid-spawn'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'surgical fix: extend the existing T-2913 _land_should_skip_inline_claims_reverify
    skip-under-rapid logic to also skip the expensive inline check_gates re-verification
    spawn when FROB_LAND_DEADLINE_S is declared and cannot plausibly cover it (reusing
    the SAME T-2774 estimator/pattern already used for the land-lock wait), converting
    a designed-but-oversized synchronous cost into a clean skip instead of a SIGKILL
    mid-spawn'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'surgical fix: extend the existing T-2913 _land_should_skip_inline_claims_reverify
    skip-under-rapid logic to also skip the expensive inline check_gates re-verification
    spawn when FROB_LAND_DEADLINE_S is declared and cannot plausibly cover it (reusing
    the SAME T-2774 estimator/pattern already used for the land-lock wait), converting
    a designed-but-oversized synchronous cost into a clean skip instead of a SIGKILL
    mid-spawn'
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
