---
id: T-0260
title: 'deploy pilot: model+generate+audit malmberg''s services, remediate the awkward
  setup'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0257
parent: T-0254
tier: ticket
sprint: null
scope:
- docs/**
- tests/**
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
T-0254 child 6 (proof on reality). Apply the full chain to malmberg (the real server product from pilot P3: server_api/ingest/cloudsync/faces/backup/display + media_store): extend design/malmberg.strata with std.host (dedicated service users per component, units, ownership of media_store paths, ports), prove HOST001/HOST002 movement-impossibility or record honest waivers, generate the deploy scripts, run the conformance gate, and if a VirtualBox environment is available run the full VM snapshot audit and attach the attestation. Remediate the current awkward setup step in malmberg's docs/scripts with the generated sequence. Work happens IN THE MALMBERG REPO per the break-and-report pilot protocol (frob-side gaps come back as tickets, filed serially by the coordinator); this frob-side ticket tracks the campaign and collects the gap list. Success = malmberg installs/uninstalls via generated scripts with a green conformance gate and a documented (or executed) VM audit path.