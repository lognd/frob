+++
id = "01M1T07NW17AMRFCRYHD2KJ3PP"
title = "waiver debt: follow_up waivers ticket-scoped, milestone budget"
type = "security"
category = "todo"
priority = "low"
parent = "01M1QDTYTFZHQYMDHNFBSGQXJJ"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:21Z"
aliases = ["T-3969"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_waive.py"]

[[acceptance]]
text = "given a frob:waive directive carrying follow_up= with no owning ticket, when frob check runs, then it is flagged as requiring a ticket scope"
bound = false

[[acceptance]]
text = "given a ticket-scoped follow_up waiver still open past its ticket's declared milestone, when a milestone gate runs, then it fails"
bound = false

[[acceptance]]
text = "given the current waiver population, when the per-subsystem count/age budget is first turned on, then it reports rather than fails (measure before enforcing)"
bound = false
+++

T-3919 item 1, ranked FIRST by the auditor's own coverage ordering ("would have caught the most of the report"). Merged with F-082 per the ticket's own instruction: F-082 reported that nothing warns when one ticket accumulates dozens of deferral waivers (a MISSING SIGNAL with no demonstrated consequence at the time); F-096 (this audit) supplies the consequence -- invisible waiver concentration is what let a HIGH-severity un-wired auth subsystem pass while frob check stayed green.

FINDING THIS WOULD HAVE CAUGHT: nearly every HIGH in the backend audit sat behind a frob:waive WIRE001 carrying a follow_up, or a frob:waive AFFECT001 reasoned as an internal execution-model change -- each individually honest, but TOGETHER letting an entire auth subsystem exist un-wired while every gate stayed green.

Proposed: waivers carrying a follow_up are ticket-scoped only (no bare/global follow_up waivers); a milestone gate fails while any such waiver remains open past its ticket's milestone; a count/age budget is reported per subsystem so concentration is visible before a milestone boundary, not just at it.

DECISION FLAGGED BY T-3919 ITSELF, make explicitly before building: this is arguably a GATE POSTURE change (a new failure mode on existing waivers) rather than new detection -- decide whether it targets 1.0.0 or a later milestone, and record the false-positive cost (an over-eager version of this could just push everyone to remove follow_up= rather than fix the debt, which defeats the purpose).
