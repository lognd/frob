## Done report

On the GitHub Windows runner, tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering failed because the eval'd output of frob agent env arrived as UTF-16 (NUL-interleaved bytes) under the runner's bash (CI runs 34675057655 and 34708801531, Windows leg). Fix: _force_utf8_stdout() in the agent-env runner reconfigures sys.stdout to UTF-8 at the top of _run_env so the emitted shell script is byte-stable regardless of PYTHONIOENCODING or the console code page; new test test_stdout_is_utf8_even_under_forced_utf16_ioencoding forces PYTHONIOENCODING=utf-16 and asserts no NUL bytes. Measured on the winrun Windows mirror: with the fix removed the new test fails with a UTF-16 BOM plus NUL-interleaved bytes; with the fix all 5 TestAgentEnvStdoutPurity tests pass on Linux and on the mirror (implementer measurement, 2026-09-12). The original Done report commit was lost when the post-land rapid sweep removed this worktree (T-4448); rewritten by the coordinator from the implementer's report.

### Changed
```
 src/frob/app/agent_runner.py | 30 +++++++++++++++++++++++++++++-
 tests/test_worktree_guard.py | 41 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-4446/ticket.md     |  8 +++++++-
 3 files changed, 77 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_diagnostics_still_appear_on_stderr` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_no_fleet_context_still_produces_valid_eval_output` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_is_utf8_even_under_forced_utf16_ioencoding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 4793 warning(s), 962 waived
- error-findings: PRE001@tickets/T-4446, TICK004@tickets.md
