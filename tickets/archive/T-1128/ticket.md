---
id: T-1128
title: 'daemon: reconcile CLI payload shapes to proxy graph-query/check-delta/touched-tests/doable
  (T-1106 residual)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_tools.py
- docs/modules/serve.md
- src/frob/app/_daemon_proxy.py
- src/frob/app/graph_runner.py
- src/frob/app/check_runner.py
- src/frob/app/test_runner.py
- src/frob/app/ticket_runner/_query.py
- docs/modules/app.md
- docs/modules/testing.md
- tests/test_serve.py
- tests/test_app_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_daemon_proxy.py
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/graph_runner.py
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/test_runner.py
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/serve/_tools.py
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/serve.md
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/app.md
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/testing.md
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: src/frob/app/**
  reason: 'T-1128: narrow the broad src/frob/app/** glob to the exact daemon-proxy
    + 4 runner files touched (sys_runner.py held by T-1061 this wave)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_serve.py
  reason: 'T-1128: our _tools.py payload-shape changes (frob_doable_tickets/frob_run_touched_tests)
    break existing frob_doable_tickets/frob_run_touched_tests unit tests; test_app_daemon_proxy.py
    holds the new differential-parity tests, the T-1093/T-1106 precedent location'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'T-1128: our _tools.py payload-shape changes (frob_doable_tickets/frob_run_touched_tests)
    break existing frob_doable_tickets/frob_run_touched_tests unit tests; test_app_daemon_proxy.py
    holds the new differential-parity tests, the T-1093/T-1106 precedent location'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_graph_query_json_daemon_matches_in_process
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_doable_tickets_json_daemon_matches_in_process
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_touched_tests_json_daemon_matches_in_process
- tests/test_serve.py::TestDoableTickets::test_lists_queued_ticket
- tests/test_serve.py::TestRunTouchedTests::test_no_diff_selects_nothing
designated_repro_test: null
acceptance:
- text: GIVEN a running daemon WHEN frob graph query, frob check --delta, frob test
    (touched-set), or frob ticket doable runs THEN each is served through the proxy
    with field-for-field differential parity against in-process execution
  evidence:
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_graph_query_json_daemon_matches_in_process
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_doable_tickets_json_daemon_matches_in_process
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_touched_tests_json_daemon_matches_in_process
  - tests/test_serve.py::TestDoableTickets::test_lists_queued_ticket
  - tests/test_serve.py::TestRunTouchedTests::test_no_diff_selects_nothing
threat: null
component: null
---
T-1106 wired frob graph affects and disclosed this residual: frob_graph_query/frob_check_delta/frob_run_touched_tests/frob_doable_tickets RPC methods EXIST server-side but each CLI payload needs field-for-field shape reconciliation with its _tools counterpart before proxying (docs/modules/serve.md Scope cut section). Coordinator refile: the original draft died to a 10b ledger restore.