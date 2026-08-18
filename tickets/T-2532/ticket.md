---
id: T-2532
title: WIRE001 reach scan misses dotted classmethod/staticmethod calls
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
- src/frob/gates/_wire.py
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
_wire.py::_wire_reach_patterns's call_pattern regex is
(?<![A-Za-z0-9_.]){short}\s*\( -- the negative lookbehind explicitly
excludes any match preceded by a dot, so a legitimate real call site
shaped ClassName.method_name(...) (a classmethod/staticmethod called
qualified, the only way Python lets you call one) is invisible to
WIRE001's reach scan. member_access_pattern (the short.attr CLASS
shape) does not help either since it only fires for SymbolKind.CLASS
records, not for the METHOD symbol itself.

Discovered in T-2530: SealedGrantSet.from_root_node is a real
classmethod, called exactly once (its only sanctioned call site,
intentionally) as SealedGrantSet.from_root_node(node) from
_seed_grants_by_root_node in the same file -- a genuine, working,
non-test caller -- and WIRE001 still flagged it as unreached, forcing a
frob:waive for code that is not actually unwired.

Fix: extend call_pattern (or add a sibling regex, METHOD/staticmethod
kind only) to also match a dotted-qualified call
(?:[A-Za-z_][A-Za-z0-9_]*\.)+{short}\s*\( so a real
ClassName.method(...) call site counts as reached, the same way
wrapper_pattern already allows an optional name.-qualified prefix for
its dict-table-value shape.
