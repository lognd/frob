---
id: T-2910
title: 'frob sys init: derive a starting strata model so a new repo gets value on
  day one'
state: queued
kind: feature
origin: human
created: '2026-08-25'
priority: high
parent: T-2920
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_bootstrap.py
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- src/frob/_cli_parsers/_misc.py
- docs/commands/sys.md
- tests/unit/strata/test_bootstrap.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_bootstrap.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/config.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/commands/sys.md
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/strata/test_bootstrap.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2907
  reason: 'T-2907 strata redesign: bootstrap and progress-surface are children of
    the derive-not-declare program'
  actor: logan
  at: '2026-08-25'
- field: parent
  old_value: T-2907
  new_value: T-2920
  reason: 'user corrected the premise: auto-deriving may=/code= makes the ceiling
    equal whatever the code does, defeating the shrink-the-interface purpose; superseded
    by the shrink-only ratchet design'
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
