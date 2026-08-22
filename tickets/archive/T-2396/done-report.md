## Done report

Changed:
- .claude/hooks/root-write-guard.py (new file) -- _is_agent_context, _worktree_fact, _worktree_paths, _target_path, _is_ledger_path, _deny, main
- .claude/settings.json -- new PreToolUse matcher "Write|Edit|NotebookEdit" wiring root-write-guard.py
- .claude/hooks/sync-claude-config.py -- MANAGED gains (".claude/hooks/root-write-guard.py", "hooks/root-write-guard.py")
- docs/guides/claude-hooks.md -- new "root-write-guard.py" section
- tests/test_hook_root_write_guard.py (new file)

Evidence:
tests/test_hook_root_write_guard.py::test_agent_context_write_to_root_is_refused (accepts 0)
tests/test_hook_root_write_guard.py::test_worktree_fact_alone_is_sufficient_without_frob_agent (accepts 0)
tests/test_hook_root_write_guard.py::test_ledger_paths_are_exempt_even_for_an_agent (accepts 0)
tests/test_hook_root_write_guard.py::test_frob_land_internal_exempts_an_agent_write (accepts 0)
tests/test_hook_root_write_guard.py::test_notebook_edit_to_root_is_refused_for_an_agent (accepts 0)
tests/test_hook_root_write_guard.py::test_coordinator_or_human_write_to_root_is_allowed (accepts 1)
tests/test_hook_root_write_guard.py::test_fake_frob_worktree_value_does_not_satisfy_the_fact_check (accepts 1)
tests/test_hook_root_write_guard.py::test_agent_write_inside_its_own_worktree_is_allowed (accepts 1)
tests/test_hook_root_write_guard.py::test_non_guarded_tool_is_ignored (accepts 1)

Measured: `uv run pytest tests/test_hook_root_write_guard.py -p no:cacheprovider -q` ->
SUITE-RESULT: exitstatus=0 collected=9 failed=0

Empirical proof the discriminator discriminates BOTH ways (acceptance
criteria 1 and 2), against a REAL throwaway git repo with a REAL linked
worktree (git worktree add), not a mock:
- test_agent_context_write_to_root_is_refused: FROB_AGENT=1 +
  FROB_WORKTREE=<real linked worktree> writing into the primary checkout
  -> denied.
- test_worktree_fact_alone_is_sufficient_without_frob_agent: FROB_AGENT
  UNSET (the exact T-2071-measured gap), FROB_WORKTREE alone (validated
  against real `git worktree list`) -> still denied.
- test_coordinator_or_human_write_to_root_is_allowed: neither var set,
  identical target write -> allowed (stdout empty, no deny payload).
- test_fake_frob_worktree_value_does_not_satisfy_the_fact_check:
  FROB_WORKTREE pointed at a directory that is NOT a registered linked
  worktree -> allowed, proving _worktree_fact is a real structural check
  against `git worktree list`, not a bare env-var-presence check.

Filed: none.

Gates: `frob check --only gates-native --ticket T-2396` clean for this
ticket's own scope -- 6 repo-wide errors present (gate:ARCH ARCH103 in
src/frob/release/_cli.py, gate:DRIFT DRIFT001/DRIFT002 in
src/frob/app/ticket_runner/_rapid_sweep.py and docs/modules/vet.md,
gate:PERF PERF004/PERF003 in src/frob/app/ticket_runner/_new.py and
src/frob/gates/_debt_deprecated.py) are pre-existing and untouched by this
ticket's scope; `frob check --only lint --ticket T-2396` similarly shows
4 pre-existing errors outside scope (src/frob/verify/_worker.py,
src/frob/vet/_capability.py). gate:DUP (5 findings, this ticket's own new
test file duplicating sibling hook-test helper functions on purpose) and
claude-config-drift (1 finding, `frob claude sync` reconciled) both
resolved -- DUP001 waived with a reasoned precedent citation (each
standalone hook test file independently exercises its own hook's
stdin/stdout contract, matching the existing 3-file pattern), drift fixed
via `frob claude sync`.

### Changed
```
 tickets/T-2396/ticket.md | 25 ++++++++++++++++++++++---
 1 file changed, 22 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_hook_root_write_guard.py::test_agent_context_write_to_root_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_worktree_fact_alone_is_sufficient_without_frob_agent` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_ledger_paths_are_exempt_even_for_an_agent` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_frob_land_internal_exempts_an_agent_write` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_notebook_edit_to_root_is_refused_for_an_agent` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_coordinator_or_human_write_to_root_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_fake_frob_worktree_value_does_not_satisfy_the_fact_check` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_agent_write_inside_its_own_worktree_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_non_guarded_tool_is_ignored` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2396/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2396/src/frob/vet/_capability.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2396, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
