---
id: T-4081
title: 'L-6: ban err.message flowing directly into rendered state'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: low
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_secrets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a catch binding's message property passed directly as a setState argument,
    when the new lint rule runs, then it is flagged
  evidence: []
- text: given an error message passed through a sanitizing/mapping function before
    setState, when the rule runs, then it stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
L-6 (F-273). VERIFIED: git grep for a rule banning err.message (or equivalent caught-exception message text) flowing into rendered UI copy found nothing in src/frob. NOT covered by M-3's generated-types rule (T-4072) -- M-3 is about fictional/stale TYPE shapes (L-3), this is about LEAKY MESSAGE TEXT (a caught error's raw message reaching the rendered DOM), a different failure mode entirely even though the consumer's own audit groups L-3 and L-6 in one bullet.

FINDING THIS WOULD HAVE CAUGHT: a caught exception's raw .message text fed into a setState call that in turn feeds rendered copy -- exposing internal error detail (stack-adjacent strings, backend implementation detail) directly to the end user, a well-known information-disclosure pattern distinct from a generic unhandled-exception concern. Proposed: a lint rule banning `err.message` (or `error.message`/`e.message`, the common catch-binding names) as a direct argument to a setState call (or equivalent state-setter) whose value is known to feed rendered text -- structural, no data-flow analysis needed for the common `catch (err) { setSomething(err.message) }` shape.
