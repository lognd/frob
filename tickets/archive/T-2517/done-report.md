## Done report

Widened fleet_status.py's forkserver reporting per the ticket's own
measurement: ORPHANED FORKSERVERS: 0 while 82 of 148 live forkservers
were stale (idle >1h) and held 12GB of swap, invisible because the
orphan test is init-reparented ancestry only and every one of these had
a live agent-shell parent.

Added a shared `_forkserver_snapshot` (pid/ppid/age_s/vmswap_kb from one
/proc walk) so the three numbers cost one scan, not three. Refactored
`orphaned_forkserver_count` onto it (same signature, same behavior --
existing tests pass unchanged). Added `stale_forkserver_count`
(age >= 1h AND concurrent_checks == 0, deliberately conservative per the
ticket's own caution against a reaper acting on a live-parented pool)
and `forkserver_swap_held_kb` (sums VmSwap across every forkserver,
never RSS -- RSS reads near-zero for a swapped-out process). Wired both
into `_land_status_lines`/`_print_land_status` as their OWN separate
lines (STALE FORKSERVERS, SWAP HELD BY FORKSERVERS), never folded into
ORPHANED FORKSERVERS -- collapsing them was the exact incident.

No automated reclamation added, as directed -- this ticket is reporting
only.

Fixed a pre-existing test (TestPrintLandStatus::test_prints_no_live_
holder_as_normal_resting_state_not_stale) that asserted "stale" never
appears anywhere in the report output; that assertion predates this
ticket and is now legitimately false (STALE FORKSERVERS is a real,
separate line) -- narrowed it to check only the LAND LOCK line, plus
monkeypatched the new forkserver functions so the test stays
deterministic instead of reading the real host's /proc.

Verified manually against the live host: ORPHANED FORKSERVERS: 0,
STALE FORKSERVERS: 0 (concurrent checks were nonzero at that instant,
correctly suppressing the stale count per its own precondition), SWAP
HELD BY FORKSERVERS: 6.2GB -- demonstrating the exact fix: swap held is
visible even when both other counts read zero.

### Changed
```
 docs/guides/coordinator-scripts.md     |  62 ++++++++
 scripts/fleet_status.py                | 269 ++++++++++++++++++++++++++++-----
 tests/unit/test_coordinator_scripts.py | 130 +++++++++++++++-
 tickets/T-2517/ticket.md               |  27 +++-
 4 files changed, 450 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_counts_old_forkserver_when_no_checks_running` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_ignores_young_forkserver` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_never_counts_anything_while_a_check_is_running` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_unknown_concurrent_checks_never_counts_anything` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb::test_sums_vmswap_across_every_forkserver` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb::test_missing_status_file_degrades_that_entry_to_zero_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_no_live_holder_as_normal_resting_state_not_stale` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV005@scripts/fleet_status.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2517/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2517/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2517/src/frob/testing/_collect_kotlin.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2517/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2517, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
