---
id: T-1479
title: wire remaining daemon-proxy subcommands named by T-0321's integration map
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/serve/**
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
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