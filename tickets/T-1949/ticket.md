---
id: T-1949
title: 'ARCH001: _close_failure_hint (_close_cmd.py) exceeds the 60-line function
  threshold'
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED while working T-1934: `frob check --only archgate` fails with a
pre-existing ARCH001 error, unrelated to T-1934's own scope:

  src/frob/app/ticket_runner/_close_cmd.py:34  ARCH001
  function `_close_failure_hint` has 116 lines (threshold: 60)

`git diff main -- src/frob/app/ticket_runner/_close_cmd.py` is empty --
this function was already over the ARCH001 threshold before T-1934
touched anything. Split `_close_failure_hint` into smaller helpers (or
add a reasoned `frob:waive ARCH001` if a real cohesion argument applies,
matching this repo's own ARCH001 waiver precedents in
src/frob/arch/_python.py and friends) so `frob check --only archgate`
reads clean again.
