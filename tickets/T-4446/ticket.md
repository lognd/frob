---
id: T-4446
title: 'Windows CI: frob agent env stdout is UTF-16 under bash eval on the runner
  (successor to T-4405)'
state: queued
kind: bug
origin: agent
created: '2026-09-12'
priority: high
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/worktree_guard*.py
- src/frob/cli/agent_env*.py
- tests/test_worktree_guard.py
- src/frob/tickets/_worktree_guard.py
- src/frob/app/agent_runner.py
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
Successor to T-4405 (dropped wrong-premise; drop is terminal so this re-files it). Node id: tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering.
CI run 34675057655 Windows leg (head d0fc8ba1e) still fails tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering: the eval'd "frob agent env" output is UTF-16 (NUL-interleaved bytes visible in the captured args) under the runner's bash. The winrun mirror pass that justified the drop does not reproduce the runner's stdout encoding -- the drop was wrong-premise. Likely cause: the runner's python writes stdout as UTF-16 when PYTHONIOENCODING/console code page differ from the mirror; fix by writing the agent-env script bytes explicitly as UTF-8 (sys.stdout.buffer) or by the test decoding with the runner's encoding, measured with the same env the CI step sets.

ACCEPTANCE: (1) frob agent env emits UTF-8 bytes regardless of console code page / PYTHONIOENCODING (write via sys.stdout.buffer or reconfigure encoding at the CLI boundary), with a unit test that captures the raw bytes under a UTF-16 stdout and asserts no NUL interleaving; (2) measured on the mirror with PYTHONIOENCODING=utf-16 forced to reproduce, then clean; (3) CI Windows leg green on this node id on the next push. Sprint v0.531.0.
