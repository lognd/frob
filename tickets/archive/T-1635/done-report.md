## Done report

Found and fixed five distinct, independently-reproduced shared-resource/
timing-assumption bugs behind the residual intermittent-failure set T-1596
handed off:

1. tests/test_serve_socket.py::TestShutdownReapsChildren::
   test_frob_shutdown_exits_and_reaps_within_budget and
   tests/test_serve_watch.py::TestWatchThread's two prompt-exit tests
   asserted 5.0s wall-clock ceilings sized for an unloaded machine.
   Reproduced failing on demand under a real full-suite `-n auto` run.
   Production's real budget (_CHILD_REAP_GRACE_S = 1.0s) is untouched;
   widened the test-side CI-safety margin to 20s and made
   test_stop_joins_promptly poll the thread's actual exit instead of
   trusting WatchThread.stop()'s own internal 5.0s-bounded join alone.

2. src/frob/gates/_suppress.py::_mypy_diagnostics never pinned mypy's
   --cache-dir, so it defaulted to `.mypy_cache` resolved against the
   process CWD -- shared across every pytest-xdist worker's own
   concurrent mypy oracle invocation. Reproduced a torn/stale
   incremental-cache read returning zero diagnostics for a file with a
   real one (TestSuppress001Gate::
   test_ty_suppressed_mypy_unsuppressed_fires: "assert 0 == 1"). Fixed
   by pinning --cache-dir under the caller's own root (no behavior
   change for real `frob check` runs, where cwd already equals root).

3. tests/test_tickets_ledger_concurrency.py's three racing-thread tests
   used a 5s Barrier timeout / 5-10s join timeouts. Reproduced
   "AssertionError: None" under xdist load -- a BrokenBarrierError
   inside the thread body left the nonlocal result unset. Widened to a
   shared _CONCURRENCY_TIMEOUT_S = 30 constant; locking behavior under
   test is unaffected.

4. tests/test_ticket_land.py::TestClaimDivergencePostMerge's two
   T-0832-regression assertions checked `"-1" not in <message
   containing the randomly-minted T-draft-<hex> ticket id verbatim>`.
   Reproduced failing once in three consecutive runs on an unchanged
   tree, purely from the random hex id spelling "...draft-1..." by
   coincidence (~1/16 chance per run, independent of load). Fixed by
   stripping the ticket id out of the string before the check.

5. tests/test_registry_exhaustiveness.py's two reg008 burn-down tests
   call `build_graph` against this repo's own real checkout root, the
   identical shape T-1433 already diagnosed (unbounded fcntl.flock over
   .frob/derived.lock plus full-repo-parse peak memory). Reproduced a
   pytest-timeout kill with a faulthandler dump showing one thread
   blocked inside derived_state_lock and "node down: Not properly
   terminated". Extended the existing, already-justified
   _SELF_SCAN_HEAVY_NAME_SUBSTRINGS xdist_group mechanism to these two
   tests -- isolating them onto a synthetic tmp_path instead is not
   available, since they exist specifically to check the real repo's
   own registry.

ACCEPTANCE STATUS: NOT fully met. Achieved two clean-in-a-row full-suite
runs (both SUITE-RESULT exitstatus=0 collected=8584 failed=0) after each
fix round, but never reached ten consecutive. The failures encountered
after fix rounds 1-3 (test_json_output JSONDecodeError on empty stdout;
repeated pytest-timeout "Timeout (0:01:40)!" kills late in a run) were
investigated and traced to REAL, ambient host-wide CPU contention from
OTHER concurrent agent worktrees on this SAME machine (directly observed
via `ps aux`: this repo's own coordinator `frob check --budget 300`,
plus w29-tick/t-1634 and w29-dead worktrees each running their own
heavy `frob check`/ProcessPoolExecutor gate runs concurrently with this
suite's own 12 xdist workers) -- not a polluter inside this repo's test
suite. This matches this project's own documented WSL-OOM-session
history (multiple concurrent agent sessions oversubscribing a 12-core
box). Every failure actually attributable to an in-repo shared-resource
or timing bug (5 classes above) was found, reproduced, and fixed; no
class recurred after its fix.

Residual: could not certify 10/10 clean while sibling agent sessions are
concurrently loading the same host. Re-running the acceptance loop with
no concurrent sibling agents active would be the clean way to confirm
whether the remaining flakiness is fully gone; that condition was not
available during this session.

Filed T-1654 (scope tests/**) to audit the other files sharing
class 5's build_graph(real root) shape that were not reproduced failing
this round: test_waive_gate.py, test_graph.py, test_dup.py,
test_gates.py, test_secrets_gate.py, test_vet.py.

### Changed
```
 src/frob/gates/_suppress.py              | 19 +++++++++-
 tests/conftest.py                        | 25 +++++++++++++
 tests/test_serve_socket.py               | 27 +++++++++++---
 tests/test_serve_watch.py                | 34 +++++++++++++++--
 tests/test_ticket_land.py                | 19 +++++++++-
 tests/test_tickets_ledger_concurrency.py | 40 +++++++++++++-------
 tickets.md                               | 64 +++++++++++++++++++++++++++++++-
 7 files changed, 202 insertions(+), 26 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 2910 warning(s), 850 waived
- error-findings: none (measured, zero errors)
