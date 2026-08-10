---
id: T-1965
title: Retire T-1942's WIRE001 follow_up citations in _arch.py/_coverage_sites.py
  now that the WAIVE004 consumer is wired
state: queued
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1942 wired frob.gates._coverage_sites' examined-sites substrate into
fix_waive004_stale_waiver as its first production consumer. Four
WIRE001 waivers in src/frob/gates/_arch.py (arch_examined_sites) and
src/frob/gates/_coverage_sites.py (attach_examined_sites,
is_family_instrumented, site_examined) cite follow_up="T-1942" as "the
follow-up ticket that will call this from production code" -- now
fulfilled. Re-point those 4 follow_up attributes to this ticket (or
simply drop follow_up now that the cited work is done, whichever this
ticket's own review decides), so T-1942 can close without a
LiveTrackerCited refusal.
