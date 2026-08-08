---
id: T-1479
title: wire remaining daemon-proxy subcommands named by T-0321's integration map
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/serve.md
- src/frob/serve/_tools.py
- src/frob/serve/_socketd.py
- src/frob/app/map_runner.py
- tests/test_app_daemon_proxy.py
- tickets/T-1479/**
- tickets/T-1807/**
- docs/modules/app.md
- docs/modules/render.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/serve/**
  reason: 'T-1479: narrow the mega-glob to the actual files -- server-side RPC handler+dispatch
    table plus the one CLI runner (frob map) chosen for this pass, matching the existing
    frob_stats/frob_graph_query precedent'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/serve/_tools.py
  reason: 'T-1479: narrow the mega-glob to the actual files -- server-side RPC handler+dispatch
    table plus the one CLI runner (frob map) chosen for this pass, matching the existing
    frob_stats/frob_graph_query precedent'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: 'T-1479: narrow the mega-glob to the actual files -- server-side RPC handler+dispatch
    table plus the one CLI runner (frob map) chosen for this pass, matching the existing
    frob_stats/frob_graph_query precedent'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/map_runner.py
  reason: 'T-1479: narrow the mega-glob to the actual files -- server-side RPC handler+dispatch
    table plus the one CLI runner (frob map) chosen for this pass, matching the existing
    frob_stats/frob_graph_query precedent'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'T-1479: narrow the mega-glob to the actual files -- server-side RPC handler+dispatch
    table plus the one CLI runner (frob map) chosen for this pass, matching the existing
    frob_stats/frob_graph_query precedent'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1479/**
  reason: 'T-1479: own ticket dir + the WIRE001-false-positive follow-up ticket filed
    during this ticket''s own work'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1807/**
  reason: 'T-1479: own ticket dir + the WIRE001-false-positive follow-up ticket filed
    during this ticket''s own work'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/app.md
  reason: 'T-1479: AFFECT001 requires the affects()-closure doc for map_runner.run
    to be touched alongside the code change'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/render.md
  reason: 'T-1479: AFFECT001 also requires this second affects()-closure doc for map_runner.run'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_map_json_daemon_matches_in_process
designated_repro_test: null
threat: null
component: null
---
docs/modules/serve.md's daemon-proxy section says T-0321's integration
map names outline/map/xref/parse/graph/exports/bind/docs/stats as
eventual proxy targets alongside check --delta-style reads, and that
these remain a disclosed residual, not yet wired. T-0321 itself is done
(tickets-archive.md); no open follow-up currently tracks wiring the
remaining subcommands through the daemon proxy. Wire the remaining
named subcommands (or a subset chosen by the implementer, disclosed in
the Done report) through frob.serve._tools/query() the same way
T-1128/T-1147 wired frob_graph_query/frob_doable_tickets/
frob_run_touched_tests/frob_check_delta. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.