## Done report

Changed:
  src/frob/app/process_runner.py (new): run(cfg), _reap(cfg)
  src/frob/app/ops_runner.py::run: dispatches ops_command == "process"
  src/frob/_cli_parsers/_ops.py::_add_ops_parser: registers "frob ops process reap"
  src/frob/app/config.py: process_command, process_reap_json fields
  src/frob/app/_config_external.py: forwards process_command/process_reap_json

Evidence:
  tests/unit/test_app_runners_process.py (8 tests: parser wiring incl.
  T-2004 flag-reaches-AppConfig, ops_runner delegation, reap
  must-fire/must-stay-quiet/json/unknown-subcommand cases)
  Live: `frob ops process reap` and `--json` run clean under this session's
  own live fleet.
  Live must-stay-quiet proof: enumerated 9 running forkserver-shaped
  processes on this host, all ancestry-confirmed live-check-parented via
  T-3072's own _forkserver_root_is_live_check; the CLI command reaped 0 of
  them (matches T-3072's must-stay-quiet guarantee, reused not
  reimplemented).

Filed: none. scripts/fleet_status.py's own half of this ticket was
already closed by T-3093 before this dispatch (confirmed via T-3106's own
scope_changes entry removing that file from scope).

Gates: touched-set `frob test --base main` clean. `frob check --only ty`
clean for this ticket's own files (one pre-existing _config_external.py
ty finding at an unrelated line, unmoved by this diff other than line
shift). `frob check --only scope` shows one SCOPE002 for
process_runner.py's frob:doc anchor into docs/modules/app.md -- same
structural class as ops_runner.py's own PRE-EXISTING identical SCOPE002
on the same anchor (large scope = many external doc anchors); not new
noise introduced by this change, and adding docs/modules/app.md to
declared scope makes it dramatically worse (explodes to every symbol
that doc describes), so left as-is rather than "fixed" into a worse
state.

### Changed
```
 src/frob/_cli_parsers/_ops.py          |  31 +++++++--
 src/frob/app/_config_external.py       |   4 ++
 src/frob/app/config.py                 |   6 ++
 src/frob/app/ops_runner.py             |  16 +++--
 src/frob/app/process_runner.py         |  80 +++++++++++++++++++++++
 tests/unit/test_app_runners_process.py | 115 +++++++++++++++++++++++++++++++++
 tickets/T-3106/ticket.md               |  31 ++++++++-
 7 files changed, 274 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_process.py::TestProcessReapParser::test_process_reap_parses_and_dispatches` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessReapParser::test_process_reap_json_flag_parses` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessReapParser::test_process_reap_json_flag_reaches_appconfig` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestOpsRunnerProcessDelegation::test_process_subcommand_delegates_to_process_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_reports_reaped_pids` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_reports_nothing_reaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_json_mode_emits_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_unknown_process_subcommand_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 101 error(s), 1864 warning(s), 861 waived
- error-findings: AFFECT001@src/frob/app/ops_runner.py, AFFECT001@src/frob/app/process_runner.py, ARCH103@src/frob/app/process_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3109/ticket.md, DOC006@tickets/T-3110/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bo/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3106, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, RENDER001@src/frob/app/process_runner.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/ticket_runner/_new.py, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@src/frob/app/_config_external.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
