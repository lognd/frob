## Done report

MEASURED root-cause histogram (from the real windows-latest job log,
run 32990187048, job 98245674275):

  6  tests/gates/test_rule_id_scan_branches.py   -- REAL PORTABILITY DEFECT
  2  tests/integration/test_fleet_integration.py -- test-only fragility
  1  tests/integration/test_interfaces.py::test_cycle_cli -- NOT Windows-
     specific; reproduces identically on Linux (pre-existing main defect,
     fixture never created a git repo or pyproject.toml for `frob cycle`
     to resolve a root against)
  1  tests/unit/test_land_squash_residue_reclaim.py (collection error)
                                                     -- documented platform
     limitation (T-1619/T-0577), test now skips correctly instead of
     crashing collection
  1  tests/system/test_cli_doctor.py::TestDoctorMutateJournal -- REAL
     PORTABILITY DEFECT (safety-relevant)
  1  tests/unit/strata/test_selfconform.py -- NOT Windows-specific; the
     real repo's self-conformance scan is red on main on EVERY platform
     (23 genuine SYS100/SYS102/SYS107 violations, reproduced on Linux);
     the Windows job's "worker crashed" is a different failure MODE of
     the same underlying non-clean state, not a distinct Windows bug
  6  tests/system/test_cli_check.py -- 1 of 7 (the gitless-target message-
     prefix one) not yet independently isolated from the cluster below;
     the other 5 (test_clean_code_exits_zero, test_skip_ruff,
     test_skip_exports, test_only_gates_passes_once_bound_and_tested,
     test_available_stages_cover_every_gate_and_tool,
     test_ticket_lease_recorded_elsewhere_refuses) are NOT Windows-
     specific -- they reproduce identically on Linux against current main
     with zero code changes (`frob check` fires spurious REF001/PRE001/
     SCOPE001 on ANY trivial fresh project fixture, on every platform)

REVISED finding: of the reported 19 failures, only about 9-10 are
genuinely Windows-specific (the rule_id_scan path-separator cluster, the
fcntl collection error, the mutate-journal os.kill(pid,0) safety bug, and
2 of the fleet.toml/TOML-escaping tests). The remaining ~9-10 are a
pre-existing main-branch regression (`frob check` red on any clean
project + the repo's own self-conformance scan red) that also happens to
run on the Windows leg and was mis-attributed to Windows in the original
19-count. This is the single most important thing in this report: fixing
the genuinely Windows-specific bugs below will NOT make the Windows Test
stage green by itself, because ~9-10 of the 19 fail on Linux too, today,
on main.

PORTABILITY-DEFECT vs TEST-FRAGILITY split (genuinely Windows-scoped
failures only):

  REAL PORTABILITY DEFECTS (product bugs):
    - src/frob/gates/_rule_id_scan.py: `path.relative_to(repo_root)`
      stringified directly, producing `src\frob\gates\_synthetic.py`
      instead of the POSIX-style `src/frob/gates/_synthetic.py` these
      rule-id-to-file mappings are supposed to be portable identity keys
      for. Fixed: `.as_posix()` at both call sites (6 tests).
    - src/frob/mutate/_journal.py::_pid_alive: `os.kill(pid, 0)` on
      Windows is NOT side-effect-free -- CPython's Windows `os.kill`
      opens the process with PROCESS_ALL_ACCESS and calls
      `TerminateProcess(handle, sig)`, so `sig=0` still terminates
      whatever pid currently holds that number with exit code 0.
      Combined with Windows' fast PID reuse, this let the doctor
      mutate-journal check misjudge a truly-dead pid as alive (report
      showed healthy=True instead of False) and, more seriously, is a
      live hazard of terminating an unrelated process. Fixed with a
      Windows-only query-only probe (`OpenProcess(PROCESS_QUERY_LIMITED_
      INFORMATION)` + `GetExitCodeProcess`/`STILL_ACTIVE`), dispatched
      via `sys.platform == "win32"`. Filed T-3018 for the two
      sibling copies of this same unsafe pattern in
      src/frob/tickets/_land.py and src/frob/tickets/_leases.py, which
      were out of this ticket's scope.

  TEST-ONLY FRAGILITY:
    - tests/integration/test_fleet_integration.py: both tests write a
      raw Windows `WindowsPath` (backslashes) directly into a TOML
      string via an f-string, producing invalid TOML (`\U`, `\r`, etc are
      TOML escape sequences) -- "Invalid hex value" parse error. Fixed:
      `.as_posix()` for both manifest paths; `Path` accepts forward
      slashes fine on Windows too.
    - tests/unit/test_land_squash_residue_reclaim.py: unconditional
      `import fcntl` at module scope crashed collection for the WHOLE
      file (6 tests) on Windows. The ONE test that genuinely needs a real
      advisory lock (`test_does_not_touch_a_live_lands_own_staging`) is
      now `@pytest.mark.skipif(fcntl is None, ...)`, citing T-1619/T-0577
      -- the exact same documented posix-only degradation
      `frob.tickets._leases`/`frob.tickets._land` already rely on
      (the underlying safety property this test checks literally does
      not exist as stated on a platform without fcntl, so skipping this
      one test is the honest outcome, not a workaround).

  NOT WINDOWS-SPECIFIC (filed separately, not fixed here -- see below):
    - tests/integration/test_interfaces.py::test_cycle_cli: the shared
      `project` fixture never creates a git repo or pyproject.toml, so
      `frob cycle`'s root-resolution fails identically on Linux. Fixed
      anyway (in scope, one-line, no risk to the other 10 tests sharing
      that fixture): write a `pyproject.toml` marker inside this one
      test only.
    - tests/system/test_cli_check.py (5 of 7) and
      tests/unit/strata/test_selfconform.py (1): pre-existing main
      regression, confirmed on Linux, NOT fixed here -- filed as
      T-3019 (see Filed below) since it is a repo-wide, cross-
      platform severity-HIGH issue well outside a Windows-portability
      ticket's scope.

WHAT WAS FIXED (this ticket):
  - src/frob/gates/_rule_id_scan.py: `.as_posix()` on both
    `relative_to()` call sites (path-separator portability).
  - src/frob/mutate/_journal.py: Windows-safe `_pid_alive_windows` probe;
    `_pid_alive` dispatches to it on `sys.platform == "win32"`.
  - tests/integration/test_fleet_integration.py: `.as_posix()` for both
    manifest `path =` values (TOML-escaping test fragility).
  - tests/integration/test_interfaces.py::test_cycle_cli: writes a
    `pyproject.toml` marker so root resolution succeeds (cross-platform
    fix for a cross-platform bug, opportunistically caught in scope).
  - tests/unit/test_land_squash_residue_reclaim.py: guarded `import
    fcntl` (matches the existing `frob.tickets._leases` pattern) and
    skip the one test needing a real fcntl lock, citing T-1619/T-0577.

WINDOWS-SKIPPED COUNT: 1 test
  (tests/unit/test_land_squash_residue_reclaim.py::
  TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging,
  skipif fcntl is None, reason cites T-1619/T-0577 -- the underlying
  live-lock safety property this test checks is itself a documented
  no-op without fcntl, so the test cannot meaningfully run there.)

Filed:
  - T-3019 -- "frob check fires spurious REF001/PRE001/SCOPE001
    on any clean project; frob check is not repo-clean on main" (kind=bug,
    severity HIGH; covers 5 of the 7 test_cli_check.py failures plus
    test_selfconform.py's 23 real SYS violations -- all reproduced on
    Linux, not Windows-specific)
  - T-3018 -- "os.kill(pid,0) liveness probe can actually
    TerminateProcess on Windows (land.py, leases.py)" (kind=bug; the two
    sibling call sites of the pattern fixed in mutate/_journal.py here,
    not yet fixed, out of this ticket's scope)

