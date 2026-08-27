---
id: T-3149
title: WIRE001 false positive for CLI dest present in _config_external.py (T-3140
  item 6)
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_wire.py
  reason: 'Verified before working: this is NOT a wire_gate production bug. T-2348

    (landed 31c1e197d, 2026-08-17) deliberately replaced WIRE001 case 3''s

    raw text-membership scan with an AST-parsed one

    (_config_external_forwarded_dest_names), collecting dest names ONLY from

    string literals that are actual elements of a module-level

    tuple/list/set/frozenset(...) ASSIGNMENT -- by design, so a dest string

    merely appearing as text elsewhere (comment, docstring, orphan fragment)

    no longer silently reads as "wired" (T-2348''s own stated false-negative

    fix). T-2348''s own new test suite

    (tests/unit/gates/test_wire001_cli_dest_semantic.py) already covers and

    PASSES the correctly-wired case using a real tuple assignment fixture

    (''_STRING_FIELDS = (\n    "bar_dest",\n)\n'').


    tests/test_gates.py::TestWireGate::

    test_new_cli_dest_present_in_config_external_is_not_flagged predates

    T-2348 and was never updated: its fixture writes ONLY a bare orphan

    string fragment (''    "ticket_accept_amend_index",\n''), which is a

    syntactically valid standalone tuple EXPRESSION but not an ASSIGNMENT --

    exactly the shape the AST-based check now correctly excludes. This is

    test staleness against T-2348''s deliberate tightening, not a wire_gate

    regression. Correcting scope from src/frob/gates/_wire.py (no fix

    belongs there) to the actual stale test file.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_gates.py
  reason: 'Verified before working: this is NOT a wire_gate production bug. T-2348

    (landed 31c1e197d, 2026-08-17) deliberately replaced WIRE001 case 3''s

    raw text-membership scan with an AST-parsed one

    (_config_external_forwarded_dest_names), collecting dest names ONLY from

    string literals that are actual elements of a module-level

    tuple/list/set/frozenset(...) ASSIGNMENT -- by design, so a dest string

    merely appearing as text elsewhere (comment, docstring, orphan fragment)

    no longer silently reads as "wired" (T-2348''s own stated false-negative

    fix). T-2348''s own new test suite

    (tests/unit/gates/test_wire001_cli_dest_semantic.py) already covers and

    PASSES the correctly-wired case using a real tuple assignment fixture

    (''_STRING_FIELDS = (\n    "bar_dest",\n)\n'').


    tests/test_gates.py::TestWireGate::

    test_new_cli_dest_present_in_config_external_is_not_flagged predates

    T-2348 and was never updated: its fixture writes ONLY a bare orphan

    string fragment (''    "ticket_accept_amend_index",\n''), which is a

    syntactically valid standalone tuple EXPRESSION but not an ASSIGNMENT --

    exactly the shape the AST-based check now correctly excludes. This is

    test staleness against T-2348''s deliberate tightening, not a wire_gate

    regression. Correcting scope from src/frob/gates/_wire.py (no fix

    belongs there) to the actual stale test file.

    '
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
tests/test_gates.py::TestWireGate::
test_new_cli_dest_present_in_config_external_is_not_flagged fails:
`wire_gate` (src/frob/gates/_wire.py, production file, out of T-3140's
declared scope) fires WIRE001 for a CLI dest that IS present in
`_config_external.py`. MEASURED (T-3140 triage): this is a genuine
WIRE001 false positive against the test's fixture, not test staleness --
the fixture writes the dest string into `_config_external.py` exactly as
the test expects it to be recognized, and `wire_gate` still flags it.

## Plan
Step through `wire_gate`'s resolution of `_config_external.py` against
this fixture shape (a `dest=` value present as a bare string literal) to
find why it is not recognized as wiring the CLI dest, and fix the false
positive with the existing test as repro (BUG002: confirm it fails at
this ticket's parent commit).
