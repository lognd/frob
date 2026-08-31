---
id: T-3589
title: 'Windows round 6: frob check itself hangs on win32 (child of tests/system/conftest.py''s
  first spawn)'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/system/conftest.py
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
Run 33390218738 (full-trace active), narrowed from 33385515507: the interrupt fires while tests/system/conftest.py:182 proc.communicate(timeout=...) waits on the suite's FIRST 'python -m frob check' child (test_cli_check.py:67; FROB=[sys.executable,'-m','frob'], no uv in the chain). Real defect: frob check itself hangs on win32, plausibly has NEVER completed there (the standalone-install job only runs 'frob --help'). Plan: (1) add a windows-only CI diagnostic step BEFORE the Test step running one bare frob check against a tiny fixture repo via a wrapper that arms a watchdog INSIDE the child (faulthandler.dump_traceback_later) so a hang names the exact frame; cap at 5 minutes. (2) make conftest run()'s TimeoutExpired path surface the drained child stdout/stderr in the raised error (currently swallowed). (3) if code reading alone reveals the cause (candidates: a gate spawning frob check --json children deadlocking on the T-3506 lock via a different lock than the bounded one; multiprocessing pool selection on win32 where forkserver does not exist -- check src/frob/gates/__init__.py's pool/_admission code path; a blocking stdin read), fix it in the same land.