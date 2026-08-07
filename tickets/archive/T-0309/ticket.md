---
id: T-0309
title: 'DSL: a trailing ''# noqa''/#-led tail on a directive line silently drops the
  directive'
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
- docs/modules/graph.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_waive_with_trailing_noqa_parses
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_tests_with_trailing_bare_noqa_binds
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_hash_inside_quoted_value_is_preserved
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (lithos W2b): appending '  # noqa: E501' to a frob:tests/frob:waive directive (to satisfy ruff 88-col on a long symref) makes _parse_attrs leftover non-empty -> MalformedDirective, edge dropped, only a debug log. ~50 directives silently regressed to unbound. A directive sharing a physical line with a linter-suppression comment is a reasonable pattern once a repo enforces both. Fix: _parse_attrs should strip a trailing '#'-led tail (noqa or any comment) from leftover before the emptiness check. Same subsystem as T-0286/T-0294. Test: 'frob:waive RULE reason="x"  # noqa: E501' parses to a valid waive edge.