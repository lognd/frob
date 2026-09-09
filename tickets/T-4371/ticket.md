---
id: T-4371
title: 'WIRE001 false-positive: test-helper-calling-test-helper chains not recognized
  as wired'
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow to actual gate
  actor: logan
  at: '2026-09-09'
- op: add
  glob: src/frob/gates/_wire.py
  reason: narrow to the WIRE001 detector itself
  actor: logan
  at: '2026-09-09'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4365: WIRE001 flags _write_fake_posix_tool/_fake_required_toolchain_path in tests/system/test_cli_doctor.py as unwired even though they are called transitively by real tests (helper -> helper -> test, two hops) in the same file. Consider whether WIRE001's caller-search should follow indirect chains within the same test file before requiring a waiver.