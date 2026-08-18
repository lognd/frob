---
id: T-2493
title: waive-audit has no systematic INERT-waiver check (path/symbol-shape mismatch)
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_waive_audit.py
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
Noted twice now in T-1614's own live passes (this session, both the pre-T-2485 attempt and this post-fix pass): 'no INERT waivers spotted' is reported for every reviewed batch, but that claim is weaker than 'none present' -- no systematic check runs. An INERT waiver (T-2314's 116 path-shape mismatches, T-2438's symbol-spelling one) reads as honoured to anyone grepping while doing nothing, and it will not show up as a NEEDS_REVIEW finding in waive-audit scan's current shape, because scan only lists waivers that MATCHED a live finding at their site -- a waiver that never matches anything (wrong path shape, wrong symbol, stale line number after a refactor) produces no violation to attach the waiver to in the first place, so it is invisible to this whole mechanism by construction, not merely unreviewed. Recommend: a companion check that, for every frob:waive directive in the source, confirms the named rule's detector actually fires (or would fire, absent the waiver) at that exact site -- i.e. walk the un-waived violation set the gate would produce and confirm every declared frob:waive has a corresponding suppressed violation, flagging any waiver with zero corresponding matches as INERT. This is a different check from waive-audit's honesty audit (which judges REASON quality) -- it judges whether the waiver DOES ANYTHING at all. Filed rather than designed/built here since T-1614's own declared scope this pass is empty (audit only, no source changes beyond the two obsolete-waiver removals already done).