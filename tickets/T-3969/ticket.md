---
id: T-3969
title: 'waiver debt: follow_up waivers ticket-scoped, milestone budget'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3919
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a frob:waive directive carrying follow_up= with no owning ticket, when
    frob check runs, then it is flagged as requiring a ticket scope
  evidence: []
- text: given a ticket-scoped follow_up waiver still open past its ticket's declared
    milestone, when a milestone gate runs, then it fails
  evidence: []
- text: given the current waiver population, when the per-subsystem count/age budget
    is first turned on, then it reports rather than fails (measure before enforcing)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3919 item 1, ranked FIRST by the auditor's own coverage ordering ("would have caught the most of the report"). Merged with F-082 per the ticket's own instruction: F-082 reported that nothing warns when one ticket accumulates dozens of deferral waivers (a MISSING SIGNAL with no demonstrated consequence at the time); F-096 (this audit) supplies the consequence -- invisible waiver concentration is what let a HIGH-severity un-wired auth subsystem pass while frob check stayed green.

FINDING THIS WOULD HAVE CAUGHT: nearly every HIGH in the backend audit sat behind a frob:waive WIRE001 carrying a follow_up, or a frob:waive AFFECT001 reasoned as an internal execution-model change -- each individually honest, but TOGETHER letting an entire auth subsystem exist un-wired while every gate stayed green.

Proposed: waivers carrying a follow_up are ticket-scoped only (no bare/global follow_up waivers); a milestone gate fails while any such waiver remains open past its ticket's milestone; a count/age budget is reported per subsystem so concentration is visible before a milestone boundary, not just at it.

DECISION FLAGGED BY T-3919 ITSELF, make explicitly before building: this is arguably a GATE POSTURE change (a new failure mode on existing waivers) rather than new detection -- decide whether it targets 1.0.0 or a later milestone, and record the false-positive cost (an over-eager version of this could just push everyone to remove follow_up= rather than fix the debt, which defeats the purpose).
