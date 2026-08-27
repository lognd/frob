## Done report

Changed:
- scripts/fleet_status.py::_read_proc_locks
- scripts/fleet_status.py::_true_flock_holder_pid
- scripts/fleet_status.py::_land_status_lines
- scripts/fleet_status.py::_print_land_status
- scripts/fleet_status.py::_is_live_check_cmdline
- scripts/fleet_status.py::_live_check_pids

Fix 1 (the ticket's primary ask): LAND LOCK holder-vs-waiter.
`land_lock_holder_pids` scans /proc/*/fd for any live process with
land.lock OPEN. `_land_lock` is a non-blocking flock poll loop, so every
WAITING process also holds the file open (without holding the flock) for
its whole polling window -- three fd-open pids read as three
simultaneous "holders". `_true_flock_holder_pid` reads /proc/locks
(matched by the lock file's own device:inode, verified live against a
real flock + a real non-blocking waiter subprocess) to find the ONE true
holder; the LAND LOCK line now names it and counts waiters separately
("held by pid=X; N waiter(s) ..."). Honest-limits requirement: when
/proc/locks itself cannot be read, the line says "N process(es) have the
lock file open; true holder not determinable from /proc" rather than
printing the fd-open set under a "holder" label -- an explicit "not
determinable" beats a confident wrong number.

Fix 2 (audit finding, fixed): ORPHANED FORKSERVERS line. This script's
own `_FROB_CHECK_TOKEN_RE = re.compile(rb"(?:^|/)frob\x00")` only
anchors "^" to the WHOLE cmdline blob's start, never to each
NUL-delimited argv token, so a bare "frob" token that is neither the
first token nor preceded by a literal "/" never matched -- exactly the
shape "python -m frob check ..." produces (the fleet's own dominant
invocation shape under "uv run"). CONFIRMED LIVE 2026-08-27, twice: two
running "python -m frob check ..." launchers had all their descendant
forkservers reported ORPHANED before the fix, and 0 orphans (correct)
after, verified against a real background "frob check --only gates" run
alongside a real sibling agent's own live forkserver. Replaced with
_is_live_check_cmdline (whole-token comparison, no anchor bug possible
by construction) -- this script cannot `import frob.process._reap`
(its own standing "no frob import" contract, kept), so this is a
second, deliberate, documented copy of T-3072's identical fix in that
module, not a silent duplicate.

AUDIT (per the ticket's own ask -- report findings even where nothing
changed):
- LAND LOCK line: FIXED (above).
- ORPHANED FORKSERVERS line: FIXED (above).
- STALE FORKSERVERS / SWAP HELD BY FORKSERVERS lines: same
  ancestry/cmdline substrate as ORPHANED FORKSERVERS
  (_forkserver_snapshot/_live_check_pids), so they inherit the same fix
  automatically -- no separate change needed.
- CONCURRENT CHECKS line (concurrent_check_count): same
  _is_live_check_cmdline fix applies directly (it IS the function this
  line reports) -- covered above, regression test added
  (test_counts_module_invoked_check).
- IDLE?/[ACTIVE]/[STRANDED]/[STALE] worktree annotations
  (worktree_content_classification): AUDITED, NOT the same bug class.
  This is a git-diff-content heuristic (deletion-dominant ratio,
  per-line presence checks, ticket-state lookups via
  _worktree_started_ticket_ids) with its own extensively documented
  thresholds and positive controls (T-2599/T-2617/T-2755), not a
  cmdline-regex classifier with an anchor bug. The bracketed label is
  already presented as a classification ("[STALE]", "[STRANDED]"), not a
  claim of certainty the way "held, live holder pid(s)=..." implied
  simultaneous true ownership. No change made.

Must-fire: one land holding the flock, two others polling (waiting) --
output names the true holder, counts waiters separately.
Must-stay-quiet: a single land, no waiters -- output meaning unchanged
(still names the holder, no waiter language added).

Test-first proof: tests/unit/test_coordinator_scripts.py committed alone
first (aaf0e7ca3), confirmed 9/9 new tests fail at that commit
(AttributeError/AssertionError); the fix commit (5e2fcae84) followed.
--designate-repro against aaf0e7ca3 confirms FAILED_AT_PARENT for
TestTrueFlockHolderPid::test_finds_the_true_holder.

Evidence: 9 node ids bound.

Filed: none new (T-3072's own residue, T-3106, already covers the
CLI-wiring half not addressed here; this ticket's own scope,
scripts/fleet_status.py, is now clean of the false-positive it
introduced).

Gates: frob check --ticket T-3093 to run at land. One pre-existing,
unrelated test failure confirmed
(TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked
fails identically in isolation at the parent commit, before any of this
ticket's changes -- a worktree-name-collision flake in this live
13-worktree repo, not caused by this change).

### Changed
```
 scripts/fleet_status.py                | 193 ++++++++++++++++++++++++++++---
 tests/unit/test_coordinator_scripts.py | 203 ++++++++++++++++++++++++++++++++-
 tickets/T-3093/ticket.md               |  16 ++-
 3 files changed, 393 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_finds_the_true_holder` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_ignores_a_lock_on_a_different_inode` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_unreadable_proc_locks_is_indeterminate` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_missing_lock_file_is_true_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_distinguishes_true_holder_from_waiters` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_must_stay_quiet_single_holder_no_waiters_unchanged_meaning` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_indeterminate_true_holder_says_so_not_a_confident_number` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount::test_counts_module_invoked_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestIsLiveCheckCmdline::test_does_not_match_check_repro_subcommand` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 84 error(s), 907 warning(s), 861 waived
- error-findings: AFFECT001@scripts/fleet_status.py, ARCH001@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@src/frob/tickets/_land_compose.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_land_compose.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3105/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bk/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3093, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
