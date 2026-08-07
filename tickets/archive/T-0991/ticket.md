---
id: T-0991
title: frob fmt wrap drops the word-boundary space before a continuation when a directive
  carries a trailing attribute (silent token concatenation)
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates_fmt_directives.py::TestConventionUnitBinding::test_target_plus_kind_attribute_splitting_after_target_round_trips
- tests/test_gates_fmt_directives.py::TestConventionUnitBinding::test_logical_text_is_identical_across_widths_and_attribute_counts
designated_repro_test: null
acceptance:
- text: given any directive with trailing attributes, when canonicalize_text wraps
    and the parser rejoins it, then the token stream is identical to the unwrapped
    form at every width
  evidence:
  - tests/test_gates_fmt_directives.py::TestConventionUnitBinding::test_target_plus_kind_attribute_splitting_after_target_round_trips
  - tests/test_gates_fmt_directives.py::TestConventionUnitBinding::test_logical_text_is_identical_across_widths_and_attribute_counts
threat: null
component: null
---
Found by T-0988s token-stream verification protocol (1152/1153 hunks clean): wrapping a frob:tests directive whose target is followed by a trailing attribute (kind="unit") split right after the target but dropped the word-boundary space before the continuation, so rejoining concatenated target+attribute into one corrupted token -- a live DRIFT002 (no longer resolves) absent at HEAD. Distinct class from T-0987 (misparse-as-new-directive) -- this is silent target corruption inside a correctly-recognized directive. Fix the wrap/rejoin round-trip to preserve token boundaries exactly; regression tests: the exact TestConventionUnitBinding shape, plus a property test asserting token-stream identity across wrap widths for directives with 0/1/2 trailing attributes. T-0988 (repo-wide recompaction) is blocked on this.