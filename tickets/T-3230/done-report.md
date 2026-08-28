## Done report

Triage: measured all 37 `spawned.is_err or spawned.danger_ok.returncode
!= 0` call sites T-3216's own survey named (git grep count reproduced
fresh, unchanged at 37). Read each site's caller to see whether the
failure-collapsed return value (`()`/`None`/`{}`/`False`/frozenset())
feeds a BLOCKING or MUTATING decision the caller cannot tell apart from
a genuine negative measurement, vs. a purely advisory/report-only read
whose empty-on-failure direction is already the safe one, vs. a site
that already returns a typed Result/Option and fails closed.

Split:
- 2 genuinely wrong (fixed here): `_reconcile.py::_live_worktree_
  ticket_ids` (feeds `_stale_in_progress_ticket_ids`'s requeue decision
  -- an unmeasurable read satisfied "not in live_worktree_ticket_ids",
  exactly the T-2292 dangerous direction) and its sibling `_live_
  worktrees` (feeds `_archive.py::_refuse_archive_if_other_worktrees_
  live`'s guard -- an unmeasurable read fell through `if not live:
  return Ok(None)`, silently PERMITTING the archive write the guard
  exists to gate).
- 7 already correctly handled: `_land_git_ops.py::_porcelain_dirty`
  (633, Result/Err), `_porcelain_dirty_paths` (708, T-3216's own
  documented empty-on-failure contract with a separate error-reporting
  seam), `_worktree_sweep.py::_list_agent_worktrees` (123, Result/Err),
  `_worktree_is_clean` (148, `bool | None`, docstring requires caller
  treat `None` as dirty), `_worktree_head_age_seconds` (162, same
  `None`-conservative contract), `_mutation_evidence.py::_touched_
  python_files` helper at 185 (fails closed to `False` = "still treat
  as touched", the safe direction), `_evidence.py::compute_changed_
  lines` (2145, explicitly documented auxiliary/non-precondition,
  logged).
- 28 low-stakes/advisory, false-negative-safe direction (an
  unmeasurable read degrades to "nothing found" for a report-only or
  self-skipping check, never a false claim backing a refusal/mutation):
  the `gates/__init__.py`/`_docblocks*.py`/`_docptr.py`/`_tdd_order.py`/
  `_tickets_gate.py`/`_todo_fmt.py` doc/scope/TDD/TICK005 helpers (all
  degrade to "skip this check" on failure, not "confirmed clean+block"),
  `_flow.py`/`_store.py` ledger-history mining (analytics only),
  `_unlanded.py`'s three sites (advisory scan), `_land_git_ops.py`'s
  remaining sites (`_conflicted_files`, `_ticket_dirs_at_head`,
  `_read_tracked_text_or_none`/`_read_text_at_commit_or_none` x2,
  file-history-for-a-path, `_staged_rapid_debt_ticket` -- all either
  feed a further guard that itself degrades safely, or are cited in
  their own docstrings as "best-effort, never turns cannot-tell into a
  fabricated answer").

  Cut made: fixed only the 2 sites where the collapsed unmeasurable
  read reaches an actual write/refusal decision through a documented
  incident precedent (T-2292) or an equivalent fresh reasoning (the
  archive guard). The 28 advisory sites are NOT filed as individual
  follow-up tickets -- re-triaging this class site-by-site if a NEW
  incident surfaces from one of them is cheaper than 28 speculative
  tickets against sites whose current failure direction is already the
  documented-safe one; this triage itself (this Done report) is the
  record for any future re-audit.

Evidence:
tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure::test_unmeasurable_worktree_signal_is_never_requeued (designated repro, force-designated: the fix changes _live_worktree_ticket_ids's return type in the same commit as the caller-side check that consumes it, so no ancestor commit holds this test failing cleanly rather than TypeErroring at collection -- see evidence record for full reasoning)
tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure::test_measured_signal_still_requeues_normally (must-stay-quiet control)
tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_unmeasurable_worktree_list_refuses_not_allows (must-fire, archive-guard side)

Filed: none -- see "Cut made" above for why the remaining 28/35
untouched sites were not individually filed.

Gates: frob check --ticket T-3230 clean on the ticket-scoped subset
(gate:SCOPE 0 errors, gate:AFFECT 0 errors after the doc update,
gate:FMT clean); ruff-check 0 errors on touched files; ty shows no
new findings on touched files (pre-existing win32 fcntl findings at
tests/test_ticket_reconcile.py:216/237 are T-3211's territory,
untouched by this diff). Repo-wide gate families remain their
pre-existing baseline counts per the --ticket scope-note (not scoped
to this ticket, not evidence of this diff's cleanliness or dirtiness).
frob test --base main: touched=18 python, run_selected exit=0.

### Changed
```
 docs/modules/tickets-data-storage.md | 11 ++++++
 src/frob/tickets/_archive.py         | 27 ++++++++++++-
 src/frob/tickets/_models.py          | 13 +++++++
 src/frob/tickets/_reconcile.py       | 72 ++++++++++++++++++++++++++--------
 tests/test_ticket_reconcile.py       | 75 ++++++++++++++++++++++++++++++++++++
 tests/test_tickets_organization.py   | 29 ++++++++++++++
 tickets/T-3230/ticket.md             | 35 ++++++++++++++++-
 7 files changed, 243 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure::test_unmeasurable_worktree_signal_is_never_requeued` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileWorktreeMeasurementFailure::test_measured_signal_still_requeues_normally` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_unmeasurable_worktree_list_refuses_not_allows` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 97 error(s), 3048 warning(s), 876 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3230, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
