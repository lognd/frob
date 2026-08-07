---
id: T-0734
title: graphlang missing net/exec/fetch_url capability declarations for src/frob/arch/_srp.py
  (SYS100)
state: dropped
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working T-0724: after merging main (which landed src/frob/arch/_srp.py, the SRP architecture check), 'frob sys audit' surfaces 4 new SYS100 gaps -- graphlang observes net/exec/fetch_url at _srp.py:311-313 (plus one more fetch_url site) that design/frob.strata's graphlang node does not declare. Unrelated to T-0724's SYS203/contention wiring; needs its own investigation of whether these are real capabilities (declare them) or a false-positive scanner hit (waive with a reason).

## Drop reason
- 2026-07-22: duplicate: T-0724's worktree drafted this for the same 4x SYS100 graphlang/_srp.py issue; T-0729 fixed it (self-pattern exemption, landed, sys audit green) before this draft finalized at T-0724's land (absorbed by T-0729)