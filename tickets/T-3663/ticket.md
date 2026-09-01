---
id: T-3663
title: 'ARCH102 remainder: _land_squash.py''s two deferred clusters'
state: queued
kind: feature
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_splice.py
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
Follow-up to T-3629 (git show 967af60c0): T-3629 extracted the test-then-impl commit-composition cluster from src/frob/tickets/_land_squash.py into the new src/frob/tickets/_land_splice.py, but _land_squash.py is still 2028 lines (LARGE001 threshold: 800) -- two more clusters were deferred at the time (see T-3629's own body/done-report for which symbols were identified but left in place). Move them into (or alongside) _land_splice.py following T-3629's own precedent: use frob refactor split/move (never hand-copy), verify via real import + the ticket_land_suite test suite, check whether any moved code observes declared strata capabilities that need a via-list update (T-3628's own capability-ratchet bump is the template if so).