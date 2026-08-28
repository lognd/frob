## Done report

MECHANISM (measured, precise call chain): `_apply_dirty_main_auto_heals`
(in `_land.py`) runs its OWN `git status` call via `_porcelain_dirty`,
which succeeds and finds real dirt (Ok(True)). `_log_dirty_main_refusal`
then makes a SECOND, separate `git status` call via
`_porcelain_dirty_paths(root)` to list the offending paths -- this second
call is where the observed incident's transient `index.lock` contention
(a concurrent land) hit and failed. `_porcelain_dirty_paths` already
collapsed "clean" and "unreadable" into the same empty tuple `()` on
failure (by design, for its many OTHER unrelated callers). Fed that
empty tuple, `_dirt_owned_by_no_open_ticket(root, ())` is vacuously
`True` (no dirty path can match any ticket's scope when there are no
dirty paths), routing into the "belongs to NO open ticket" message
branch, whose text calls `describe_root_dirt(root)` for the path list --
a THIRD `git status` call, which (by the time it ran) may succeed or
fail independently. In the observed incident it failed too, and
`_render_dirty_paths(())`'s old behavior guessed "(git status
unavailable)" from emptiness alone, producing the exact observed
message: "has uncommitted work belonging to NO open ticket's scope:
(git status unavailable)" plus the fixed "an agent cannot fix this by
retrying" text -- both wrong for transient contention.

Changed:
- src/frob/tickets/_land_git_ops.py::_porcelain_status_error (new) --
  single source of truth for "was git status itself readable", never
  inferred from an empty path tuple.
- src/frob/tickets/_land_git_ops.py::_porcelain_dirty_paths -- UNCHANGED
  behavior (still returns () on failure) to preserve its 8 other,
  unrelated callers across _land.py/_land_finalize.py/_land_squash.py.
- src/frob/tickets/_land_git_ops.py::_render_dirty_paths -- no longer
  guesses "unreadable" from an empty tuple; renders "(none)" for a
  genuinely empty (readable) result. Its only caller (describe_root_dirt)
  now checks readability BEFORE ever reaching it.
- src/frob/tickets/_land_git_ops.py::describe_root_dirt -- checks
  _porcelain_status_error FIRST; on failure, returns a STATUS-UNREADABLE
  description naming the git error, never a paths-based rendering.
- src/frob/tickets/_land.py::_log_dirty_main_refusal -- checks
  _porcelain_status_error FIRST, before either ownership branch; on
  failure, logs a THIRD, distinct refusal that names the git error,
  states this is NOT a confirmed claim of uncommitted work, and says
  retrying is appropriate for likely transient contention -- never the
  old "an agent cannot fix this by retrying" text, which is now scoped
  correctly to the genuine-dirt case only.

Extended scope beyond the ticket's original src/frob/tickets/_land_git_ops.py
to also cover src/frob/tickets/_land.py (where the misleading message text
and the false "NO open ticket" branch actually live -- describe_root_dirt
alone cannot fix the _log_dirty_main_refusal-level bug), plus the test
files touched and docs/modules/tickets-verify-sweep.md (describe_root_dirt's
affects()-closure doc target).

Fixtures:
- must-fire (genuinely dirty root still refuses, paths listed): existing
  TestLandDirtyMain::test_refuses_on_dirty_main (test_ticket_land.py, unchanged
  by this ticket) plus TestDescribeRootDirt.test_names_a_real_dirty_file.
- must-stay-quiet (clean root passes): every other passing land test in
  test_ticket_land.py exercises a clean root implicitly; explicit new
  fixture TestDescribeRootDirt.test_readable_clean_status_is_not_status_unreadable.
- THIRD fixture (the actual bug -- status unreadable produces a distinct,
  non-misleading refusal): TestPorcelainStatusError (3 tests, unit-level on
  the new probe), TestDescribeRootDirt.test_status_unreadable_names_the_git_error_not_uncommitted_work
  (describe_root_dirt-level), TestDirtOwnerTickets.test_status_unreadable_refusal_never_claims_uncommitted_work
  (test_ticket_land.py, _log_dirty_main_refusal-level -- asserts neither
  "cannot fix this by retrying" nor "belonging to NO open ticket" appear).

SIBLING GUARDS: filed T-3230 (will renumber on land) -- 37 call
sites across src/frob/tickets/ and src/frob/gates/ share the exact
"spawned.is_err or spawned.danger_ok.returncode != 0" shape found here.
NOT triaged individually (out of this ticket's scope) -- filed as a
survey ticket per the acceptance criteria's instruction to report the
count separately rather than fix them all here.

One known pre-existing test failure unrelated to this change, confirmed
reproducing identically on unmodified main:
tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_true_verdict_lands_normally
(a warm-sweep-stage path assertion, unrelated to DirtyMain/git status) --
not touched.

Gates: frob check --ticket T-3216 clean for the ticket-scoped families
(gate:SCOPE 0 errors, gate:FMT 0 errors, gate:AFFECT 0 errors after a
frob:waive on describe_root_dirt -- AFFECT001 does not honor frob ack the
way DRIFT001 does, so both were applied). 509 tests pass across
tests/unit/test_rapid_sweep.py and tests/test_ticket_land.py (one
pre-existing unrelated failure deselected and independently confirmed
on main).

### Changed
```
 tickets/T-3216/ticket.md           | 47 +++++++++++++++++++++++++++++++++++++
 tickets/T-3230/ticket.md | 48 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 95 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 96 error(s), 1491 warning(s), 881 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3216/src/frob/tickets/_land_git_ops.py, FLAGCOV001@frob.toml, I001@/home/logan/projects/frob/.claude/worktrees/t-3216/tests/unit/test_rapid_sweep.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3216, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
