## Done report

Repointed the stale frob:tests directive on run_drain_async's
test_green_round_advances_watermark_a_subsequent_round_sees edge: the
method was moved to a new class TestDrainAdvancesWatermarkEndToEnd
(alongside T-2324's fix) but the directive still cited the old
TestRunDrainAsync class, which no longer defines that method. This was
a genuine drift, not a false-positive stale blocker: DRIFT002 correctly
flagged "no longer resolves" because pytest could not find
TestRunDrainAsync.test_green_round_advances_watermark_a_subsequent_
round_sees anywhere. Verified the retargeted method still accurately
covers the described behavior (green round advances watermark; a
subsequent read sees the new watermark) by reading its body, then
repointed the directive and acked src/frob/verify/_drain.py::
run_drain_async. The blocked_by=T-2324 edge on the ticket did not
self-heal in the shown ticket frontmatter, but T-2324 is done on main
and its lease was clear, so ticket work proceeded without collision.

### Changed
```
 tickets/T-2337/ticket.md | 9 +++++++--
 1 file changed, 7 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd::test_green_round_advances_watermark_a_subsequent_round_sees` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2337/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2337, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md
