---
id: T-1568
title: 'cli regrouping: frob design verb group (sys/registry/docs/graph/exports)'
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
- src/frob/_cli_parsers/_design.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/_cli_parsers/__init__.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/app.py
- src/frob/app/design_runner.py
- docs/modules/cli.md
- docs/design/cli-regrouping.md
- docs/modules/app.md
- README.md
- tests/unit/test_app_runners.py
- tickets/T-1568/**
- docs/commands/exports.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_design.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/__main__.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/app.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/design_runner.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: README.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1568/**
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/commands/exports.md
  reason: 'AFFECT001: _add_exports_parser''s affects()-closure doc needs a touch noting
    the new frob design exports alias'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[sys]
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[registry]
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[docs]
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[graph]
- tests/unit/test_app_runners.py::TestDesignRunner::test_exports_subcommand_delegates_to_exports_runner
- tests/unit/test_app_runners.py::TestDesignRunner::test_unknown_subcommand_exits_1
designated_repro_test: null
threat: null
component: null
---
Refiled from T-1568 (T-1238 taxonomy slice, draft-loss class). Group design/model verbs under frob design following the frob explore precedent.