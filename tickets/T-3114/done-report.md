## Done report

Changed: src/frob/tickets/_land_compose.py::LandComposeError (new ResyncBlocked member)
src/frob/tickets/_land_compose.py::resync_root_to_published_tip
tests/unit/test_land_compose.py::TestResyncRootToPublishedTip
docs/modules/tickets-landing.md (new "post-CAS root resync (T-3114)" section)

Evidence: tests/unit/test_land_compose.py::TestResyncRootToPublishedTip.test_unrelated_dirty_path_resyncs_and_is_preserved (must-stay-quiet)
tests/unit/test_land_compose.py::TestResyncRootToPublishedTip.test_dirty_path_the_land_also_changed_blocks_atomically (must-fire)
Full module: 13 passed, 0 failed.

Filed: none (this ticket IS the residue T-3089 decomposed out; T-3089's body
now carries the settled resync design this implements).

Gates: frob check --ticket T-3114 clean for this change. Two findings remain
in the scoped output and BOTH are pre-existing, not introduced here: REF002
on _land_compose.py (file-level single-inbound-reference, true since T-3088
shipped the module unwired) and five SELFAUDIT001 'exec' capability
observations on tests/unit/test_land_compose.py at lines 24/26/187/275/282 --
all of them subprocess helpers that predate this diff, whose additions start
at line 306. WIRE001 on the new public symbol carries an explicit
frob:waive follow_up="T-3089", the same posture T-3088 and T-3107 shipped in:
the only caller is the squash-stage wiring, which is T-3089's scope and is
blocked on this primitive existing.

### Changed
```
 tickets/T-3114/ticket.md | 31 ++++++++++++++++++++++++++++++-
 1 file changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_compose.py::TestResyncRootToPublishedTip::test_unrelated_dirty_path_resyncs_and_is_preserved` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestResyncRootToPublishedTip::test_dirty_path_the_land_also_changed_blocks_atomically` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 83 error(s), 670 warning(s), 862 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3109/ticket.md, DOC006@tickets/T-3110/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3114/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3114, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
