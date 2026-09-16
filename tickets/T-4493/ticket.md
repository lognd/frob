---
id: T-4493
title: SUPPRESS001 ty diagnostic correlation doubles the worktree path (root/.claude/worktrees/x/.claude/worktrees/x/...)
  and cannot read any file
state: done
kind: bug
origin: agent
created: '2026-09-15'
priority: medium
parent: null
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_suppress.py
- tests/unit/test_suppress_worktree_path.py
- tests/test_gates_suppress.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_suppress.py
  reason: existing TestRelativize.test_already_relative_path_passes_through encodes
    the exact wrong assumption (relative path is root-relative) this fix corrects;
    must update to cwd-relative semantics
  actor: logan
  at: '2026-09-15'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001/SYS100: new test file tests/unit/test_suppress_worktree_path.py
    writes real files via write_text under tmp_path, a genuine new fs.write capability
    site that must be declared in testsuite node''s via-list'
  actor: logan
  at: '2026-09-15'
- op: remove
  glob: design/frob.strata
  reason: 'no longer needed: rerouted the new test''s fs.write through an existing
    declared helper instead of adding a new capability site'
  actor: logan
  at: '2026-09-15'
evidence:
- tests/unit/test_suppress_worktree_path.py::TestRelativizeUnderNestedWorktreeRoot::test_correlate_reads_the_real_file_under_nested_root
designated_repro_test: tests/unit/test_suppress_worktree_path.py::TestRelativizeUnderNestedWorktreeRoot::test_correlate_reads_the_real_file_under_nested_root
acceptance:
- text: GIVEN frob check runs against a worktree under <root>/.claude/worktrees/<x>
    WHEN SUPPRESS001 correlates ty diagnostics THEN it resolves each diagnostic path
    once, relative to the worktree, and reads the file
  evidence:
  - tests/unit/test_suppress_worktree_path.py::TestRelativizeUnderNestedWorktreeRoot::test_correlate_reads_the_real_file_under_nested_root
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15 in the land log of T-4496: dozens of 'SUPPRESS001: could not read .claude/worktrees/t-draft-926571db/tests/... for ty diagnostic correlation: [Errno 2] .../frob/.claude/worktrees/t-draft-926571db/.claude/worktrees/t-draft-926571db/tests/...'. ty reports paths relative to the repo root while the correlation joins them onto the worktree path again. Every ty diagnostic in a worktree check is therefore uncorrelated: a silent zero for SUPPRESS001 inside worktrees. Find the real file first with git grep SUPPRESS001 -- src/frob/gates; adjust scope if it is not _suppress.py.