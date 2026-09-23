---
id: T-5376
title: 'ARCH001 self-check fails: fleet_status._ticket_readiness_lines redundant with
  test-side declaration (T-4710)'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_fleet_status_ticket_readiness_arch001.py
- src/frob/app/fleet_status.py
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
CI run 35819358270 (ubuntu/macos/windows, dev 7d7e0ae4d4); re-verified on dev tip 39b89ed091: tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding fails -- frob-arch reports fleet_status.py::_ticket_readiness_lines as redundant with an existing test-side declaration (T-4710 remnant), tripping ARCH001 on frob's own repo. Not covered by any open ticket I could find; filed fresh per T-4758-style sweep.