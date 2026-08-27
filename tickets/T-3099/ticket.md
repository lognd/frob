---
id: T-3099
title: Wire T-3094 apply_agent_env/warn_if_xdist_bound_missing into pytest-spawn call
  sites
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/testing/_collect.py
- src/frob/testing/_coverage_refresh.py
- src/frob/app/mutate_runner.py
- src/frob/app/perf_runner.py
- docs/guides/agent-playbook.md
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
T-3094 added apply_agent_env(root) and warn_if_xdist_bound_missing(root) to
src/frob/tickets/_worktree_guard.py: the first mutates the CURRENT process's
os.environ with the T-2221 fleet-aware PYTEST_XDIST_AUTO_NUM_WORKERS bound
(so a child subprocess.run inherits it with no shell eval hop), the second
logs loudly when a fleet context is detected but the bound is absent from
the environment.

Neither is wired into any actual pytest-spawn call site yet -- that spans
files outside T-3094's single-file scope (src/frob/tickets/_worktree_guard.py
only). The known call sites that spawn pytest as a subprocess and would
benefit:

  - src/frob/app/ticket_runner/_verify.py (_run_pytest_directly)
  - src/frob/testing/_collect.py (collect_python_tests)
  - src/frob/testing/_coverage_refresh.py (the make-coverage pytest recipe)
  - src/frob/app/mutate_runner.py, src/frob/app/perf_runner.py
  - the frob CLI's own main() entrypoint, early enough to cover every
    subcommand that eventually shells out to pytest (frob check, frob test)

WHAT IS WANTED
- Call apply_agent_env(root) once, early, in the frob CLI process (or at
  minimum at the start of frob check/frob test) so every pytest subprocess
  frob itself spawns inherits the bound automatically.
- Call warn_if_xdist_bound_missing(root) immediately before each of the
  pytest-spawn call sites above, so a missing bound is visible in that
  process's own log.
- Update docs/guides/agent-playbook.md's eval "$(uv run frob agent env ...)"
  guidance: the eval-only mechanism is still needed for an agent's own RAW
  shell pytest invocation (a case apply_agent_env cannot reach -- it only
  affects the process it runs in and that process's children), but the
  playbook should say so explicitly now that an in-process alternative
  exists for frob-orchestrated test runs.

ACCEPTANCE
- Under a live multi-agent fleet, PYTEST_XDIST_AUTO_NUM_WORKERS is present
  in frob check/frob test-spawned pytest worker processes, verified via
  /proc/<pid>/environ of running workers (same evidence standard T-3094
  used).
- warn_if_xdist_bound_missing fires in frob's own log output when a fleet
  context exists and the bound did not make it into a spawn.
