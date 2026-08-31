---
id: T-3590
title: 'Error burn-down: clear the 73 live frob check errors (DRIFT/DOC cluster dominant)'
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-08-31 on main via budgeted frob check --json: 73 live errors led by DRIFT002 24, DRIFT001 10, DOC007 8, CLAUDE001 5. Re-measure per family with frob check --only <family> --budget 300, fix real findings at their source (DRIFT = re-verify the doc paragraph then frob ack, never blanket-ack; DOC = fix the pointer or the doc; CLAUDE001 = frob claude sync drift; TICK004 = queue hygiene), and record the remainder per rule with disposition if zero is not honestly reachable in one ticket.