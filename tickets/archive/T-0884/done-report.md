## Done report

## Done report

Changed: src/frob/app/ticket_runner.py::_run_pytest_directly
Changed: src/frob/app/ticket_runner.py::_WORKTREE_LEASE_ENV_VARS
Changed: tests/test_ticket_runner_pytest_env.py::TestRunPytestDirectlyStripsLeaseEnv

Evidence: tests/test_ticket_runner_pytest_env.py::TestRunPytestDirectlyStripsLeaseEnv::test_strips_worktree_and_agent_env, tests/test_ticket_runner_pytest_env.py::TestRunPytestDirectlyStripsLeaseEnv::test_missing_lease_env_is_fine (both recorded via frob ticket evidence); manual repro confirmed tests/test_ticket_land.py::TestLand now passes when spawned by _run_pytest_directly with FROB_WORKTREE/FROB_AGENT set in the caller's own env (the exact leak scenario T-0884 describes).

Filed: none

Gates: frob check --ticket T-0884 clean across gates-fast, gates-native, gates-security, lint, static (--only stages, per FROB_AGENT chunking requirement); frob test --base main PASS (python exit=0)

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_runner_pytest_env.py::TestRunPytestDirectlyStripsLeaseEnv::test_strips_worktree_and_agent_env` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_pytest_env.py::TestRunPytestDirectlyStripsLeaseEnv::test_missing_lease_env_is_fine` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
