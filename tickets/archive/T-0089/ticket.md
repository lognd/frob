---
id: T-0089
title: test_scaffold_dx flaky under full-suite run, passes in isolation
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
blocked_by:
- T-0122
- T-0122
parent: null
tier: ticket
sprint: null
scope:
- tests/system/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
designated_repro_test: null
threat: null
component: null
---
tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately failed during a full uv run pytest -q but passes standalone; suspect shared graph cache or cwd contention between system tests. Found during T-0058 close-out. Also: pytest.mark.slow is unregistered (PytestUnknownMarkWarning).
## Done report

Not a test-side bug. Root cause chain: (1) T-0122 -- frob check ran
arch and gates concurrently in one ThreadPoolExecutor and a logging
save/restore race could leave the stdout handler stuck at WARNING, so
the final summary was swallowed while exiting 0; the scaffolded-project
test correctly flagged the missing summary. (2) T-0125 -- the root
thread-unsafety of quiet_stdout_logs, fixed with a lock + reentrancy
depth counter. With both fixes in the globally installed binary:
previously-flaky test passes 8/8 in an isolation loop and the full
tests/system suite passes 285/285 under -n auto (historic flake rate
was 1-in-4 to 1-in-8 full-suite runs). No changes to the test itself
were needed -- the T-0089 investigation (deterministic 6/12 OS-process
repro) is preserved in T-0122's ledger entry.