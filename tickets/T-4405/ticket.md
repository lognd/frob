---
id: T-4405
title: frob agent env stdout is UTF-16-garbled under bash eval on Windows
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: 0.531.0
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
scope_changes:
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: actual implementation and test targets per scope-closure warnings
  actor: logan
  at: '2026-09-10'
- op: add
  glob: src/frob/app/agent_runner.py
  reason: actual implementation and test targets per scope-closure warnings
  actor: logan
  at: '2026-09-10'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3505
  reason: windows drain epic T-3505 covers this leaf
  actor: logan
  at: '2026-09-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34546329688, Windows leg only.

Node id: tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering

Assertion (verbatim):
    assert result.returncode == 0, result.stderr
E   assert 1 == 0
E    +  where 1 = CompletedProcess(args=[bash -c eval "$(python -m frob agent env ...)"],
        stdout contains bytes like "\x00s\x00t\x00r\x00o\x00>\x00' \x00t\x00o\x00 \x00i\x00n\x00s\x00t\x00a\x00l\x00l\x00.\x00\n\x00\n\x00" ...).returncode

The interleaved NUL bytes are the classic signature of UTF-16LE text being
read/written as if it were UTF-8/ASCII (each ASCII byte followed by a NUL
high byte) -- on Windows, a subprocess or file stream not explicitly
opened in text mode with an explicit encoding defaults to a platform
encoding that differs from Linux/macOS, and something in the `frob agent
env` emission path (or the git-bash pipe reading its stdout) is not
pinning UTF-8. The eval then chokes on the mis-decoded shell script,
returning a nonzero exit. Fix: audit the `frob agent env` command path for
any subprocess.run/Popen or open() call missing `encoding="utf-8"` (or a
BOM/UTF-16 default sneaking in via a Windows-specific stdout reconfigure),
declared with a sys.platform-aware comment if the root cause is
platform-specific. Do not skip the test -- stdout purity for eval is a
real cross-platform contract.