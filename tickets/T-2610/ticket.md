---
id: T-2610
title: WIRE001 resolver misses @property attribute reads as real callers
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
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
- src/frob/gates/_gate_cache.py
- tests/unit/test_wire001_property_attribute_access.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_gate_cache.py
  reason: T-2746 already landed the generic WIRE001 property-attribute-access resolver
    fix; measured the sole remaining beneficiary is the GateRunReplay.age_s waiver
    at _gate_cache.py (follow_up=T-2610), and the repro control belongs beside T-2746's
    own test file per its own precedent
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_wire001_property_attribute_access.py
  reason: T-2746 already landed the generic WIRE001 property-attribute-access resolver
    fix; measured the sole remaining beneficiary is the GateRunReplay.age_s waiver
    at _gate_cache.py (follow_up=T-2610), and the repro control belongs beside T-2746's
    own test file per its own precedent
  actor: logan
  at: '2026-08-25'
- op: add
  glob: frob.lock
  reason: 'T-2610: frob ack of GateRunReplay''s affects-closure doc after removing
    the redundant WIRE001 waiver writes to frob.lock'
  actor: logan
  at: '2026-08-25'
evidence:
- tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_as_keyword_argument_value_is_not_flagged
designated_repro_test: tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_as_keyword_argument_value_is_not_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

Found while working T-2585, out of that ticket's scope (a resolver-gate
capability question, not `frob check`'s replay feature itself).

`gate:WIRE`'s WIRE001 resolver follows call-EXPRESSION syntax (`x.foo()`)
to find a new symbol's real callers, but does not follow plain attribute
reads of a `@property` (`x.foo`, no parens). `src/frob/gates/_gate_cache.
py::GateRunReplay.age_s` is a real `@property` with a genuine production
caller (`frob.check._python._label_replay` reads `replay.age_s`) -- WIRE001
still flags it as unwired because the read is a plain attribute access, not
a call expression.

Waived narrowly for this one property (`frob:waive WIRE001 follow_up=
"<this ticket>"` at `GateRunReplay.age_s`) rather than left as a permanent
unexplained gap.

## Suggested direction

Extend WIRE001's call-graph resolver to also register a reference when a
NEW symbol decorated `@property` is read via plain attribute access
(`instance.name`), not just when it is called. This is the same class of
gap `TrackedSnapshot.symbols`/`.edges`/`.file_hashes` (pre-existing
`@property` members in the same file) would also hit if they were ever
re-flagged as "new in this diff" -- they are not currently, only because
WIRE001 only fires for symbols new to a given diff, not retroactively.
