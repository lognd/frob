---
id: T-1828
title: T-1738's wave feature landed with ARCH001/ARCH103/COV001 findings (2 files,
  unwaived)
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_doable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Discovered while landing T-1570 (unrelated CLI-regrouping ticket): a full
unscoped `frob check --land-parity` on top of current main shows 4 real,
unwaived errors that predate T-1570's own diff entirely -- confirmed via
`git log -- <file>`, the introducing commit is T-1738's own land
(0b51c6766, "frob ticket wave: partition the doable set into N mutually
scope-disjoint groups for parallel"), landed by a different agent earlier
today:

  ARCH001  src/frob/app/ticket_runner/_query.py::_wave has 72 lines (threshold: 60)
  ARCH103  src/frob/app/ticket_runner/_query.py::_wave mixes I/O, string-formatting, and 10 decision points in one body
  ARCH001  src/frob/tickets/_doable.py::wave has 98 lines (threshold: 60)
  COV001   src/frob/tickets/_doable.py::WaveGroup/WaveRemainderReason/WaveResult/wave are public with no frob:doc edge

None of these files are in T-1570's scope (ticket/debt/deprecated CLI
naming) and none were touched by this ticket's diff. Filed as its own
ticket per the disclosed-cut convention rather than silently expanding
T-1570's scope to fix someone else's landed feature.
