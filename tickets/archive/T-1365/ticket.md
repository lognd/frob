---
id: T-1365
title: 'Clear main''s two gate errors: PII012 false positive and the TICK003 archive
  backlog'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_doctor_runner_t1276.py
- tickets.md
- src/frob/app/doctor_runner.py
- tests/system/test_cli_render_golden.py
- tickets-archive.md
- src/frob/gates/_todo_fmt.py
- tests/test_todo_fmt_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: 'scope-closure: the waived test file''s frob:tests targets live here'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: tests/system/test_cli_render_golden.py
  reason: 'scope-closure: doctor_runner.run''s frob:tests evidence lives here'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: tickets-archive.md
  reason: T-1365 also clears the TICK003 archive backlog and the PII012 token false
    positives the landed slice introduced
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/gates/_todo_fmt.py
  reason: T-1365 also clears the TICK003 archive backlog and the PII012 token false
    positives the landed slice introduced
  actor: logan
  at: '2026-08-01'
- op: add
  glob: tests/test_todo_fmt_gate.py
  reason: T-1365 also clears the TICK003 archive backlog and the PII012 token false
    positives the landed slice introduced
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_todo_fmt_gate.py::TestTodo001BareComment::test_no_todo_token_no_violation
designated_repro_test: null
acceptance:
- text: given main, when frob check --only gates runs, then gate:PII and gate:TICK
    report 0 errors
  evidence:
  - tests/test_todo_fmt_gate.py::TestTodo001BareComment::test_no_todo_token_no_violation
threat: null
component: null
---
