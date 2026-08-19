---
id: T-2450
title: Promote verify->ticket_runner private helpers to a public seam
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/verify/**
- src/frob/app/ticket_runner/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/verify/**;src/frob/app/ticket_runner/**
  reason: 'T-2614: split single semicolon-joined glob string into two valid scope
    entries; the joined string is not a valid glob pattern and matched nothing'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/verify/**
  reason: 'T-2614: split single semicolon-joined glob string into two valid scope
    entries; the joined string is not a valid glob pattern and matched nothing'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/ticket_runner/**
  reason: 'T-2614: split single semicolon-joined glob string into two valid scope
    entries; the joined string is not a valid glob pattern and matched nothing'
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed by T-2407's SYS003 burn-down. verify/_drain.py, verify/_worker.py
call three PRIVATE (underscore-prefixed) app.ticket_runner helpers
directly: _rapid_sweep._detached_sweep_env, _land_cmd._unscoped_error_
findings, _rapid_sweep._file_regression_ticket. T-2407 declared the
verify -> cli Flow to unblock SYS003 (the coupling is real and
architecturally sound -- verify genuinely needs ticket_runner's sweep/
land primitives) but calling PRIVATE names across a node boundary is
itself debt: rename the three symbols to a public seam (drop the
leading underscore or introduce a small public wrapper module) and
update app.ticket_runner's cli-node interface= declaration plus all
callers. Measured blast radius at filing time: 10/55/62 grep hits
across src+tests+design for the 3 names respectively -- wide enough to
deserve its own reviewed change, not folded into the SYS003 pass.