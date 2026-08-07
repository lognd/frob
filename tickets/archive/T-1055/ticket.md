---
id: T-1055
title: 'PLACE001: fix 2 misplaced directives in test_ticket_runner_gate_findings.py
  (blocked on T-0714 landing)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_parses_multiple_findings_from_errors_section
- tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_uses_tree_venv_python_when_present
designated_repro_test: null
threat: null
component: null
---
Carved out of T-1024 (REF/COV/DEAD/PLACE small-bucket sweep). Both
PLACE001 findings sit in tests/unit/test_ticket_runner_gate_findings.py
(lines 78 and 279 as of T-1024's measurement): a frob: directive whose
fully-resolved binding falls back to the enclosing class/module rather
than the specific nearby symbol it plausibly intends.

T-1024's dispatch explicitly deferred this pair because
tests/unit/test_ticket_runner_gate_findings.py is scope-leased to T-0714
("ticket doable: relocate stale-lease/scope diagnostics to frob check"),
which is still `state: queued` (not landed) as of T-1024's close -- fixing
the two directive placements here would collide with T-0714's own planned
edits to the same file.

Fix: once T-0714 lands (or is confirmed abandoned), move the two
misplaced directives at tests/unit/test_ticket_runner_gate_findings.py:78
and :279 into their intended following-windows, then re-measure PLACE001
to zero.