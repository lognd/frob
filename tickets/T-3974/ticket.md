---
id: T-3974
title: 'policy.norm: measure exercisability, document or redesign'
state: queued
kind: docs
origin: agent
created: '2026-09-06'
priority: low
parent: T-3920
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: 'given the investigation, when it completes, then a written verdict exists:
    either a worked example showing a real diff-shape use, or a recommendation to
    deprecate/redesign the surface'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3920 item 4. VERIFIED: git grep for "policy.norm" and "[[policy" across src/frob/policy and src/frob/strata found no norm-specific handling text and no worked example in docs -- consistent with the auditor's claim that they never found a way to exercise it. This is filed as an INVESTIGATE-AND-DOCUMENT-OR-FIX ticket, not a build ticket, per T-3920's own guidance ("either the surface is mis-aimed or its use case needs documenting with a worked example").

FINDING THIS WOULD HAVE CAUGHT: nothing directly -- this is a process/tooling gap, not a missed detection. [[policy.norm]] was NEVER EXERCISABLE across a full real security pass: every finding in their audits was a static-file property, not a diff-shape property, which is what policy.norm is apparently for. An entire configuration surface unused once in a real pass is itself a signal.

WORK: read what policy.norm is meant to do (its own design docs/tests), determine whether a genuine diff-shape security property exists that it could have caught in this consumer's four audits (if none, that is itself a finding to record), and either (a) write the missing worked example/doc showing a real use, or (b) if the surface is fundamentally mis-aimed, say so and recommend deprecation-or-redesign rather than silently leaving it undiscoverable.
