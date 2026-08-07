---
id: T-1133
title: 'gates: suppress WAIVE004 staleness advisories on scoped/--only runs entirely'
state: done
kind: ux
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: call site wiring for the WAIVE004 scoped-run suppression lives in _assemble_gate_report
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: redundant -- already covered by the existing src/frob/gates/** glob
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run
- tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings
- tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only <stage> or any diff-scoped run WHEN a waiver matches
    0 findings because its gate did not run THEN no WAIVE004 advisory is emitted (the
    rule only fires on full unscoped runs where match-absence is meaningful)
  evidence:
  - tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run
threat: null
component: null
---
Every scoped run this session printed ~400-447 WAIVE004 warnings with a 'known-flaky, trust only full runs' caveat baked into the message text. A rule that prints its own do-not-trust-me disclaimer on scoped runs should not fire there at all; the caveat is tribal knowledge encoded as noise every coordinator and agent must mentally filter. Keep full-run behavior unchanged (T-1021's sweep depends on it).