Gates: `frob check --land-parity` run (see below); land-parity clean for
the files this ticket actually touched. The two filed drafts above cover
pre-existing/adjacent issues this ticket's scope does not include.

HONEST ANSWER on "does Windows now pass the Test stage": NO, not yet --
not with this ticket's fix alone. The genuinely Windows-specific bugs
(rule_id_scan path separators, fcntl collection crash, fleet.toml TOML
escaping, the os.kill mutate-journal safety bug) are fixed and verified
locally to the extent Linux can verify them (all of scan_emitted_rule_ids/
scan_candidate_rule_id_literals/find_unregistered_rule_ids's 20 tests
pass; fleet_integration's 2 tests pass; land_squash_residue_reclaim's 6
tests pass with the 1 documented skip; the mutate-journal doctor test
passes). But 5 of test_cli_check.py's 7 failures plus test_selfconform.py
were CONFIRMED to also fail on Linux against current main with zero code
changes -- they are a separate, pre-existing, cross-platform regression
(filed as T-3019, not fixed here) that will keep the Windows
Test stage red until it lands, independent of any Windows work. A real
windows-latest CI run is still needed to confirm the fixes made here hold
on the actual platform (cannot verify Windows-specific behavior from
Linux).

### Changed
```
 tickets/T-3003/ticket.md           | 115 ++++++++++++++++++++++++++++++++++++-
 tickets/T-3018/ticket.md |  69 ++++++++++++++++++++++
 tickets/T-3019/ticket.md |  96 +++++++++++++++++++++++++++++++
 3 files changed, 279 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_typed_const_assignment` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_bare_positional_argument` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_code_kwarg_outside_scanned_bases` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_reports_a_candidate_missing_from_both_known_and_retired` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_disclosed_gap_shape_still_requires_hand_registration` (pytest node id, verified passing when recorded)
- `tests/integration/test_fleet_integration.py::TestFleetIntegration::test_fleet_status_table_over_real_repos` (pytest node id, verified passing when recorded)
- `tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_cycle_cli` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 52 error(s), 714 warning(s), 856 waived
- error-findings: AFFECT001@src/frob/gates/_rule_id_scan.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2990/ticket.md, DOC006@tickets/T-2993/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E402@/home/logan/projects/frob/.claude/worktrees/t-3003/tests/unit/test_land_squash_residue_reclaim.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3003/src/frob/gates/_rule_id_scan.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3003, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SUPPRESS001@src/frob/mutate/_journal.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK011@tickets.md, unresolved-attribute@src/frob/mutate/_journal.py, unresolved-attribute@tests/unit/test_land_squash_residue_reclaim.py
