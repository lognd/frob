---
id: T-5155
title: Declare frob run/build's exec site (src/frob/app/run_runner.py) on the cli
  node in design/frob.strata
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
found while landing T-4759: the real land refused on SELFAUDIT001 (capability 'exec' observed at src/frob/app/run_runner.py but not declared on the cli node). design/frob.strata was leased by T-4112/T-4113/T-4509 at the time, so T-4759 carries a frob:waive SELFAUDIT001 at the subprocess.run site instead. This ticket adds src/frob/app/run_runner.py to the cli node's may "exec" via-list and removes that waiver; the capability-via-ratchet lock bump is Tier-A land-owned (fix_sys111_capability_ratchet_sync).