---
id: T-0984
title: 'frob fmt: off-by-one line-wrapping bug touches unrelated lines repo-wide'
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_fmt_directives.py
  reason: regression tests for the boundary-condition fix live alongside the module's
    existing test suite
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 touch note for canonicalize_text's changed behavior
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_space_exactly_at_budget_boundary_does_not_overflow
- tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_directive_line_at_exact_limit_is_byte_identical
- tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_directive_line_one_under_limit_is_byte_identical
- tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_directive_line_one_over_limit_wraps_and_stays_in_bounds
designated_repro_test: null
threat: null
component: null
---
Found by T-0972: a repo-wide "uv run frob fmt src/frob" intended to fix new waiver-comment line lengths touched ~180 out-of-scope files with an off-by-one wrapping decision (reverted by hand). Reproduce on a synthetic file whose directive comment sits exactly at the limit, fix the boundary condition, add a regression test asserting untouched-below-limit lines stay byte-identical.