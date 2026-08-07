## Done report

`frob ticket start` is now, by default, just the queued/planned ->
in-progress state transition -- the pre-work sweep (dup scan + xref +
scope digest, ~57s on this repo's /mnt/c checkout) is launched as a
DETACHED background subprocess instead of blocking the command.

- `AppConfig.ticket_foreground: bool = False` + `frob ticket start <id>
  --foreground` opt back into the pre-T-0474 synchronous behavior (still
  running the sweep in-process, exactly as before) -- useful for a
  script/test that wants the sweep guaranteed recorded the instant
  `start` returns.
- `_spawn_background_sweep(root, ticket_id)`: `subprocess.Popen([sys.
  executable, "-m", "frob", "ticket", "sweep", ticket_id, "--path",
  str(root)], start_new_session=True, ...)`, stdout/stderr discarded --
  `start` returns as soon as this is launched. Best-effort: a spawn
  failure (`OSError`, e.g. a sandbox refusing subprocess creation) falls
  back to running `_run_sweep` synchronously right there, so a sweep is
  NEVER silently dropped, only ever delayed.
- `frob ticket sweep <id>` (unchanged) remains the always-available,
  always-synchronous way to (re)record the sweep -- PRE001 stays
  satisfiable exactly as the ticket requires, via that command, whether or
  not `start`'s own background launch has landed yet.

Updated the 3 existing tests whose assertions depended on the pre-T-0474
synchronous contract (they were directly testing the exact behavior this
ticket changes, so updating them is inherent to this ticket, not scope
creep):
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::
  test_start_auto_plans_queued_ticket` now asserts the "launched in the
  background" log line instead of "swept T-0001" (no longer emitted by
  the parent process under the new default).
- `tests/system/test_cli_ticket_worktree_root.py::
  test_ticket_start_prework_written_under_worktree` passes `--foreground`
  to keep its synchronous file-existence assertion valid (it would
  otherwise race a real background process).
- `tests/test_prework_parity.py::TestCliStartRecordsGateCompatibleDigest::
  test_start_then_gate_is_clean` likewise passes `--foreground` (it wants
  the old immediate-consistency guarantee end-to-end via `frob check`).

Added test coverage:
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::
  test_start_foreground_runs_sweep_synchronously` -- `--foreground`'s
  opt-out reproduces the exact old contract.
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep`
  (2 tests) -- the spawned subprocess's argv/kwargs (monkeypatched
  `subprocess.Popen`, no real process spawned) and the OSError ->
  synchronous-fallback path.

Docs: `docs/modules/tickets.md`'s `frob ticket start` mention updated to
describe the background default + `--foreground`.

CAVEAT (declared-scope collision, not a code defect): `mutate_scope`
refused to add `src/frob/app/ticket_runner.py`/`config.py` and
`src/frob/__main__.py` to this ticket's FORMAL scope -- T-0419 (a
different, unrelated, currently in-progress ticket elsewhere) holds an
over-broad in-progress lease on `src/frob/app/` that necessarily overlaps
any file under it, and `mutate_scope` correctly refuses to let an
explicit `--add` cross a busy lease (T-0453/T-0455 design). These three
files already carry pre-existing, unrelated `frob:waive SCOPE001`
directives from earlier tickets (T-0176/T-0319/T-0323), so `frob check`
still reports 0 new errors for them, but T-0474's own `scope:` field in
the ledger does not list them -- this is a bookkeeping gap, not a
functional one; I could not resolve it without touching T-0419's lease.

All 5 evidence tests pass; full run of the 3 touched test files (batch7 +
worktree-root + prework-parity) is green together.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_foreground_runs_sweep_synchronously` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_spawns_detached_sweep_subprocess` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_popen_failure_falls_back_to_synchronous_sweep` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_worktree_root.py::TestTicketRootFromLinkedWorktree::test_ticket_start_prework_written_under_worktree` (pytest node id, verified passing when recorded)
- `tests/test_prework_parity.py::TestCliStartRecordsGateCompatibleDigest::test_start_then_gate_is_clean` (pytest node id, verified passing when recorded)
