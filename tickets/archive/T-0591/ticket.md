---
id: T-0591
title: 'TEST-family pool triage: bucket + calibrate + disposition the 335 warn findings'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/**
- src/frob/registry/**
- src/frob/graph/**
- src/frob/lang/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/registry/**
  reason: TEST014/TEST003 disposition touches per-symbol frob:tests/waivers in producing
    modules, not only gates/tests
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/graph/**
  reason: TEST014/TEST003 disposition touches per-symbol frob:tests/waivers in producing
    modules, not only gates/tests
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/lang/**
  reason: TEST014/TEST003 disposition touches per-symbol frob:tests/waivers in producing
    modules, not only gates/tests
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_registry_models.py::TestParseDisposition::test_handled_by
designated_repro_test: null
threat: null
component: null
---
Triage the TEST-family warning pool per mission: bucket by rule (TEST005/012/013/014/015), calibrate detectors where a noise class dominates, disposition genuine findings. Companion to T-0583 (memoize_per_run wrapper opacity fix).