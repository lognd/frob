## Done report

scripts/fleet_status.py::_flock_holders_matching (os.major/os.minor) and
the /proc-forkserver-scan function (os.sysconf) called POSIX-only
stdlib functions unconditionally -- same shape T-3191 fixed for
frob.process._reap/_pid_liveness: typeshed declares both under
`if sys.platform != "win32":`, invisible under a host-only Linux ty
check, surfaced once T-3191 wired win32/darwin targets in too. Fixed
with the identical `sys.platform != "win32"` narrowing guard (never a
`ty: ignore` -- the matched-opposite-error shape a static suppression
cannot satisfy). tests/system/test_fleet_status_ground_truth.py's own
os.major/os.minor fixture-construction call got the equivalent `assert
sys.platform != "win32"` narrowing (a whole /proc/locks-fixture test,
meaningless off POSIX anyway).

Triage: re-measured fresh via `frob check --only ty` on current main
(202 findings across 23 files, up from the ticket's own 18-file/
unspecified-count snapshot -- confirms the drift the ticket itself
warned about). Split:
- 2 genuine product-code sites, fixed here: scripts/fleet_status.py's
  two functions above.
- 3 findings on 3 src files (src/frob/app/_config_external.py,
  src/frob/app/ticket_runner/_new.py, src/frob/verify/_worker.py) are
  `unused-ignore-comment`, NOT `unresolved-attribute`/`unknown-
  argument` -- a DIFFERENT bug shape (a stale `ty: ignore` left over
  from before some earlier, unrelated fix, not a missing platform
  guard). Left untouched -- not what this ticket's premise described,
  and mixing that fix shape in here would blur two unrelated defect
  classes into one commit.
- ~197 remaining findings across 21 files (mostly test bodies: bare
  `fcntl.flock`/`os.fork` usage repeated inside POSIX-only test
  fixtures -- tests/test_ticket_leases.py alone is 55/197) split into
  T-3244 with the exact file list and finding count, rather
  than fixed mechanically here -- the volume and repetition (8+
  near-identical local `import fcntl` blocks in test_ticket_leases.py
  alone) warrants its own pass, possibly with a shared fixture/helper
  instead of 8 independent guards in one file, which is a design
  decision this ticket's narrow scope should not make unilaterally.

Cut made: fixed the 2 product-code sites (highest value: real library
code, not test fixtures) plus the one test file (test_fleet_status_
ground_truth.py) whose fixture directly exercises the fixed function,
since leaving that one inconsistent with its own subject under test
would be a worse state than before. Everything else split to the
follow-up ticket with an exact count and file list.

Gates: frob check --only ty shows zero scripts/fleet_status.py findings
after the fix (was 3). Touched-file pytest (test_fleet_status_ground_
truth.py, test_coordinator_scripts.py -k Win32Guard) green. ruff-check
0 errors on touched files.

### Changed
```
 scripts/fleet_status.py                        |  30 ++++-
 tests/system/test_fleet_status_ground_truth.py |   6 +
 tests/unit/test_coordinator_scripts.py         |  40 ++++++
 tickets/T-3211/ticket.md                       |  13 +-
 tickets/T-3244/ticket.md             | 167 +++++++++++++++++++++++++
 5 files changed, 250 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestFlockHoldersMatchingWin32Guard::test_win32_platform_returns_empty_without_calling_os_major_minor` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFlockHoldersMatchingWin32Guard::test_posix_platform_still_matches_normally` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ground_truth.py::TestLandLockHolderClaim::test_must_fire_the_true_holder_among_waiters` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 97 error(s), 2910 warning(s), 877 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3211, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
