---
id: T-2662
title: 'docs/modules/gates.md: add table rows for CYCLE001/MILE001-004/TICK012/WAIVE009'
state: done
kind: docs
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
- docs/modules/gates.md
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
T-2613 fixed docs/modules/gates.md's `frob:enumerates` anchor (DOCENUM001)
by adding seven newly-found missing ids to the members= list: CYCLE001,
MILE001, MILE002, MILE003, MILE004, TICK012, WAIVE009. That anchor is now
in sync, but none of these seven ids have an actual documentation ROW
anywhere in docs/modules/gates.md's own gate-catalog table -- they exist
only as bare entries in the enumerate anchor's member list, same as they
did before T-2613, just no longer flagged as drift since DOCENUM001 only
checks the anchor's claimed-vs-real MEMBER SET, not full per-rule
documentation.

Add a proper table row (rule id, severity, one-line description, any
special-case notes) for each of the seven, matching the style of
existing rows in docs/modules/gates.md (see e.g. the GATESSCHEMA001 or
WIRE001 rows for the expected shape). Read each rule's own gate module
docstring (src/frob/gates/_waive.py and wherever CYCLE001/MILE00x/
TICK012/WAIVE009 are actually implemented) for the real description
rather than guessing from the id alone.