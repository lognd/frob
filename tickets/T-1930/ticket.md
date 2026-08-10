---
id: T-1930
title: add a single porcelain verb sequencing the happy-path ticket workflow (T-1556
  criterion 2b)
state: queued
kind: ux
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/**
- src/frob/_cli_parsers/_ticket/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1556's criterion 2 has two halves: (a) every close/land refusal names
the exact next command, and (b) a single porcelain verb exists that
sequences the happy path (start -> implement -> evidence -> accepts ->
done-report -> close). T-1556 delivered (a) in full (_close_cmd.py's
_close_failure_hint now covers EvidenceScopeUnbound, EvidenceNotPassing,
OwnObligationsUnclean, GateClaimUnverified, LiveTrackerCited, and
NewGateRuleUnaccepted, each naming the exact remedy command) but not (b)
-- no new porcelain verb was added. Filed as its own follow-up so it does
not silently get treated as delivered under T-1556's already-closed
acceptance trail.
