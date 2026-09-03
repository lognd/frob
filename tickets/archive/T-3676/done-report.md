## Done report

Added frob:waive SEC110 directives at the 5 os.environ["FROB_WORKTREE"]/
os.environ.get("FROB_WORKTREE") reads in
tests/ticket_land_suite/test_wip.py::TestWorktreeLeaseEnvIsolation --
these tests deliberately mutate/read FROB_WORKTREE directly (bypassing
monkeypatch) to prove T-3123's autouse leak-isolation fixture in
tests/conftest.py actually isolates it. FROB_WORKTREE is a local
filesystem worktree path, never a secret.

Evidence: `timeout 300 uv run frob check --only secrets` -- 0 gate:SEC
findings for this file (the bucket-list's originally-cited location,
.claude/hooks/*.py, did not match the current log; the log's actual 5
SEC110 sites, tests/ticket_land_suite/test_wip.py:236,237,249,264,286,
are the ones fixed here).

### Changed
```
 tests/ticket_land_suite/test_wip.py |  5 +++++
 tickets/T-3676/ticket.md            | 13 +++++++++++++
 2 files changed, 18 insertions(+)
```

### Evidence
- `tests/ticket_land_suite/test_wip.py::TestWorktreeLeaseEnvIsolation::test_a_leaves_frob_worktree_set_like_apply_agent_env_does` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_wip.py::TestWorktreeLeaseEnvIsolation::test_b_does_not_see_a_leaked_frob_worktree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 15 error(s), 4249 warning(s), 904 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PERF003@src/frob/refactor/_scan.py, PRE001@tickets/T-3676, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
