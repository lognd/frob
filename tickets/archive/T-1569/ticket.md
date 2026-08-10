---
id: T-1569
title: 'cli regrouping: frob ops verb group (release/natives/doctor/clean/fleet/deploy/scaffold/gitlog/stats)'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1725
- T-1764
- T-1765
- T-1766
parent: T-1238
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_ops.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/_cli_parsers/__init__.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/app.py
- src/frob/app/ops_runner.py
- docs/modules/cli.md
- docs/design/cli-regrouping.md
- docs/modules/app.md
- README.md
- tests/unit/test_app_runners.py
- tickets/T-1569/**
- docs/commands/scaffold.md
- docs/guides/install.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ops.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/__main__.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/app.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ops_runner.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: README.md
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1569/**
  reason: narrow mega-glob to the exact files T-1569 (ops verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/commands/scaffold.md
  reason: 'AFFECT001: _add_scaffold_parser/_add_doctor_parser''s affects()-closure
    docs need a touch noting the new frob ops aliases'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/guides/install.md
  reason: 'AFFECT001: _add_scaffold_parser/_add_doctor_parser''s affects()-closure
    docs need a touch noting the new frob ops aliases'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[release]
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[natives]
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[doctor]
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[clean]
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[fleet]
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[deploy]
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[scaffold]
- tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[gitlog]
- tests/unit/test_app_runners.py::TestOpsRunner::test_stats_subcommand_delegates_to_stats_runner
- tests/unit/test_app_runners.py::TestOpsRunner::test_unknown_subcommand_exits_1
designated_repro_test: null
threat: null
component: null
---
Refiled from T-1569 (T-1238 taxonomy slice, draft-loss class). Group operational verbs under frob ops following the frob explore precedent.