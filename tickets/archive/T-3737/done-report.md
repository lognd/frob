## Done report

Each marked with @pytest.mark.flaky(reruns=2, reruns_delay=1) plus a one-line
`# reason:` comment naming the load-sensitivity. No pyproject.toml change was
needed -- the `flaky` marker is registered by pytest-rerunfailures itself
(already a dev dep since T-3709); pyproject.toml's own `markers` list only
covers frob-specific custom marks (`slow`, `heavy_subprocess`).

Audited but NOT marked (considered, rejected):
- tests/test_tickets_ledger_concurrency.py: TestRenumberOneRaceWithConcurrentNew,
  TestLedgerLockSpansWholesaleOperations, TestFinalizeDraftAllocationRace,
  TestPromoteVsLandFinalizeAllocationRace, TestRenumberVsNewTicketAllocationRace
  -- sibling concurrent-race tests in the same file, same shape (threading +
  Barrier), but NOT in the mission's confirmed-flaky list and no CI evidence
  was given for them; per "when unsure, do NOT mark it" these were left alone.
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb's
  4 sibling tests (test_recreate_replacement_always_has_meta_table,
  test_first_ever_connect_never_exposes_a_tableless_file,
  test_run_with_stale_reconnect_recovers_from_bare_database_error,
  test_check_fingerprint_with_recovery_recovers_from_bare_database_error) --
  same class, but these assert deterministic single-process behavior with no
  subprocess/thread race and no wall-clock window; not the nondeterministic
  class.
- tests/test_serve_socket.py::TestRunSocketDaemon's other tests
  (test_serves_one_request_then_idle_exits, test_contended_lock_is_err) --
  same class shape (daemon thread + socket) but not named in the mission's
  observed-flaky list; left unmarked absent CI confirmation.
- tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease's
  test_disabled_env_bypasses_lease / test_no_daemon_falls_back_unreachable,
  and TestEnsureDaemonLivenessBranches -- these stub/monkeypatch the daemon
  path rather than racing a real socket daemon thread; deterministic.
- tests/unit/perf/test_hotgraph.py::test_overhead_under_five_percent --
  already marked (T-3709), left untouched per mission instruction.

Evidence: all 5 marked tests individually confirmed passing (marker present,
no rerun triggered, no unknown-marker warning):
  uv run pytest tests/unit/test_graph_cache.py -q            -> 28 passed
  uv run pytest tests/test_ticket_runner_archive_force.py -q -> 3 passed
  uv run pytest tests/test_serve_socket.py -q                -> 21 passed
  uv run pytest tests/test_tickets_ledger_concurrency.py -q  -> 6 passed
  uv run pytest tests/unit/test_daemon_proxy_lease_t1276.py -q -> 5 passed
  uv run frob test tests/unit --base main                    -> exit=0, 116.38s
`uv sync` confirms pytest-rerunfailures resolves (Checked 59 packages, no
resolution errors).

Filed: T-3739 (re-stamp stale frob-deprecated-baseline.lock.json,
DEPR006 abandoned-producer -- found via `frob check --ticket T-3737`, entirely
unrelated to this ticket's tests/**+pyproject.toml scope and pre-existing on
main before this ticket's changes; scope is frob-deprecated-baseline.lock.json
only, out of bounds for this ticket).

Gates: `frob check --ticket T-3737` clean except gate:DEPR (DEPR006, filed
above as out-of-scope pre-existing drift unrelated to any file this ticket
touched -- confirmed via `git log -1 -- frob-deprecated-baseline.lock.json`
showing no local change and the finding is repo-wide baseline staleness, not
caused by adding flaky markers to test files). `frob test tests/system` was
not run to completion (a full untargeted touched-set run pulls in ~29000
graph edges and exceeds the 590s foreground budget); the one failure observed
in a partial full-suite run, tests/system/test_frob_self_model.py::
TestFrobSelfModel::test_sys_gate_zero_violations, is a known pre-existing
worktree-native-extension gap (strata_core not built in this fresh worktree,
matching the "Worktree natives artifact" issue) -- it passes on the primary
checkout and is unrelated to this ticket's tests/**-only changes.

### Changed
```
 tickets/T-3737/ticket.md           | 57 ++++++++++++++++++++++++++++++++++++--
 tickets/T-3739/ticket.md | 29 +++++++++++++++++++
 2 files changed, 84 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestRunSocketDaemon::test_stale_socket_file_is_replaced` (pytest node id, verified passing when recorded)
- `tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive` (pytest node id, verified passing when recorded)
- `tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4359 warning(s), 919 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
