---
id: T-1139
title: 'gates: register SYSWAIVE003 in _KNOWN_GATE_RULES (T-0671 registration gap)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: '_KNOWN_GATE_RULES (the registry T-1139 asks to add SYSWAIVE003 to) has

    since moved out of gates/__init__.py into gates/_waive.py (a prior split

    land, before this ticket was filed) -- the ticket''s original scope

    (_rule_id_scan.py, the scanner/authority module) does not include the

    file the registry literal itself now lives in. Adding

    src/frob/gates/_waive.py so the actual fix can land.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
---
tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
fails on current main: SYSWAIVE003 (src/frob/strata/_selfconform.py:1387,
introduced by T-0671's staleness-gated waiver mechanism) is emitted but
missing from frob.gates._rule_id_scan._KNOWN_GATE_RULES. Found while
verifying T-1115's gates/__init__.py family split (DEBT/DEPR extraction)
-- confirmed pre-existing/unrelated to that split (SYSWAIVE003 does not
appear anywhere in gates/__init__.py or the new _debt_deprecated.py; the
rule id is constructed entirely in src/frob/strata/_selfconform.py).
Add the missing _KNOWN_GATE_RULES entry.