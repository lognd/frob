---
id: T-2746
title: WIRE001 cannot see a @property's own attribute-access caller (false positive)
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- tests/test_wire.py
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
WIRE001's text-scan reach check (`frob.gates._wire._wire_reach_patterns`)
only recognizes call-shaped (`short(`) and by-reference (wrapper marker
/ dict-table value / ErrorSet member-access) usages of a newly-added
symbol. A `@property`'s only legal Python access shape is attribute
access with NO trailing parens (`graph.degraded_languages`, never
`graph.degraded_languages()`), which none of the existing patterns
match -- so any brand-new `@property` on a class gets a WIRE001 false
positive on its very first real, non-test caller, forcing a waiver
every time rather than the gate correctly recognizing it as reached.

Observed concretely at `DependencyGraph.degraded_languages`
(src/frob/cycle/graph.py, T-2700): `find_cycles` in the SAME file reads
it via plain attribute access one line below the property's own
definition, and WIRE001 still fired.

Scope: teach `_wire_reach_patterns`/`_is_reached_outside_diff_tests` a
property-shaped alternative (bare `short` NOT followed by `(` or other
call-token, gated on `record.kind == SymbolKind.METHOD` plus a way to
tell "this method is decorated `@property`" from the snapshot/AST) so a
genuine attribute-access caller of a new property counts as reached
without needing a waiver.
