## Done report

Changed: tests/test_hook_root_write_guard.py (_make_repo_with_nested_worktree
fixture, test_agent_write_inside_a_nested_worktree_is_allowed)

Evidence: tests/test_hook_root_write_guard.py::test_agent_write_inside_a_nested_worktree_is_allowed
Verified manually: fails (denied) against pre-fix hook
(git show 39039b5f3^:.claude/hooks/root-write-guard.py), passes
(allowed) against current .claude/hooks/root-write-guard.py. Full
suite: 10/10 pass (9 pre-existing + this new case).

Filed: none (this ticket itself was filed for the regression-test gap
found while landing T-2394/reviewing T-2396's fix)

Gates: pytest tests/test_hook_root_write_guard.py 10/10 pass locally
(SUITE-RESULT: exitstatus=0 collected=10 failed=0)

### Changed
```
 tests/test_hook_root_write_guard.py | 55 +++++++++++++++++++++++++++++++++++--
 tickets/T-2442/ticket.md            |  4 ++-
 2 files changed, 56 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_hook_root_write_guard.py::test_agent_write_inside_a_nested_worktree_is_allowed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2442/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2442/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2442/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2442, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
