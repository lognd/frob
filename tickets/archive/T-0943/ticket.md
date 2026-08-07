---
id: T-0943
title: PARSE002 missing from _KNOWN_GATE_RULES registry (test_every_emitted_rule_literal_is_known
  fails)
state: dropped
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_parse_failures.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known`
fails on main: PARSE002 (introduced by T-0905/T-0902,
`src/frob/gates/_parse_failures.py:68`) is emitted but missing from
`_KNOWN_GATE_RULES` (and not in `_KNOWN_ISSUE_ALLOWLIST` either). Found
while verifying T-0926 in a fresh worktree after `make core`; unrelated
to T-0926's own scope (tests/conftest.py, src/frob/graph/__init__.py).
Fix: add a `_KNOWN_GATE_RULES` entry for PARSE002 (mirroring PARSE001),
or an allowlist entry citing this ticket if intentionally deferred.

## Drop reason
- 2026-07-27: already fixed by T-0924 (absorbed by T-0924)