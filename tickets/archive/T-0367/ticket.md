---
id: T-0367
title: PERF004 detector false-positives on post-loop sorts (indentation-blind heuristic)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/
- tests/test_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_perf.py
  reason: 'regression tests for PERF004 AST-aware fix, T-0367

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_perf.py::test_perf004_does_not_fire_on_sort_after_loop_same_indent
- tests/test_perf.py::test_perf004_does_not_fire_on_sorted_call_after_loop_same_indent
- tests/test_perf.py::test_perf004_still_fires_on_sort_nested_deeper_inside_loop_body
- tests/test_perf.py::test_perf004_fires_on_sort_in_loop
- tests/test_perf.py::test_perf004_does_not_fire_on_sort_outside_a_loop
- tests/test_perf.py::test_perf004_does_not_fire_when_sorted_is_the_loop_iterable
- tests/test_perf.py::test_perf004_does_not_fire_on_sorted_generator_no_preceding_loop
- tests/test_perf.py::test_perf004_anchors_to_sort_call_line_not_def_line
designated_repro_test: null
threat: null
component: null
---
T-0363 had to reason-waive 3 genuine sorted()/.sort() sites (dup/_template.py:159, graph/__init__.py:153, vet/_capability.py:344) because the PERF004 heuristic is token/bracket-depth based and cannot see Python indentation, so it false-positives on any sort textually AFTER a for-loop at the same/outer indent (runs once, not per-iteration). Systematic fix: make the PERF004 detector indentation/AST-aware (tree-sitter: is the sort call a descendant of the loop BODY, not merely lexically after the loop header) so genuine once-after-loop sorts are not flagged and true in-loop sorts still are. Would let the 3 (soon 4, incl T-0366) waivers be removed. Do NOT loosen the true-positive case.