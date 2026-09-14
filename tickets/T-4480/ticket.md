---
id: T-4480
title: FMT001 test and gate must accept the T-4475 noqa-suffixed over-limit directive
  line
state: in-progress
kind: bug
origin: agent
created: '2026-09-14'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_todo_fmt.py
- tests/gates_suite/test_fix_engine.py
- src/frob/gates/_fmt_directives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34817719845 (main 316b99eec), ubuntu+macOS: tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean fails on `assert all(len(line) <= limit for line in rewritten.splitlines())`. Since T-4475/T-4477 the canonicalizer deliberately emits ONE over-limit physical line carrying `# noqa: E501` when a directive token cannot fit. The test's invariant must become: every physical line either fits the limit or ends with the noqa marker AND the remaining lines are E501-clean (run the real `ruff check --select E501` on the rewritten file as T-4475's own tests do), and the FMT001 re-verify must stay clean -- which means the FMT001 detector in src/frob/gates/_todo_fmt.py must also treat a noqa-suffixed over-limit line as compliant (the T-4477 agent flagged that gap: FMT001 is a raw len(line) check). Fix both so gate and test agree on the canonical form. Sprint v0.531.0 (CI green blocker).
