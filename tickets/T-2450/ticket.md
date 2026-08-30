---
id: T-2450
title: Promote verify->ticket_runner private helpers to a public seam
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/**
- src/frob/app/ticket_runner/**
- design/frob.strata
- tests/test_ticket_land.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets-verify-sweep.md
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
- op: add
  glob: design/frob.strata
  reason: 'T-2450: interface= declaration for the 3 new public seam symbols, plus
    their delegation tests'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2450: interface= declaration for the 3 new public seam symbols, plus
    their delegation tests'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2450: interface= declaration for the 3 new public seam symbols, plus
    their delegation tests'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'T-2450: new public-seam anchor section + updated cross-references for the
    three wrapper functions'
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_rapid_sweep.py::TestDetachedSweepEnvPublicSeam::test_delegates_to_the_private_implementation
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicketPublicSeam::test_delegates_to_the_private_implementation
- tests/test_ticket_land.py::TestUnscopedErrorFindingsPublicSeam::test_delegates_with_the_same_arguments
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ed9d7cbf9662bb7e0b995990fe3e40fcffb47c0f
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