---
id: T-2865
title: Burn COV006 WARN findings to zero via individual waivers (never promote)
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
- tests/test_ticket_land.py
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
Split off T-2370: COV006's own docstring (frob/gates/__init__.py::_cov006)
states WARN severity is deliberate and unconditional -- frob.graph.callgraph
is an explicitly best-effort, name-based resolver, so a miss is a prompt to
double check, not proof of a bad binding. COV006 must NEVER be promoted to
ERROR regardless of count. This ticket is scoped to the individual-waiver
burn-down only; it will never satisfy a "promote to error" acceptance
criterion by design, and should close on zero live warnings alone.

Work already done in worktree .claude/worktrees/t-2370 (branch t-2370),
re-measured 2026-08-22 via unbudgeted `frob check --only coverage --json`:
wrote 4 individual `frob:waive COV006` comments citing the T-2550 class
(public entry point several hops from the private target, invisible to the
name-based call graph), each confirmed by direct read to be genuinely
exercised:
  - tests/test_gates.py::TestCoverageGate.test_cov006_third_file_reachable_chases_relative_import_reexport
    -> src/frob/gates/__init__.py::_cov006_resolve_relative_module
  - tests/test_gates.py::TestFixEngineTierA.test_tick006_renamed_draft_resolved_via_git_not_refiled
    -> src/frob/gates/_fix_engine.py::_resolve_via_git_rename
  - tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty.test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
    -> src/frob/tickets/_land_git_ops.py::_do_wip_commit
  - tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr.test_wip_commit_failure_logs_stderr
    -> src/frob/tickets/_land_git_ops.py::_do_wip_commit

Re-measured after writing: COV006 warning count is 0. Each waiver comment
verified with no trailing space before its backslash continuation and no
embedded quote in its reason string (T-2857 hazard).

Acceptance: zero COV006 warnings via `frob check --only coverage --json`
unbudgeted. Do NOT add an acceptance criterion to promote COV006 -- the
gate's own docstring forbids it permanently.