## Done report

Changed:
- src/frob/app/release_runner.py::run (no code change; test-side fix below)
- src/frob/app/stats_runner.py::run (split into a thin `quiet_stdout_logs()` wrapper)
- src/frob/app/stats_runner.py::_run_body (new, carries the former `run` body + its ARCH103 waiver)
- src/frob/app/perf_runner.py::_hot (wraps `_hot_json` in `_run_quiet_if_json`)
- tests/unit/test_app_runners_batch5.py::TestReleaseRunner.test_stamp_err_result_exits_1 (stub signature fix)
- tests/test_coverage_wait_shared.py::TestWorktreeLock.test_uses_daemon_lease_when_daemon_up (sets FROB_DAEMON=1)

Per-failure disposition:
1. `TestReleaseRunner::test_stamp_err_result_exits_1` -- TEST bug. T-1381 added an
   `allow_unbumped` kwarg to the production `stamp()` call
   (`release_runner.py:63`); the test's monkeypatched lambda stub was never
   updated to accept it, so it raised `TypeError`. Fixed the stub
   (`lambda root, snap, ver, **kwargs: Err("nope")`); production code was
   already correct.
2. `TestStatsRunner::test_json_mode_prints_json` -- PRODUCTION bug.
   `stats_runner.run` never wrapped its `--json` path in
   `quiet_stdout_logs()`, unlike every sibling `--json` runner
   (`gitlog_runner`, `map_runner`, `perf_runner._heat`, ...) -- so
   `frob.app._daemon_proxy`'s "computing frob_stats in-process" INFO line
   and `frob.tickets`' ticket-loader DEBUG line leaked onto stdout ahead of
   the JSON payload, breaking `json.loads` on the caller side. Fixed by
   splitting `run` into a thin wrapper (applies `quiet_stdout_logs()` when
   `cfg.stats_json`) plus `_run_body` (the original logic, unchanged) --
   the same shape every other `--json` runner already uses.
3. `TestHotSortKeyMetricSelection::test_by_p90_and_by_p50xcount_disagree_on_order`
   and `TestPersistRunUnattributedExclusionAndWeightSum::test_only_attributed_section_persists_with_summed_weight`
   -- PRODUCTION bug, same root cause as (2) in a different runner:
   `perf_runner._hot`'s `--json` branch called `_hot_json` directly,
   without the `_run_quiet_if_json` wrapper `_heat`/`_collect` already use
   for exactly this reason, so `frob.app._daemon_proxy`'s "computing
   frob_perf_hot in-process" line leaked into `--json` stdout. Fixed by
   routing `_hot_json` through `_run_quiet_if_json`.
4. `TestWorktreeLock::test_uses_daemon_lease_when_daemon_up` -- TEST bug,
   stale relative to a legitimate, already-shipped design change. T-1126
   wrote this test to assert that a *live* daemon socket alone is enough
   for `_worktree_lock` to use the daemon-lease RPC. T-1379 (landed later,
   `c427d733`) deliberately made the daemon path **opt-in**
   (`FROB_DAEMON=1`) rather than opt-out, specifically because of known
   T-1378 daemon defects -- a live socket is no longer sufficient by
   itself. The test never picked up that contract change. Fixed by adding
   `monkeypatch.setenv("FROB_DAEMON", "1")` so the test actually exercises
   the lease path its name describes; `_daemon_enabled()`/`_worktree_lock`
   were left untouched (T-1379's behavior is correct and intentional).

Also fixed, discovered by `frob check --ticket T-1392` after the above:
`stats_runner.py`'s pre-existing `frob:waive ARCH103` directive (T-0977)
rode along onto the new private `_run_body` when `run` was split (COV005
correctly flagged this) -- moved the waiver onto `_run_body` (where the
branching logic it describes now lives) and added an honest `frob:waive
COV005` explaining the rebind is deliberate. `frob:waive AFFECT001` added
on `stats_runner.run` (docs/modules/app.md#runners' one-line summary is
still accurate and docs/** is under an active T-1235 lease this ticket
cannot touch).

Merged `main` mid-ticket (`eb6e4b23`/`b6243056`, unrelated concurrent
landings) to pick up a sibling fix to `src/frob/logging/handler.py`'s
DOC002 anchor before re-checking.

Full-suite verification: ran the complete unscoped suite twice
(`uv run pytest -q -p no:randomly -n 4`) -- both runs reached 100% with
the five target failures passing and no other FAILED lines, except one
discovery below. Per playbook section 3b, all later re-verification
(the five targets, each touched test file, and the production modules'
covering test files) was run foreground with an explicit `timeout`,
never backgrounded.

Disclosed cut: the full unscoped suite run also surfaced ONE additional
failure, `tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge`,
which passes standalone in 0.45s -- an xdist-parallel-run flake, not one
of this ticket's five named failures and not touched by this diff. Not
fixed here (out of scope); filed as T-1393.

Filed: T-1393 (xdist flake above), T-1394 (pre-existing,
out-of-scope `src/frob/logging/handler.py` COV001 x2: `_LazyStdoutHandler.stream`/
`_LazyStderrHandler.stream` are public with no `frob:doc` edge -- confirmed
pre-existing on `main`, not caused by this diff, `handler.py` never touched).

Gates: `frob check --ticket T-1392` -- every ticket-scoped gate family
(gate:SCOPE, gate:PREWORK, gate:FMT, gate:AFFECT, and the diff-driven
COV002/TODO001 checks inside gate:COV) reads 0 errors. `ruff check .`,
`ruff format --check .`, and `ty check src/frob/` all pass repo-wide.
Remaining unscoped `gate-summary` errors (`gate:COV` 2, the handler.py
COV001 pair above) are repo-wide, pre-existing, and outside this ticket's
declared scope per the gate's own `gate:scope-note` disclosure -- tracked
as T-1394, not silently left unaccounted for.
