## Done report

T-1355 shipped `land(allow_cross_ticket=...)` as the escape hatch for its
own new CrossTicketLeakage refusal, fully implemented and tested at the
library level, but with no way to reach it from the CLI. That turned a
guard with known false positives into an unconditional block.

It went from theoretical to blocking within hours:

- T-1355 and T-1356 mutually deadlocked on their own lands (each is the
  other's still-open sibling on a shared series branch). Recovered only
  because T-1358's land had already merged the branch, so both could be
  closed directly on main.
- T-1371, a repo-wide EXHAUST drain touching 38 files, is refused by FOUR
  open tickets at once -- T-1344, T-1345, T-1346 and T-1350 -- purely
  because those are epics whose umbrella scopes (`src/frob/gates/**`,
  `src/frob/tickets/**`) legitimately cover their own leaves' files.

Wired `--allow-cross-ticket` through the three links the value has to
cross: parser dest, `AppConfig.from_external`'s bool-field list, and the
`land()` call in `_land`. Tests pin all three plus both flag states,
because every historical break in this chain was a missing wiring step,
not a logic bug -- and a flag stuck always-True is as broken as one stuck
always-False.

This is an override, not a fix. T-1370 tracks teaching the guard about
series worktrees and epic/leaf ancestry so the false positives stop
needing an override at all.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketReachesLand::test_land_receives_the_keyword[True]` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketReachesLand::test_land_receives_the_keyword[False]` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketReachesConfig::test_from_external_carries_the_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 1594 warning(s), 697 waived
- error-findings: E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215, PRE001@tickets/T-1369, SELFAUDIT001@design
