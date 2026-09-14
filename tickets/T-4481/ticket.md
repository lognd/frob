---
id: T-4481
title: test_ci_workflow_self_gate_does_not_swallow_errors pins the pre-T-4460 self-gate
  run line
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
- tests/gates_suite/test_test_gate.py
- .github/workflows/ci.yml
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
CI run 34817719845 (main 316b99eec), ubuntu+macOS: tests/gates_suite/test_test_gate.py::TestTestGate::test_ci_workflow_self_gate_does_not_swallow_errors fails: it asserts the literal `run: uv run frob check\n` exists in .github/workflows/ci.yml, but T-4460 changed the self-gate step to `set -o pipefail; uv run frob check | tee "$RUNNER_TEMP/frob-check.log"` so the job summary can read the output. Update the test to assert the new shape while keeping its intent (T-1265: the self-gate's exit code must not be swallowed): assert the step's run script pipes `uv run frob check` through tee ONLY with `set -o pipefail` in effect (or uses a `tee` form that preserves the exit status), and still fails on a plain `... || true` / `; true` swallow. Sprint v0.531.0 (CI green blocker).
