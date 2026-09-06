## Done report

Fixed both tests named directly in T-4055's own history
(test_serves_one_request_then_idle_exits, test_stale_socket_file_is_replaced)
by replacing their fixed `thread.join(timeout=5); assert not
thread.is_alive()` wall-clock bet with a poll-until-dead-or-30s-deadline loop,
and dropped test_stale_socket_file_is_replaced's `@pytest.mark.flaky` rerun
marker (a prohibited retry-based mask of the same nondeterminism). Verified
15/15 clean runs under `-n 4 --dist=loadgroup` (matching ubuntu-latest's real
worker count) in isolation, plus repeated clean runs under added file-level
load.

Mined 23 recent ubuntu-latest CI job logs via `gh api
repos/{owner}/{repo}/actions/jobs/<id>/logs` and the SUITE-RESULT markers
tests/conftest.py already emits, to enumerate the flake population beyond the
3 samples in the ticket body -- found 6 distinct genuinely-intermittent tests
(now recorded in the ticket body above), plus a 7-test cluster that failed
together in one run (shape: shared xdist resource, not classified further --
out of this ticket's declared scope) and a separately-flagged 5-run cluster
that is a real bug window, not a flake, and should not be treated as part of
this population. Addressed the coordinator's mid-task correction (macOS also
flakes, on tests/unit/test_graph_cache.py) by folding it into the enumeration
and confirming it does not indicate an ubuntu/macOS xdist-worker-count
config difference (pyproject.toml addopts is `-n auto --dist=loadgroup` for
both legs identically; the runner core-count difference, not config, is
what varies).

Filed T-4066 for the out-of-scope tests
(test_ticket_runner_archive_force.py x2, test_check_runner.py,
test_check_tool_unavailable.py cluster) rather than expanding T-4055's own
declared scope (tests/test_serve_socket.py) to cover them, per this ticket's
own instruction not to skip past enumeration into an ever-widening fix.

### Changed
```
 tests/test_serve_socket.py         | 25 +++++++---
 tickets/T-4055/ticket.md           | 95 +++++++++++++++++++++++++++++++++++++-
 tickets/T-4066/ticket.md | 50 ++++++++++++++++++++
 3 files changed, 162 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestRunSocketDaemon::test_stale_socket_file_is_replaced` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 4 error(s), 4418 warning(s), 932 waived
- error-findings: DOC006@tickets/T-3998/ticket.md, PERF003@tests/test_serve_socket.py, PRE001@tickets/T-4055, SCOPE002@tickets.md
