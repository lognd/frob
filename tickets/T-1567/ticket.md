---
id: T-1567
title: 'cli regrouping: frob quality verb group (check/test/dup/arch/bind/cycle/mutate/perf)'
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
- src/frob/_cli_parsers/_quality.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_check.py
- src/frob/_cli_parsers/__init__.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/app.py
- src/frob/app/quality_runner.py
- docs/modules/cli.md
- docs/design/cli-regrouping.md
- tests/unit/test_app_runners.py
- tickets/T-1567/**
- docs/modules/app.md
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_quality.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_check.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/__main__.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/app.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/quality_runner.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1567/**
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: AFFECT001/DOC005 require touching app.md's runner doc + README's command
    table alongside the new quality_runner
  actor: logan
  at: '2026-08-08'
- op: add
  glob: README.md
  reason: AFFECT001/DOC005 require touching app.md's runner doc + README's command
    table alongside the new quality_runner
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[check]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[test]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[dup]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[cycle]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[perf]
- tests/unit/test_app_runners.py::TestQualityRunner::test_arch_subcommand_delegates_to_arch_runner
- tests/unit/test_app_runners.py::TestQualityRunner::test_mutate_subcommand_missing_file_exits_nonzero
- tests/unit/test_app_runners.py::TestQualityRunner::test_unknown_subcommand_exits_1
designated_repro_test: null
threat: null
component: null
---
Refiled from T-1567 (T-1238 taxonomy slice; the draft died in the land-splice draft-loss class before T-1271's land). Group the quality-facing verbs under one frob quality namespace following the frob explore precedent (T-1271/T-1238, src/frob/_cli_parsers/_explore.py + explore_runner.py).