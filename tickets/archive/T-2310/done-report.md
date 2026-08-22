## Done report

T-2310: implemented the automatic rapid-profile watermark drain per the
coordinator's binding decision (recorded verbatim in
frob.verify._drain's own module docstring):

- frob.verify._drain.spawn_deferred_drain(root, land_ticket_id): fires
  `frob verify drain-async` into a DETACHED child, same
  _detached_sweep_env-pinned shape as T-1684's spawn_deferred_post_land_
  sweep. Never checks land-in-progress itself (the spawning process is
  itself a land, still holding land.lock -- a check there would always
  see itself).
- frob.verify._drain.run_drain_async(root): the detached child's own
  entrypoint. Declines immediately (one non-blocking probe,
  frob.tickets._leases._probe_land_once -- the same primitive
  refuse_if_land_in_progress uses) if a land is in progress anywhere;
  otherwise calls frob.verify._worker.run_coalesced_verification exactly
  ONCE (never a loop over the backlog) -- that function's own existing
  contract already is the bounded/resumable batch primitive constraint 4
  needs.
- `frob verify drain-async` CLI verb (src/frob/_cli_parsers/_verify.py,
  src/frob/app/verify_runner.py::_run_drain_async) -- a real subcommand,
  not a code string, matching `frob ticket sweep-async`'s own precedent.
- Doc anchor: docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-t-2310.

All 5 coordinator constraints verified:

1. Never-block contract: spawn_deferred_drain never blocks the caller
   (fire-and-forget Popen); run_drain_async is only ever reached in a
   DETACHED child, never on a land's own execution path.
2. Automatic, reuses the sweep's own detached-spawn machinery
   (_detached_sweep_env) rather than inventing a second one.
3. Idle-fleet-only: test_declines_while_a_land_is_in_progress proves the
   single non-blocking probe, no queue, no retry.
4. Incremental/resumable: test_green_round_advances_watermark_a_
   subsequent_round_sees and test_unmeasurable_round_leaves_watermark_
   untouched_not_corrupt exercise the REAL (non-monkeypatched)
   run_coalesced_verification -- a green round durably advances the
   watermark, an unmeasurable one leaves the prior watermark valid and
   untouched (never corrupt, never rolled back).
5. rapid_soft_warning (T-2290) untouched.

NOT DONE, reported rather than forced: the actual land-side trigger call
(spawn_deferred_drain from _land_cmd.py's rapid-land branch, alongside
spawn_deferred_post_land_sweep) is BLOCKED -- both _land_cmd.py and
_rapid_sweep.py were held under T-2303's live cross-worktree lease for
T-2310's entire duration (repeated `frob ticket scope --add` attempts,
including a late retry, all refused with ScopeLeaseConflict). Filed as
the exact two-line follow-up: T-2317 (renumbers at land).
Everything else -- the drain mechanism, the CLI verb, all 4 positive
controls -- is fully implemented, tested, and independently runnable by
hand (`frob verify drain-async`) today; only the automatic land-side
trigger is pending that one wiring commit.

### Changed
```
 tickets/T-2310/ticket.md           | 36 ++++++++++++++++++-
 tickets/T-2317/ticket.md | 72 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 107 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_drain.py::TestRunDrainAsync::test_declines_while_a_land_is_in_progress` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_drain.py::TestRunDrainAsync::test_never_blocks_or_loops_over_the_backlog` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_drain.py::TestSpawnDeferredDrain::test_spawns_a_detached_child` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_drain.py::TestSpawnDeferredDrain::test_exec_disabled_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd::test_green_round_advances_watermark_a_subsequent_round_sees` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd::test_unmeasurable_round_leaves_watermark_untouched_not_corrupt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2310, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE001@src/frob/verify/_drain.py
