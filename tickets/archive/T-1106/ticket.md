---
id: T-1106
title: 'daemon: wire remaining query-shaped CLI commands through the proxy (T-0321
  integration map)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: T-0321
tier: ticket
sprint: null
scope:
- src/frob/app/_daemon_proxy.py
- tests/test_app_daemon_proxy.py
- docs/modules/serve.md
- src/frob/app/graph_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/
  reason: 'narrowed per dispatch instructions: src/frob/app/ was contended this wave
    (ticket_runner.py owned by a sibling ticket, app/ subject to a late arch extraction);
    wiring frob graph affects --json needs only graph_runner.py, the existing _daemon_proxy.py,
    and their tests'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/graph_runner.py
  reason: 'narrowed per dispatch instructions: src/frob/app/ was contended this wave
    (ticket_runner.py owned by a sibling ticket, app/ subject to a late arch extraction);
    wiring frob graph affects --json needs only graph_runner.py, the existing _daemon_proxy.py,
    and their tests'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_graph_affects_json_daemon_matches_in_process
designated_repro_test: null
acceptance:
- text: given each query-shaped CLI command from T-0321's integration map (outline,
    map, xref, graph, exports, stats, ...), when the daemon runs, then the command
    serves from the daemon with a differential-parity test proving daemon-served output
    identical to in-process
  evidence:
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_graph_affects_json_daemon_matches_in_process
threat: null
component: null
---
Refile of T-1093's dead draft T-1106 (lost in the 10b restore). T-1093 wired frob perf hot --json only (the one command with a field-identical payload to diff); this extends the proxy across the integration map, each command gaining its own parity test.