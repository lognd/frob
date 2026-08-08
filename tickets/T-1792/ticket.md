---
id: T-1792
title: 'post-land sweep regression from T-1693: 3 new error(s) (DRIFT002, PARSE001,
  SYS004)'
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1693 at commit d4045f2a4ed6a32e6e5ed6c674ea4813683bfeee found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- DRIFT002  tests/system/test_frob_self_model.py
- PARSE001  design/frob.strata
- SYS004  design/frob.strata

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.