## Done report

Changed:
  scripts/fleet_status.py::swap_pressure (new)
  scripts/fleet_status.py::_swap_guidance (new)
  scripts/fleet_status.py::_land_status_lines (swap param, guidance clause)
  scripts/fleet_status.py::_print_land_status (swap wiring)
  scripts/fleet_status.py::_all_process_ppid_cpu (new, fold-in)
  scripts/fleet_status.py::_descendant_cpu_seconds (new, fold-in)
  scripts/fleet_status.py::land_invocations (child_cpu_s field, fold-in)
  docs/guides/coordinator-scripts.md (new/updated entries)

T-2249's own fix: `swap_pressure` reads SwapTotal/SwapFree from
/proc/meminfo (the same file host_load already reads MemAvailable from
-- no subprocess, no new dependency, per the ticket's explicit "do NOT
shell out to free" instruction). `_swap_guidance` overrides the static
"3-4 agent" concurrency clause when swap_used_kb >= 1GB
(_SWAP_PRESSURE_FLOOR_KB) -- stated measured basis: the incident had 6GB
swap used against a 24GB total; 1GB is set well below that (still
fires) and well above the few-MB of swap a healthy host routinely
carries from boot/idle paging (does not false-positive on "any swap at
all", per the ticket's own caution). SwapTotal: 0 never claims pressure
or divides by zero (must-still-pass). LOAD/MEM figures unchanged --
this adds a signal via the guidance clause only.

Two fold-ins, neither separately ticketed (per the coordinator's
explicit "fold in while you own this file" instruction): (1) LAND LOCK
wording for an idle, no-live-holder lock now reads as the NORMAL resting
state rather than "stale" (a flock is kernel-released on holder death;
the old wording had already contributed to one retracted ticket
claiming a deadlock). (2) land_invocations' cpu_s gains a child_cpu_s
sibling, summed over every live descendant of a land's own tracked pids
via one extra `ps -eo pid,ppid,time` snapshot -- a healthy land running
`frob check` as a child no longer reads as a near-zero-CPU stall.

Evidence: tests/unit/test_coordinator_scripts.py::TestSwapGuidance::test_swap_above_floor_overrides_the_static_guidance
  FAILED_AT_PARENT confirmed at 25b739358 (repro-only commit); PASSED
  after the fix commit 0591b3ba9.
  Also added: TestSwapPressure (3 tests, incl. SwapTotal=0 must-still-pass
  and unreadable-file-returns-None), TestSwapGuidance (2 more: below-floor
  and unknown-swap must-still-pass), TestDescendantCpuSeconds (2 tests),
  test_child_cpu_s_sums_live_descendants_not_tracked_rows,
  test_prints_child_cpu_when_nonzero_omits_when_zero, and renamed/updated
  test_prints_stale_lock_when_no_live_holder to assert the new wording.
  Full run: tests/unit/test_coordinator_scripts.py -- 108 collected, 0
  failed. Manually verified `uv run python3 scripts/fleet_status.py`
  against this repo's real live /proc state: LOAD/MEM line unchanged,
  guidance stays "3-4 agent concurrent" (no swap pressure on this host
  right now).

Filed: none

Gates: frob check --ticket T-2249 -- gate:SCOPE/gate:PREWORK clean;
  gate:AFFECT closed via real docs/guides/coordinator-scripts.md edits
  (not waived); frob-arch itself passes (0 errors) -- the one
  scripts/fleet_status.py ARCH103 finding in the repo-wide gate:ARCH
  count is `_print_rot_bucket`, pre-existing from T-2229's already-landed
  work, not introduced by this diff.

### Changed
```
 docs/guides/coordinator-scripts.md     |  93 ++++++++++++--
 scripts/fleet_status.py                | 215 ++++++++++++++++++++++++++++++---
 tests/unit/test_coordinator_scripts.py | 182 ++++++++++++++++++++++++++--
 tickets/T-2249/ticket.md               |  37 ++++--
 4 files changed, 478 insertions(+), 49 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestSwapGuidance::test_swap_above_floor_overrides_the_static_guidance` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-2180, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2249/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2249/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2249/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
