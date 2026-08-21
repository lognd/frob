---
id: T-1238
title: 'EPIC cli regrouping: verb groups to shrink the top-level surface -- frob explore
  first'
state: done
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners.py
- tickets/T-1238/**
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_inv.py
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: keep evidence file covered before narrowing away the broad tests/** grant
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'T-2318: reconciling stale ledger state only; deliverables already landed
    under T-1271/T-1567..T-1571'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/**
  reason: 'T-2318: reconciling stale ledger state only; deliverables already landed
    under T-1271/T-1567..T-1571'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/__main__.py
  reason: 'T-2318: reconciling stale ledger state only; deliverables already landed
    under T-1271/T-1567..T-1571'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/**
  reason: 'T-2318: reconciling stale ledger state only; deliverables already landed
    under T-1271/T-1567..T-1571'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tests/**
  reason: 'T-2318: reconciling stale ledger state only; deliverables already landed
    under T-1271/T-1567..T-1571'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: design/frob.strata
  reason: 'T-2318: reconciling stale ledger state only; deliverables already landed
    under T-1271/T-1567..T-1571'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/gates/_inv.py
  reason: 'T-2318: reconciling stale ledger state only; deliverables already landed
    under T-1271/T-1567..T-1571'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tickets/T-1238/**
  reason: 'T-2318: ledger-only reconciliation scope'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: 'GIVEN frob --help THEN the top level presents a small set of verb groups
    (target: under ~15 entries) with subcommands grouped by intent, every old invocation
    either still working or aliased with a pointer, and the grouped help readable
    by a first-time user'
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: GIVEN frob explore THEN map/outline/xref/docs-search live as its subcommands,
    un-deprecated (frob:deprecated markers and sunset warnings removed), with their
    standalone deprecated top-level forms aliased through a transition window
  evidence:
  - tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
- text: GIVEN the regrouping design doc THEN it proposes the full grouping taxonomy
    for every current top-level command with a migration/alias policy, before any
    group beyond explore is implemented
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User directive 2026-07-29: frob is intimidating; group everything together. First concrete slice: the T-0580-deprecated navigation commands (map/outline/xref/docs-search) regroup into frob explore instead of being deleted -- this SUPERSEDES the 2026-10-01 sunset (T-0802 dropped with this epic as the reason). Design phase first for the full taxonomy (candidate buckets to evaluate, not prescribe: explore/navigation, quality/check+test+fix, tickets, design/sys+strata, supply-chain/vet, ops/release+registry+natives+doctor+clean, serve/perf tooling); un-deprecation of the explore members includes removing the docs 'Kept commands'/deprecation drift the 2026-07-29 staleness sweep catalogued. Children to file at design time: taxonomy design doc, explore group implementation, alias/transition machinery, help-surface rework, docs/index updates.