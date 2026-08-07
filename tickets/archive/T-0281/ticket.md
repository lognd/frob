---
id: T-0281
title: 'deploy generate polish: dedup shared runs_as useradd, listens unit hardening,
  multi-host status, CAP_NET_BIND over-grant, DEBUG flood'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/deploy/**
- src/frob/strata/**
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/deploy/test_generate.py::TestSorted::test_sorted
- tests/unit/deploy/test_generate.py::TestSorted::test_privileged_port_grants_cap_net_bind
- tests/unit/deploy/test_generate.py::TestInstall::test_idempotent
- tests/unit/deploy/test_generate.py::TestInstall::test_empty_model
- tests/unit/deploy/test_generate.py::TestInstall::test_shared_runs_as_useradd_block_rendered_once
- tests/unit/deploy/test_generate.py::TestStatus::test_one_line
- tests/unit/deploy/test_generate.py::TestStatus::test_no_units_declared
- tests/unit/deploy/test_generate.py::TestStatus::test_manifest_present_but_not_a_unit
- tests/unit/deploy/test_generate.py::TestStatus::test_unit_with_no_listens_ports
- tests/unit/deploy/test_generate.py::TestUninstall::test_removes
- tests/unit/deploy/test_generate.py::TestUninstall::test_empty_model
- tests/unit/deploy/test_generate.py::TestUninstall::test_node_with_no_unit_no_owns_no_runs_as
- tests/unit/deploy/test_generate.py::TestUninstall::test_shared_runs_as_userdel_block_rendered_once
- tests/unit/deploy/test_generate.py::TestAll::test_returns_all
- tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks
designated_repro_test: null
threat: null
component: null
---
T-0260 malmberg pilot findings (batched, all in the deploy generator; each needs a fixture+fix): (5) a user shared across a node and a store (media_store+ingest both runs_as malmberg-ingest) emits the useradd guard block TWICE in install.sh -- dedup service-user creation by distinct runs_as identity. (6) listens PORT drives status.sh /dev/tcp health probes but is never materialized into the unit (no .socket, no IPAddressAllow/SocketBindAllow) -- emit network hardening or at least document the port in the unit. (7) status.sh probes 127.0.0.1 for ALL units incl. ones on other hosts (malmberg display is a separate host) -> always reports remote port closed; std.host has no host/placement vocabulary to partition artifacts per host -- design a /placement construct or partition status per declared host (bigger, may split out). (8) may 'net' unconditionally adds CAP_NET_BIND_SERVICE even when all declared listens ports are >=1024 (unprivileged) -- only add it when a listens port is <1024. (4) frob deploy generate floods stdout with per-node 'host manifest runs_as=...' DEBUG lines (repeated per consumer pass) -- route through the logger at DEBUG, mute stdout like check_runner/map_runner (T-0202 class). (10, doc) waive clauses parse but elaborate(...).danger_ok exposes no waivers attribute (read via separate _waive channel) -- add a doc note on reading waivers back from a parsed model. Item 7 (host/placement vocabulary) may warrant its own ticket if it grows.