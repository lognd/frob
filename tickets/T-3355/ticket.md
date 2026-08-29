---
id: T-3355
title: frob:debt does not actually suppress the gate finding it documents suppressing
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/_debt_deprecated.py
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
docs/guides/extending/comment-dsl-directives.md states 'frob:debt suppresses a GATE FINDING (the symptom)' -- but _apply_waivers (src/frob/gates/_waive.py) only reads EdgeKind.WAIVE via _waive_edges/_waivers_by_rule; EdgeKind.DEBT edges are never consulted there, only by debt_gate's own DEBT001-003 self-checks. Measured directly: converting a frob:waive to frob:debt (T-3295) makes the underlying gate finding (AFFECT001/COV001) reappear LIVE in frob check output rather than staying suppressed as the doc promises. Either the doc is aspirational and wrong (frob:debt was only ever meant to track, never suppress -- fix the doc), or _apply_waivers should also match DEBT edges the same way it matches WAIVE edges (fix the code). Found while converting T-3295's misclassified waivers -- did not fix here, outside that ticket's declared scope and this is a real design decision, not a quick patch.