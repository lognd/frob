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
