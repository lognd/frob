---
id: T-1977
title: Wire capability_ratchet_violations into frob sys audit / a gate rule
state: queued
kind: security
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_sys_selfaudit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1628 built the capability via-list one-way ratchet (frob.strata._effects.capability_ratchet_violations) but wiring it into frob sys audit's own CLI/gate surface (src/frob/gates/_sys_selfaudit.py, frob.strata._selfconform's _collect_sys_violations aggregator) is out of T-1628's own declared scope (src/frob/strata/_effects.py only) -- same disclosed gap shape SYS109's own T-1627 left (see check_stale_via_symbols module docstring). Wire it the same way SYS109 was wired, with a real rule id (e.g. SYS111) once it fires through a production Violation-producing gate path, not just its own tests.