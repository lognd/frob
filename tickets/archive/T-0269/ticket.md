---
id: T-0269
title: invalid frob:tests kind='system' shipped in test_cli_check.py:237 -- malformed
  directive silently dropped
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/graph/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestDsl::test_invalid_kind_in_module_docstring_is_surfaced_not_silent
designated_repro_test: null
threat: null
component: null
---
T-0231 review found a pre-existing malformed frob:tests directive at tests/system/test_cli_check.py:237 using kind='system' (valid kinds: unit/integration/e2e per _TESTS_KINDS). It parses malformed and is silently dropped -- the bound symbol has no real test edge. Landed via commit 289f2c68 (T-0229). Fix: kind='integration' (or extend _TESTS_KINDS to include 'system' if that taxonomy is intended -- decide, since T-0225 also touches the design-vs-code test-kind question). Also: this class only surfaces on full frob check, not --ticket -- covered by T-0265's scoping fix but this is the concrete instance to clean up. Grep the whole repo for other kind='system'/invalid-kind directives while here.