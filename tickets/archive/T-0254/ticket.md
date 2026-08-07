---
id: T-0254
title: 'frob deploy epic: auditable, isolated, provable OS-layer deployment'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- strata-core/**
- design/**
- docs/**
- tests/**
- Makefile
- tickets.md
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
evidence:
- tests/integration/test_deploy_malmberg_pilot.py::TestMalmbergPilotChain::test_every_component_declares_a_host_manifest
- tests/integration/test_deploy_malmberg_pilot.py::TestMalmbergPilotChain::test_lateral_isolation_discharges_with_no_waivers
- tests/integration/test_deploy_malmberg_pilot.py::TestMalmbergPilotChain::test_vertical_isolation_discharges_with_no_waivers
- tests/integration/test_deploy_malmberg_pilot.py::TestMalmbergPilotChain::test_generate_and_conform_round_trip_clean
- tests/integration/test_deploy_malmberg_pilot.py::TestMalmbergPilotChain::test_every_service_reaches_media_store_only_via_declared_flow
designated_repro_test: null
threat: null
component: null
---
User mandate 2026-07-19: a frob deploy utility built into strata. The threat model: red teams compromise the one user that owns a service and nothing isolates that user -- lateral and vertical movement must be PROVABLY blocked, not hoped. The deployment sequence (idempotent install, status/health, uninstall with NO artifacts) must be auditable end to end, including an expensive opt-in VM-snapshot audit (VirtualBox) that is NOT part of make check. Scripts must tie into the model so hand edits are DETECTABLE through the strata checker, and the 'weird layer between the OS and the backend' (users, groups, units, ownership, ports) becomes provable architecture. Children: std.host OS-layer modeling -> movement-impossibility proofs + deploy script generation -> script<->model conformance gate -> VM snapshot audit harness -> real-service pilot (malmberg) remediating its awkward setup. Umbrella closes when all children close.