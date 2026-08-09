---
id: T-1897
title: Tier-A interface= canonical-order fixer emits malformed [[],] for empty interface
  lists
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
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
found while working T-1883: land's pre-land Tier-A auto-fix (T-1872's interface= canonical-order fixer, src/frob/gates/_fix_engine_sync.py) rewrote design/frob.strata's 'node testsuite' and 'node scripts_ops' blocks (both declare attr interface=[]; -- empty list) into 'attr interface=[\n    [],\n];', which strata-core then fails to parse ('expected attribute value inside [..]', line 1333). This breaks 'frob ticket land' for EVERY ticket until fixed -- observed live during T-1883's land attempt on a clean post-T-1880-merge tree. Repro: run the Tier-A canonicalizer over a strata node whose declared attr interface=[] is already empty (zero symbols) and diff the output. Likely an off-by-one in the fixer's list-join: it emits a literal empty-list placeholder element instead of leaving an already-empty list untouched.