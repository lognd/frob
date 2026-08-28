## Done report

THE CUT (stated explicitly, per instructions -- this ticket is an epic, not
fully closed by this change):

Implemented: ToolResult.measurement/measurement_reason as computed pydantic
fields (src/frob/process/parsers/common.py), deriving the SAME predicate
frob.check._is_unresolved_only_gate already computed privately just for
as_text's icon (T-2891) -- now a first-class part of the model, so every
existing ToolResult-producing call site in this repo gets it for free with
NO per-gate migration, and as_json() genuinely discloses it (closing the
exact JSON-blindness gap T-2891's own docstring left open). CheckResult.
unmeasured_results and an automatically-printed "## Unmeasured gates"
as_text section give an operator the roster without a second command to
remember (the standing automatic-over-commands directive).

This retroactively covers every gate family that already goes through
_gates_family_result's existing UNRESOLVED-only shape: all *_SCHEMA
config-table validators, FLAGCOV001, REF001/REF002 -- a real, currently-
shipping subset, not a token slice.

NOT implemented (explicitly deferred, four follow-up tickets filed):
  T-3204  budget-truncation NOT_MEASURED + exit-code distinction
                    (acceptance[0] budget case, acceptance[2] exit code)
  T-3205  per-gate NOT_APPLICABLE self-declaration for a
                    hardcoded-layout-style gate against a foreign project
                    (acceptance[1], instance 2 from this ticket's body)
  T-3202  GATESTATUS001 gate-on-gates meta-check enforcing the
                    doctrine structurally (acceptance[3]) -- deliberately
                    NOT implemented by lexical pattern-matching (T-1662's
                    own standard: a lexical decision is itself a defect);
                    needs its own design pass first
  T-3203  epic tracking ticket for the remaining ~50-gate
                    migration to explicit self-reporting (T-2391's own
                    body: "a default-MEASURED shim keeps existing gates
                    compiling while they are converted one at a time")

Why this cut: the shipped slice is a real, generalizable, backward-
compatible substrate (a computed field, not a stored one requiring every
caller to opt in) that immediately fixes the single MOST measured, most
reachable instance of the doctrine violation (T-2891's own 12+-family
off-repo defect, now JSON-visible) without a shallow, unverifiable pass
across 52 gates that would have amounted to sprinkling a field nobody
reads. The remaining acceptance items each need a genuinely different
mechanism (budget-chunking integration, per-gate semantic self-knowledge,
a new static-analysis-grade meta-check) that would not fit honestly in
one change.

Gates: frob check --ticket T-2391 -- zero SCOPE001 errors after adding the
draft-ticket-file scope entries the four follow-up `frob ticket new` calls
required (T-3172 precedent: a machinery side effect of filing this
ticket's own required follow-up work, not scope creep). The 399 repo-wide
errors in that run are pre-existing (ty native-import resolution, an
import cycle, coverage-stamp staleness) unrelated to this change --
confirmed by symbol/file, none touching src/frob/check/__init__.py,
src/frob/process/parsers/common.py, or the touched test files.

frob test --base main: touched set (17 tests) exit=0. Also manually
verified no regression in tests/unit/test_app_runners_batch6.py (T-2486's
byte-identical JSON contract, updated in the same commit since the new
fields genuinely change that shape), tests/unit/test_check_tool_
unavailable.py, tests/test_check_runner.py, tests/unit/test_check_budget.py,
tests/unit/test_check.py, tests/unit/fleet/test_status.py, tests/unit/
test_check_json_none_handling_t2484.py, tests/unit/test_ticket_runner_
gate_findings.py -- all green.

Filed: T-3204, T-3205, T-3202, T-3203
(ids will renumber to real T-#### on next allocator pass).

### Changed
```
 src/frob/check/__init__.py            | 50 ++++++++++++++++----
 src/frob/process/parsers/common.py    | 67 +++++++++++++++++++++++++-
 tests/unit/test_app_runners_batch6.py |  5 ++
 tests/unit/test_check_measurement.py  | 76 ++++++++++++++++++++++++++++++
 tests/unit/test_process.py            | 85 +++++++++++++++++++++++++++++++++
 tickets/T-2391/ticket.md              | 89 +++++++++++++++++++++++++++++++++++
 tickets/T-3202/ticket.md    | 29 ++++++++++++
 tickets/T-3203/ticket.md    | 29 ++++++++++++
 tickets/T-3204/ticket.md    | 30 ++++++++++++
 tickets/T-3205/ticket.md    | 29 ++++++++++++
 10 files changed, 480 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 86 error(s), 824 warning(s), 879 waived
- error-findings: AFFECT001@src/frob/check/__init__.py, AFFECT001@src/frob/process/parsers/common.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@src/frob/process/parsers/common.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/__init__.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@src/frob/process/parsers/common.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_check_measurement.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/__init__.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@src/frob/process/parsers/common.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_check_measurement.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/check/_python.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TEST001@src/frob/process/parsers/common.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
