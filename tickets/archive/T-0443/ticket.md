---
id: T-0443
title: 'docblocks: console/bash ''frob <subcommand>'' command-drift tier for DOC004
  (needs frob.toml-configurable command source)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_docblocks.py
- frob.toml
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0443 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: T-0443 gates work maps to docs/modules/gates.md
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_nonexistent_subcommand_is_stale
- tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_anchored_passes
- tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound
- tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_waive_suppresses_console_stale
- tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_no_config_means_no_console_checking
designated_repro_test: null
threat: null
component: null
---
