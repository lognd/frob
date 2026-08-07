## Done report

## Done report

Changed: tests/system/conftest.py::run
Changed: docs/guides/agent-playbook.md (new section 5b)
Changed: tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_strips_dispatch_agent_env_vars
Changed: tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_explicit_env_can_still_set_frob_agent

Evidence: tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_strips_dispatch_agent_env_vars,
tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_explicit_env_can_still_set_frob_agent
(both recorded via `frob ticket evidence`); manual repro re-run of the ticket's own
reproduction (`FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run pytest tests/system/test_cli_check.py`)
now passes bare and under the leaked env, confirming the fix; full
`tests/system/test_run_helper_env_leak.py tests/system/test_cli_check.py` (38 tests) green.

Filed: T-0909 (system tests bypassing run() helper still leak
FROB_AGENT/FROB_WORKTREE -- test_cli_check.py::TestFrobTomlCheckDefaults,
test_cli_ticket.py::TestTicketNewNonInteractive use bare subprocess.run, out
of T-0880's scope), T-0908 (in-process system tests -- test_spawn_budget.py,
test_cli_sys_plan.py -- leak FROB_WORKTREE into the worktree-lease guard via
direct library calls, a different mechanism than the run()-subprocess leak
T-0880 fixes, also out of scope)

Gates: `frob check --ticket T-0880` clean across gates-fast, gates-native,
gates-security, lint, static (--only stage groups, per FROB_AGENT chunking
requirement). `frob test --base main` stalled/timed out in this session
(matches the coordinator's known-hang caution); substituted targeted
`pytest tests/system/test_run_helper_env_leak.py tests/system/test_cli_check.py`
(38 passed) plus the per-stage `frob check` gate:TEST pass already covering
touched-set binding as the verification evidence instead.

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_strips_dispatch_agent_env_vars` (pytest node id, verified passing when recorded)
- `tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_explicit_env_can_still_set_frob_agent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
