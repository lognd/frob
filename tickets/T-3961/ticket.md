---
id: T-3961
title: provenance / trust-as-identity construct in strata
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3920
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design note answering what a derived_from edge means for existing
    carries()/atoms and how SYS100 would consume it, when this ticket's design step
    completes, then the note is attached before any implementation begins
  evidence: []
- text: given the design is accepted, when implemented, then SYS100 (or a successor
    rule) can require that a single helper produce every client IP, and a trust-as-identity
    declaration exists distinct from the capability ratchet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Convergence 2 of T-3928 (backend audit item 6 + threat-model item 6, arrived independently -- the strongest single signal across all four lists, per T-3928's own framing). Filed here per T-3920's own decomposition guidance: "item 6 is a strata LANGUAGE change and should be scoped with T-3919 item 6 as one design, not two." Do NOT file a second ticket on T-3919 or T-3928 for this ask; cite this one.

FINDING THIS WOULD HAVE CAUGHT: a raw client IP trusted behind a proxy (confirmed threat-model finding). Backend item 6 frames it as PII provenance -- a derived_from edge would let SYS100 require that a single helper produce every client IP, currently invisible because a wrong IP is still just a string. Threat-model item 6 frames the same gap one level up: the capability ratchet polices what code MAY DO; nothing polices what it may TRUST AS IDENTITY (raw peer address vs proxy header). Capability and trust are different axes and strata models only the first.

This is a strata LANGUAGE change (a derived_from edge / provenance construct on atoms, plus a trust-as-identity construct), not a gate rule -- different subsystem, different reviewer, different risk than the rest of T-3919/T-3920/T-3928's items. Needs its own design pass before implementation: what a derived_from edge means for existing carries()/atoms, how SYS100 would consume it, and how a trust-as-identity declaration composes with the existing capability ratchet.
