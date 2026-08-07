---
id: T-1380
title: 'T-1377/T-1379 follow-through: gate obligations for the new daemon-liveness
  code'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/_daemon_proxy.py
- design/frob.strata
- .frob-release.json
- pyproject.toml
- docs/modules/serve.md
- tests/test_app_daemon_proxy.py
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: the probe's evidence tests live here and covers_scope needs them in scope
  actor: logan
  at: '2026-08-01'
- op: add
  glob: uv.lock
  reason: the REL001 minor bump to 0.294.0 is recorded in uv.lock's own project version
    entry, so it legitimately changes with this ticket
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN frob check --only gates runs THEN gate:ARCH, gate:COV, gate:PRE
    and gate:SCOPE report 0 errors
  evidence:
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned
threat: null
component: null
---
T-1377 (bounded liveness probe) and T-1379 (opt-in default) closed before their own gate obligations were fully discharged: the probe split into _ask_version_over_socket/_classify_version_reply needs frob:ticket edges to an OPEN ticket, the new public test classes needed a design/frob.strata sync, the public-API change needs a REL001 bump, and _ask_version_over_socket trips ARCH103 for mixing socket I/O with its own branch decisions. This ticket carries all of that so the closed tickets' work is not left half-accounted.