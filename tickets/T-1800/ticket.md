---
id: T-1800
title: SYS108 missing from _KNOWN_GATE_RULES (TestKnownGateRuleIds red on main)
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
- tickets/T-1800/**
- tickets/T-1805/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1800/**
  reason: 'T-1800: own ticket dir + the follow-up ticket filed during this ticket''s
    own work'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1805/**
  reason: 'T-1800: own ticket dir + the follow-up ticket filed during this ticket''s
    own work'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
---
Found while working T-1539 (PERF012 registry-entry gap). tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known fails on main (confirmed pre-existing, unrelated to T-1539's PERF012 change): SYS108 is constructed at src/frob/strata/_selfconform.py:1421 but absent from _KNOWN_GATE_RULES in src/frob/gates/_waive.py. Same drift class as the PERF012 gap T-1539 fixes -- paste the missing entry per generated_gate_rule_ids()'s report.