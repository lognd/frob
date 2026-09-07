---
id: T-4154
title: 'ty check: exclude .claude/worktrees to stop nested-worktree false positives'
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
- tests/unit/test_check.py
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
Found while working T-3931 (scaffold day-one gate noise). With implementer
agents dispatched into .claude/worktrees/agent-*/ (or via `frob ticket
work`), the main checkout's `frob check` ty stage scans those worktrees
too and reports unresolved imports for files that exist only on their own
unmerged branch. frob creates this directory itself; it should not need a
per-project [tool.ty]/[tool.ruff]/[graph].exclude waiver to keep ty out of
it.

FIX (drafted, reverted from T-3931 due to a lease conflict): in
src/frob/check/_python.py::_ty_base_cmd, append
["--exclude", ".claude/worktrees/**"] to the `ty check` argv
unconditionally (ty supports --exclude as a gitignore-style glob per
`ty check --help`) -- mirrors the same nested-worktree pruning
frob.excludes._is_nested_worktree already gives frob's own graph build,
extended to the one external-tool subprocess invocation that walks the
filesystem itself and has no knowledge of that convention.

Draft test (tests/unit/test_check.py, in the TestRunTy class):
test_nested_claude_worktrees_are_excluded -- asserts "--exclude" and
".claude/worktrees/**" appear in the ty argv `_run_ty` builds.

BLOCKED: src/frob/check/_python.py is currently leased by in-progress
T-3887 (the bare-pytest/coverage-runner PATH fix, unrelated to this
change but the same file). Start this once T-3887's lease frees.
