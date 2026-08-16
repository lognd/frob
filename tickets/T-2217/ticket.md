---
id: T-2217
title: Wire frob.verify._quarantine.retire_unidentifiable_findings into frob verify
  dispose CLI
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/verify_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2207 fixed the core identity-less quarantine finding defect
(producer filter in raise_quarantine, consumer recovery verb
retire_unidentifiable_findings) but could not wire it to the CLI --
src/frob/app/verify_runner.py is outside T-2207's declared scope
(src/frob/verify/_quarantine.py only).

Add a `frob verify dispose --retire-unidentifiable` flag (or similar)
that calls frob.verify._quarantine.retire_unidentifiable_findings
directly, so an operator hitting a stuck identity-less quarantine
record again does not need a Python REPL / ad hoc script to invoke the
recovery verb -- only a direct import currently reaches it.
