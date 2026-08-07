## Done report

Added a background daemon thread to frob serve (src/frob/serve/_daemon.py),
started alongside the stdio MCP transport by run_stdio, running two jobs on
a repeating timer (default 20s, well inside the acceptance clause's
one-minute bar):

1. Post-land re-verify (poll_post_land): watches main's resolved HEAD via
   git rev-parse main. An unchanged HEAD is a cache hit (no re-work); a
   moved HEAD invalidates the warm graph/baseline/test cache and runs one
   frob_check_delta-equivalent pass plus (by default) the touched-set
   tests against main, publishing the result as a PostLandVerdict.
2. Rebase-bot (poll_rebase_bot): for every in-flight worktree branch
   (frob.tickets._leases.read_all_leases, the same T-0473 liveness signal
   `doable` already trusts), simulates merging current main into that
   branch with old-style `git merge-tree <merge-base> <branch> <main-head>`
   (this repo's git baseline is 2.34, predating the --write-tree form) --
   no checkout, no scratch clone, a single read-only subprocess against the
   shared git object store. A conflict is detected by `<<<<<<<` markers in
   that command's stdout (verified empirically: exit code is always 0 on
   this git version, conflicts only show up in the diff body). Every
   conflicting branch gets a RebaseWarning, replacing the full warning set
   for the root each cycle.

Both jobs write into one DaemonStatus cache per repo root; a new
frob_daemon_status() MCP tool (registered in server.py, exported from
frob.serve) reads it back verbatim as JSON, never triggering a poll
itself.

Both jobs are read-only against frob-owned state -- no ticket/lock/ledger
write, no worktree checkout, no branch switch; the only mutation is the
in-process DaemonStatus cache and, transitively through the warm-state
rebuild, the same .frob/cache.db the existing read tools already write.

docs/modules/serve.md gained a "Daemon jobs" section documenting both jobs,
the DaemonStatus/PostLandVerdict/RebaseWarning models, the merge-tree
conflict-detection mechanics for this repo's git baseline, and an updated
Deviations note. The Tools section and CLI section were updated to mention
frob_daemon_status and the new background daemon.

Acceptance demonstrated by tests (deterministic, no real sleeps for a
minute -- tests call poll_post_land/poll_rebase_bot/run_daemon_cycle
directly for a single-cycle assertion, and the one test that does exercise
the real background thread uses a tiny interval plus a threading.Event
wait, not a real minute):
- TestPollPostLand.test_head_moved_refreshes_verdict: a fresh commit on
  main moves HEAD; the next poll produces a new verdict with the new HEAD
  and a re-run delta -- demonstrating a fresh delta verdict becomes
  available without any agent invoking `frob check`.
- TestPollRebaseBot.test_conflicting_branch_warns: a real second git
  worktree on its own branch with a lease recorded, diverged from main on
  the same line of the same file; poll_rebase_bot publishes exactly one
  RebaseWarning naming that ticket/branch before any Done report would be
  written.
- TestPollRebaseBot.test_clean_branch_no_warning /
  test_no_leases_is_no_warnings: the negative cases (non-conflicting
  divergence, no in-flight leases at all) publish no warnings.
- TestFrobDaemonStatus.test_reads_current_status /
  TestRunDaemonCycle.test_runs_both_jobs_and_returns_status /
  TestStartDaemon.test_background_loop_runs_a_cycle_then_stops: the MCP
  tool, the single-cycle unit, and the real background thread all wired
  together correctly.
- TestBuildServer.test_registers_all_five_tools (tests/test_serve.py,
  pre-existing, updated): the new tool is registered alongside the
  existing eight.

Deviations: none from the ticket's plan. One pre-existing test
(tests/test_serve.py::TestBuildServer::test_registers_all_five_tools)
needed updating for the new tool name and was added to scope with a
reason, per the playbook's "touch only declared scope, file/scope
anything else" rule. One test-only flake was found and fixed during
verification: TestStartDaemon's real-background-thread test originally
used a 5s wait against a 0.01s poll interval, which was observed to fail
once under the full touched-set run (frob test --base main, many parallel
xdist workers spawning git subprocesses); widened to a 0.05s interval and
a 30s wait margin, re-verified clean under the same full touched-set run
afterward.

### Changed
```
 docs/modules/serve.md      |  75 +++++++++-
 src/frob/serve/__init__.py |   2 +
 src/frob/serve/_daemon.py  | 356 +++++++++++++++++++++++++++++++++++++++++++++
 src/frob/serve/_tools.py   |  29 ++++
 src/frob/serve/server.py   |  28 +++-
 tests/test_serve.py        |  11 +-
 tests/test_serve_daemon.py | 185 +++++++++++++++++++++++
 tickets.md                 | 100 ++++++++++++-
 8 files changed, 773 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_serve_daemon.py::TestPollPostLand::test_head_unchanged_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollPostLand::test_head_moved_refreshes_verdict` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBot::test_no_leases_is_no_warnings` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBot::test_clean_branch_no_warning` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestFrobDaemonStatus::test_reads_current_status` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestRunDaemonCycle::test_runs_both_jobs_and_returns_status` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestStartDaemon::test_background_loop_runs_a_cycle_then_stops` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestBuildServer::test_registers_all_five_tools` (pytest node id, verified passing when recorded)
