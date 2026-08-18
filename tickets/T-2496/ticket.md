---
id: T-2496
title: wire find_collision_suspects into a waive-audit CLI subcommand
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/_cli_parsers/_ticket/_closeout.py
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
T-2493 built find_collision_suspects (sound INERT-waiver collision detection: flags a frob:waive only when an ACTIVE unsuppressed GateReport violation of the same rule sits in the same file, never from absence -- see that function's own T-2493 section docstring in _waive_audit.py for the full incident history/reasoning) but deliberately left it unwired to any CLI subcommand, per the coordinator's report-only-to-start brief. This ticket is the follow-up: wire it into 'frob ticket waive-audit scan' as an opt-in flag (e.g. --check-collisions), which requires (a) running or accepting an already-computed GateReport (avoid forcing every scan call to pay for a gate run -- keep it opt-in/explicit) and (b) CLI parser changes in _closeout.py, both out of T-2493's single-file scope. Still report-only -- do not wire anything that removes/rewrites a waiver or gates a check/land in this follow-up either, that decision needs its own separate review.