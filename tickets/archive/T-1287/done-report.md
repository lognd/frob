## Done report

Verified each of the three 0.0%-branch flagged symbols against the T-1279 stale-stamp
precedent before writing any new code.

- server.py::build_server: exercised by TestBuildServer.test_registers_all_five_tools,
  which calls build_server(tmp_path) directly and asserts the exact set of 10
  registered MCP tool names -- real behavioral coverage, not import-only.
- server.py::run_stdio: run_stdio itself calls build_server, _start_daemon, and
  server.run(transport="stdio"); its internal _require_mcp() branch is exercised
  by test_require_mcp_raises_when_unavailable (simulated ImportError -> McpUnavailable),
  and its delegation path is covered indirectly via
  TestServeRunner.test_run_delegates_to_run_stdio_with_resolved_root (frob/app/serve_runner.py).
- _daemon.py::daemon_status: called directly and asserted against in
  TestPollRebaseBot.test_conflicting_branch_warns (status.rebase_warnings == warnings)
  and test_clean_branch_no_warning, both real git-worktree-backed behavioral tests.

All four existing tests were run scoped (tests/test_serve.py::TestBuildServer,
tests/test_serve_daemon.py::TestPollRebaseBot) and pass. No new tests were needed --
this is a stale coverage-stamp finding, matching the T-1289/T-1291/T-1292/T-1308
precedent. No dead code found; all three symbols have live callers/entry points.

### Changed
```
 tickets.md | 20 ++++++++++++++++----
 1 file changed, 16 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_serve.py::TestBuildServer::test_registers_all_five_tools` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestBuildServer::test_require_mcp_raises_when_unavailable` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBot::test_clean_branch_no_warning` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 489 warning(s), 679 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design
