## Done report

Changed:
tests/test_gates.py::TestCoverageGate.test_cov006_third_file_reachable_chases_relative_import_reexport
tests/test_gates.py::TestFixEngineTierA.test_tick006_renamed_draft_resolved_via_git_not_refiled
tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty.test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr.test_wip_commit_failure_logs_stderr

Each of the four now carries an individual `frob:waive COV006` comment
scoped to its own `frob:tests` edge, citing the T-2550 call-graph-blindness
class (public entry point reached several hops from the bound private
target, invisible to `frob.graph.callgraph`'s name-based resolver) and
confirming the binding is genuinely exercised by direct read.

Evidence: the 4 node ids above, re-run green with `FROB_WORKTREE` unset
(the leased-worktree guard otherwise false-fails the two land_git_ops
tests, which spawn their own nested git worktrees -- an env artifact, not
a real failure): `SUITE-RESULT: exitstatus=0 collected=4 failed=0`.

Filed: none (T-2865 and T-2866 are this ticket's own siblings, split from
T-2370 before this ticket existed).

Gates: `frob check --only coverage --json` unbudgeted, worktree t-2370,
2026-08-22 -- COV006 warning count 0 (was 4 at start of this batch).
COV006 severity is NOT promoted and never will be: its own docstring
(`frob/gates/__init__.py::_cov006`) states WARN is permanent because
`frob.graph.callgraph` is an explicitly best-effort, name-based resolver
-- a miss is a prompt to double check, not proof of a bad binding. This
ticket's acceptance is zero live warnings only, by design.

### Changed
```
 tickets/T-2370/ticket.md | 114 +++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2865/ticket.md |   7 ++-
 2 files changed, 120 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_chases_relative_import_reexport` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_renamed_draft_resolved_via_git_not_refiled` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_wip_commit_failure_logs_stderr` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 37 error(s), 1384 warning(s), 796 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/graph.md, DOC006@tickets/T-2860/ticket.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
