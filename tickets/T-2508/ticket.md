---
id: T-2508
title: audit non-node/store/queue strata constructs for a future clearance concept
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_strata.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2410 gave `.strata` real publicness derived from `clearance`, but only
node/store/queue carry a `clearance` clause in strata-core's grammar
today -- cache/cdn/balancer/resource stay public=True unconditionally
(an honest "no visibility concept here", not a placeholder, since their
grammar genuinely has none). If a future strata surface-syntax change
adds `clearance` to any of these constructs, `_declared_clearances`/
`_locate_declared_items` (src/frob/lang/_walk_strata.py) will silently
keep returning public=True for it until someone notices and wires it in
-- there is no gate today that would catch a newly-clearance-bearing
construct kind going unhandled. Low priority: audit whether any of
cache/cdn/balancer/resource plausibly warrant a clearance concept, and
if grammar work ever adds one, extend `_declared_clearances`'s handling
to match.