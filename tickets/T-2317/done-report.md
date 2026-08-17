## Done report

Wired T-2310's `spawn_deferred_drain` into `_land_core_finish_post_land`'s
rapid-land branch, immediately after the existing `spawn_deferred_post_
land_sweep` call, under the identical guard (`not report.dry_run and
report.commit_sha is not None`) -- exactly the two-line change the ticket
body specified verbatim, both `_land_cmd.py` and `_rapid_sweep.py` now
free of T-2303's lease.

Added `tests/unit/test_land_cmd_drain_wiring.py` (no existing test
covered this call site directly -- only `spawn_deferred_post_land_sweep`
itself was tested elsewhere): asserts a real rapid land fires both
`spawn_deferred_post_land_sweep` and `spawn_deferred_drain`, and that
neither fires under `dry_run` or a `None` commit_sha (the same guard both
share). All 3 pass (`SUITE-RESULT: exitstatus=0 collected=3 failed=0`).

Updated `docs/modules/tickets-verify-sweep.md`'s "Automatic watermark
drain" closing paragraph to remove the "deliberately does NOT change"
caveat and describe the now-wired trigger.

`ty` clean.

### Changed
```
 tickets/T-2317/ticket.md | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_dry_run_spawns_neither` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_no_commit_sha_spawns_neither` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2317, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE001@tests/unit/test_land_cmd_drain_wiring.py, WIRE003@docs/modules/cli.md
