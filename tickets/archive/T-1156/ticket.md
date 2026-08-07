---
id: T-1156
title: 'strata: wire module= through the live SELFAUDIT001/sys audit call site so
  SYS201/SYS203 arbiter-awareness actually discharges'
state: dropped
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/sys_runner.py
- src/frob/strata/_design_load.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1149 built SYS201 arbiter-awareness (check_resource_contention's
module= argument now discharges an overlapping-path pair that shares a
common arbitered access resource, mirroring SYS203/T-1025). Like SYS203
before it, the capability is not yet load-bearing on the live gate: the
LIVE SELFAUDIT001 gate (src/frob/gates/__init__.py) and `frob sys audit`
CLI (src/frob/app/sys_runner.py) both call check_resource_contention
without a module= argument, and DesignIds has no Module-carrying field
to source one from -- the same disclosed gap T-1025 already left open
for SYS203, now shared by SYS201 too.

This ticket is that wiring, for both SYS203 and SYS201 together: thread
a Module (or equivalent) through the live gate's call site so both
rules' arbiter-awareness actually takes effect in `frob check`/`frob
sys audit`, not just in direct unit-test calls. Once landed, evaluate
whether design/frob.strata's five SYS203:tickets_ledger and five
SYS205:tickets_ledger waivers can be replaced by a real owns= path
declaration on the five tickets_ledger writers (this needs its own
verification against SYS205's WRITE path-scoping literal-path
extraction, not assumed to be automatic).

## Drop reason
- 2026-07-28: Duplicate of pre-existing T-1146 (same live-wiring gap for SYS203, filed before T-1149 discovered T-1146 already existed); T-1146 is being worked directly and its scope covers the identical gates/__init__.py+sys_runner.py+_design_load.py wiring. T-1146's own body should be updated to note it now also needs SYS201 (T-1149 gave it the same module= discharge SYS203 already had). (absorbed by T-1146)