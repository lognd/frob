---
id: T-draft-8b609d73
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-5339):
  7 new (rule, file) identit(ies) (DOC011, DUP001, DUP002, INV003)'
state: queued
kind: bug
origin: agent
created: '2026-09-23'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/webapp-a11y-interaction.md
- src/frob/webapp/_a11y_interaction.py
- tests/unit/test_webapp_a11y_interaction.py
findings:
- - DOC011
  - docs/modules/webapp-a11y-interaction.md
- - DUP001
  - tests/unit/test_webapp_a11y_interaction.py
- - DUP002
  - tests/unit/test_webapp_a11y_interaction.py
- - INV003
  - docs/modules/webapp-a11y-interaction.md
- - REF002
  - docs/modules/webapp-a11y-interaction.md
- - REF002
  - src/frob/webapp/_a11y_interaction.py
- - WIRE001
  - tests/unit/test_webapp_a11y_interaction.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-5339) at commit ce5745c0d28a10ab98b4c5948c224f4bcbbdadab found 7 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- DOC011  docs/modules/webapp-a11y-interaction.md
- DUP001  tests/unit/test_webapp_a11y_interaction.py
- DUP002  tests/unit/test_webapp_a11y_interaction.py
- INV003  docs/modules/webapp-a11y-interaction.md
- REF002  docs/modules/webapp-a11y-interaction.md
- REF002  src/frob/webapp/_a11y_interaction.py
- WIRE001  tests/unit/test_webapp_a11y_interaction.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.