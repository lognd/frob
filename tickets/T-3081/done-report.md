## Done report

Changed:
  src/frob/tickets/_new_renumber.py::_ticket_from_spec

Evidence:
  tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket.test_no_scope_declared_round_trips_through_new_ticket (DESIGNATED REPRO, confirmed FAILED_AT_PARENT at 21dafc074)
  tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket.test_runs_last_parallel_safe_round_trips_through_new_ticket

Measured (the "other dropped fields" check requested):
  Compared every TicketSpec field against what _ticket_from_spec copies onto
  Ticket(...). Two bool+reason escape-hatch pairs were silently dropped, not
  one:
    - no_scope_declared / no_scope_declared_reason (T-2394) -- the ticket's
      own reported bug.
    - runs_last_parallel_safe / runs_last_parallel_safe_reason (T-2579) --
      found by this same comparison, previously unreported. Confirmed by the
      same round-trip technique: filed via TicketSpec(runs_last_parallel_safe=
      True, ...), reloaded ticket read runs_last_parallel_safe=False.
  scope_breadth_ack / scope_breadth_ack_reason (T-2302) was already wired
  correctly and served as the reference shape both fixes now match. All
  other TicketSpec fields (title, kind, origin, priority, scope, findings,
  blocked_by, parent, tier, sprint, runs_last, milestone, acceptance, threat,
  evidence, component, labels, body) were confirmed present in the
  Ticket(...) call already.

Filed: none

Gates: frob check --ticket T-3081 (--only scope/prework/fmt/affect_drift)
  clean (0 errors). Repo-wide gate families (DRIFT/PRE/WAIVE/etc, not scoped
  to this ticket per the tool's own scope-note) show pre-existing failures
  unrelated to this diff -- not introduced by this change.

### Changed
```
 src/frob/tickets/_new_renumber.py | 21 ++++++++-
 tests/test_tickets_no_scope.py    | 97 +++++++++++++++++++++++++++++++++++++++
 tickets/T-3081/ticket.md          | 17 ++++++-
 3 files changed, 132 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket::test_no_scope_declared_round_trips_through_new_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket::test_runs_last_parallel_safe_round_trips_through_new_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 76 error(s), 695 warning(s), 862 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3088/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bh/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3081, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
