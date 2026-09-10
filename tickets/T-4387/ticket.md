---
id: T-4387
title: DOC014 missing from _KNOWN_GATE_RULES registry
state: done
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml
- tests/gates_suite/test_sys.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4139 (landed fa90c64cd) added DOC014 gate rule (src/frob/gates/_doclink_docanchor.py) but never registered it in _KNOWN_GATE_RULES (src/frob/gates/_waive.py), breaking tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known on every CI OS leg: rule id(s) constructed in src/frob/gates or src/frob/strata but missing from _KNOWN_GATE_RULES: {'DOC014': 'src/frob/gates/_doclink_docanchor.py:513'}. Register DOC014 in _KNOWN_GATE_RULES (mirroring DOC013's entry), plus the docs/rule-catalogue entries DOC013 has: docs/modules/gates.md (frob:enumerates member list + severity table row) and docs/design/registry/check-coverage.yaml (CHK-GATE-DOC013-shaped CHK-GATE-DOC014 entry, already referenced by the frob:enforces CHK-GATE-DOC014 directive at _doclink_docanchor.py:507).