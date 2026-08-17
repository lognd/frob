---
id: T-2273
title: 'NameError: _OrphanEvidenceCheckOutcome is not defined blocks every land (T-2255
  residue)'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while landing T-2270 (unrelated ticket, scope src/frob/tickets/_store.py): 'frob ticket land' fails with 'main: unhandled exception during dispatch: name _OrphanEvidenceCheckOutcome is not defined' / 'frob: name _OrphanEvidenceCheckOutcome is not defined'.

_land.py uses _OrphanEvidenceCheckOutcome.SKIPPED_UNMEASURED / .RAN at lines ~4543-4603 (T-2255's orphan-evidence-check instrumentation, referenced in T-2256's own body as the guard meant to prevent orphaned-evidence lands) but the class itself is never defined or imported anywhere in the repo (confirmed via git grep across src/ for 'class _OrphanEvidenceCheckOutcome' and '_OrphanEvidenceCheckOutcome =' -- zero hits). This is not a transient failure: every 'frob ticket land' invocation that reaches this code path will hit the same NameError. Blocks the whole fleet, not just one ticket.