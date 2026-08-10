---
id: T-1958
title: 'DOCENUM001: docs/modules/gates.md#rule-catalog stale after T-1937''s 8 new
  rule ids'
state: queued
kind: docs
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1937 (landed 577c708436639342620efdd080d6667ee552db78) added 8 new rule
ids to src/frob/gates/_waive.py::_KNOWN_GATE_RULES (BUDGET001, CHECK001,
CVEFP001, DEPLOY001, DEPLOY002, DEPLOY003, DERIVED001, SYS109). T-1937's
own declared scope did not include docs/modules/gates.md, so the doc was
not updated in the same diff -- confirmed as a real, new gate ERROR by an
unscoped `frob check --only gates` measured immediately after the land:

  DOCENUM001 docs/modules/gates.md:13: frob:enumerates at
  docs/modules/gates.md#rule-catalog claims a stale member list for
  'src/frob/gates/_waive.py::_KNOWN_GATE_RULES' (doc omits: BUDGET001,
  CHECK001, CVEFP001, DEPLOY001, DEPLOY002, DEPLOY003, DERIVED001,
  SYS109)

Fix: add the 8 ids to docs/modules/gates.md's #rule-catalog enumeration
so the frob:enumerates directive is accurate again.
