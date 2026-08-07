---
id: T-1357
title: 'SUPPRESS001 finding: src/frob/gates/_debt_deprecated.py:663 mypy-suppressed,
  ty-unsuppressed attr-defined'
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_debt_deprecated.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates_suppress.py::TestSuppress001Gate::test_both_dialects_present_reports_nothing
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_two_baselined_symbols_each_evaluated_independently
designated_repro_test: null
threat: null
component: null
---
SUPPRESS001 (T-1340's new evidence-driven detector, landed alongside this ticket)
fires for real against src/frob/gates/_debt_deprecated.py:663:

    baseline_counts = entry.file_counts()  # type: ignore[attr-defined]

This line carries a mypy `type: ignore[attr-defined]` but `ty` reports an
unsuppressed `unresolved-attribute` diagnostic on the same line -- a
downstream consumer running `ty` (or a future repo default switching
gating checkers) would eat a spurious error here that mypy's own
suppression never covered.

Fix: add a matching `# ty: ignore[unresolved-attribute]` comment to this
line (T-1341's own auto-fix, once it exists, would do this mechanically;
until then it is a one-line manual fix). Found while working T-1340,
outside T-1340's own declared scope (src/frob/gates/_suppress.py and
friends only) -- filed rather than hand-patched.