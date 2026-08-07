---
id: T-0022
title: 'Polyglot monorepo check: per-subtree stage detection, frob.toml [check] scoping,
  TypeScript stage (tsc/eslint)'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ts_parsers.py::TestParseTsc::test_clean_output
designated_repro_test: null
threat: null
component: null
---
