---
id: T-3310
title: OPAQUE001/WIRE001 false-fire on legitimate test-only reflection and private
  test helpers
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-037, F-041). Two
different gates, same theme: both false-fire on legitimate test-only code
shapes, forcing a worse rewrite of the test to satisfy the gate rather than
the property it is testing.

F-037: OPAQUE001 fires on `getattr` used inside a reflective invariant test
that must assert a property over EVERY field of a dataclass (the natural
spelling: `for f in fields(ASCII): getattr(ASCII, f.name)`), flagging it as
a "runtime-resolved capability indirection". `dataclasses.asdict` works as a
substitute but a test whose whole point is reflective field enumeration is a
reasonable exception the rule does not carve out today.

F-041: WIRE001 ("no caller outside its own tests") fires on private test-
module helpers -- a `@st.composite` hypothesis strategy and a small payload
helper, each used only by tests in the SAME file. That is the expected,
correct state for a private test helper; the only workaround was inlining
both, making the property test noticeably longer and harder to read.

WHAT NOT TO DO: do not blanket-exempt all of tests/ from either rule --
OPAQUE001 and WIRE001 both catch real problems in test code too (a
genuinely opaque runtime-resolved test dependency, or a "private" helper
that turns out to have callers outside its module and should be shared
properly). The carve-out needs to be for the SPECIFIC shape reported:
reflective enumeration via stdlib `dataclasses.fields`/`getattr` for
OPAQUE001, and a helper/strategy defined and used only within one test
module for WIRE001.

WHAT TO BUILD: a narrow exemption for each, scoped to the reported shape.
State in the Done report what detection each rule uses today and exactly how
the exemption is bounded (e.g. WIRE001: a symbol whose only references are
within the SAME test file, not merely "any test file").

MUST-FIRE FIXTURE (OPAQUE001): a `getattr` call resolving a name from an
external, non-dataclass-field source at runtime -- must still fire.

MUST-FIRE FIXTURE (WIRE001): a "private" helper that DOES have a caller in a
different file -- must still fire, module-locality is the whole point.

MUST-STAY-QUIET FIXTURES: (a) `for f in fields(X): getattr(X, f.name)` in a
reflective invariant test; (b) a hypothesis `@st.composite` strategy or
payload helper used only within its own test module.
