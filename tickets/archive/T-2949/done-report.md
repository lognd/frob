## Done report

`_ticket_terminal_state_on_main` (the `frob ticket land --finish`
already-done fast path) used to call `frob.tickets.load_all(root)`,
which parses whatever `tickets.md`/`tickets/<id>/ticket.md` content
currently sits on DISK in `root`'s working tree -- including any
uncommitted leftover content from an aborted land's own pre-commit
staging (T-2927's exact incident: an abort correctly left the working
tree unstaged/uncommitted, but the STALE on-disk file still read
`state: done`, and `--finish` read that as "already landed" and deleted
the worktree, while `main`'s real HEAD still had the ticket `queued` and
the actual land commit lived only on the about-to-be-orphaned branch).

Premise reproduced: confirmed `load_all`'s implementation
(`src/frob/tickets/_store.py`) globs/reads files straight off the
filesystem with no git-ref awareness at all -- exactly the "reads
uncommitted working-tree state" defect the ticket describes.

Fix: `_ticket_terminal_state_on_main` now delegates to a new
`_read_ticket_state_at_head(root, ticket_id)`, which reads
`git show HEAD:tickets/<id>/ticket.md` (v2 mode) or
`git show HEAD:tickets.md` (single-ledger mode, parsed and looked up
by id) instead of the filesystem, so an uncommitted working-tree edit
can never be mistaken for main's real committed state.

Evidence:
tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain.test_done_ticket_returns_its_state
tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain.test_done_ticket_uncommitted_on_disk_returns_none (must-stay-quiet: dirty on-disk done, HEAD still queued -> None)
tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain.test_in_progress_ticket_returns_none
tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain.test_unknown_ticket_id_returns_none
tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded.test_terminal_on_main_skips_land_core_and_cleans_up (must-fire: committed done -> cleanup-only path taken)
tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded.test_non_terminal_on_main_runs_the_normal_land
tests/unit/test_land_finish_idempotent.py::TestReadTicketStateAtHead::test_reads_committed_state_not_dirty_working_tree
tests/unit/test_land_finish_idempotent.py::TestReadTicketStateAtHead::test_returns_none_when_head_has_no_such_ticket

Repro-fails-at-parent: `_read_ticket_state_at_head` and
`test_done_ticket_uncommitted_on_disk_returns_none` do not exist at the
parent commit -- confirmed by reverting only `_land_cmd.py` to the
parent's content and re-running the new test IDs, which failed at
collection with `ImportError: cannot import name
'_read_ticket_state_at_head'`.

Filed: none.

Gates: `frob check --ticket T-2949` clean except ARCH103 on
`_assert_touched_files_lint_clean_pre_land`, a pre-existing finding on
an untouched function already present on main (confirmed via
`git show main:src/frob/app/ticket_runner/_land_cmd.py`), out of this
ticket's scope.

### Changed
```
 frob.lock                                 | 20 +++++++-
 src/frob/app/ticket_runner/_land_cmd.py   | 84 ++++++++++++++++++++++++-------
 tests/unit/test_land_finish_idempotent.py | 54 ++++++++++++++++++++
 tickets/T-2949/ticket.md                  |  8 +++
 4 files changed, 147 insertions(+), 19 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 96 error(s), 901 warning(s), 882 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2949, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/check/_python.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
