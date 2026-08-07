---
id: T-0776
title: 'testing: subprocess spawn-budget litmus for CLI hot paths (fail on duplicate
  identical argv per invocation)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gitio.py
- src/frob/testing/**
- tests/system/
- docs/modules/testing.md
- tests/test_gitio.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/testing.md
  reason: recorder needs its public-API doc entry per playbook Document-as-you-go
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gitio.py
  reason: TEST001 requires a unit test for the new spawn_recorder/SpawnRecorder public
    API next to gitio's existing unit tests
  actor: logan
  at: '2026-07-23'
- op: add
  glob: pyproject.toml
  reason: 'REL001: new public gitio.SpawnRecorder/spawn_recorder API required a release
    stamp; reviewer-directed scope-add'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: .frob-release.json
  reason: 'REL001: new public gitio.SpawnRecorder/spawn_recorder API required a release
    stamp; reviewer-directed scope-add'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: uv.lock
  reason: 'REL001: new public gitio.SpawnRecorder/spawn_recorder API required a release
    stamp; reviewer-directed scope-add'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_exclude_hazard_gate_spawns_each_argv_at_most_once
designated_repro_test: null
acceptance:
- text: GIVEN a spawn-budget test running frob ticket list against a fixture repo
    WHEN the same argv is spawned more than its declared budget (default 1 for idempotent
    derivations like rev-parse --git-common-dir) THEN the test fails listing each
    duplicated argv with its count; GIVEN the post-T-0773 memoized lease layer THEN
    the budget test passes
  evidence:
  - tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once
  - tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once
  - tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
  - tests/system/test_spawn_budget.py::test_exclude_hazard_gate_spawns_each_argv_at_most_once
threat: null
component: null
---
Exact-count complement to the static loop-invariant-effect detector: gitio already logs every spawn, so expose a test-mode spawn recorder (context manager or env-gated counter in frob.gitio) and add system tests that run hot CLI entry points (ticket list/doable/show, check --only fast stages) against a fixture repo and assert no identical argv is spawned twice in one invocation unless a declared budget allows it. This is heuristic-free and would have caught the rev-parse incident (T-0773) the day it regressed. Design note: the recorder must be zero-cost when disabled and must not change spawn behavior; budgets live next to the tests, not in frob.toml, to keep the check self-contained.