---
id: T-4523
title: 'scaffold pool warm/lease/status have zero references anywhere: confirm dead
  or document, then delete or document'
state: done
kind: ux
origin: agent
created: '2026-09-16'
priority: low
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_core.py
- src/frob/scaffold/_pool.py
- docs/commands/scaffold.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip
designated_repro_test: null
acceptance:
- text: GIVEN the three leaves WHEN traced to callers (git grep, docs, hooks, CI)
    THEN each is either deleted with its runner or documented with one usage example
    in docs/commands/scaffold.md
  evidence:
  - tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16: scaffold pool has 27 doc refs but its leaves warm/lease/status have 0 references in docs/, .claude/, tickets/, CHANGELOG and commit subjects since 2026-07-01 (_populate_scaffold_actions in src/frob/_cli_parsers/_core.py).