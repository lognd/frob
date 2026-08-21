---
id: T-2610
title: WIRE001 resolver misses @property attribute reads as real callers
state: queued
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
