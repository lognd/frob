---
id: T-0573
title: 'frob fleet: cross-repo status, gate rollup, and ticket routing for the 9-repo
  estate'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/fleet/**
- src/frob/app/fleet_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- docs/modules/fleet.md
- tests/unit/fleet/**
- tests/unit/test_fleet_runner.py
- fleet.toml
- tests/integration/test_fleet_integration.py
- README.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/fleet/**
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/fleet_runner.py
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/app.py
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/__main__.py
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/fleet.md
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/fleet/**
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/test_fleet_runner.py
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: fleet.toml
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/integration/test_fleet_integration.py
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: README.md
  reason: 'T-0573: new fleet module + CLI wiring + docs + tests + integration test
    + README row'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: uv sync churn from make core / uv run during the review-fix round left a
    transient local diff; net content now matches main, but the touched-file history
    still needs scope coverage
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_ok
- tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_missing
- tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_malformed
- tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_ok
- tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_unknown_repo
- tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_missing_path
- tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_not_frob_enabled
- tests/unit/fleet/test_status.py::TestCollectStatus::test_collect_status_ok
- tests/unit/fleet/test_status.py::TestCollectStatus::test_collect_status_probes_sibling_pinned_frob_not_bare_path_frob
- tests/unit/fleet/test_status.py::TestCollectStatus::test_collect_status_missing_path
- tests/unit/fleet/test_status.py::TestRollup::test_rollup_orders_reddest_first
- tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_status_table
- tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_status_missing_manifest
- tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_route_ok
- tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_route_missing_flags
- tests/integration/test_fleet_integration.py::TestFleetIntegration::test_fleet_status_table_over_real_repos
designated_repro_test: null
threat: null
component: null
---
Nine repos run frob; the compliance campaign is coordinated from coordinator memory files. frob fleet status reads a fleet manifest (repo paths/remotes), rolls up per-repo check summaries, open-ticket counts by priority, and reddest-first ordering. Later: cross-repo ticket routing. Scope: new src/frob/fleet/, docs.