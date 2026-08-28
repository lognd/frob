## Done report

Reproduced the false positive directly on current main before fixing:
_opaque_indirection_findings(Path("src/frob/gates/_refs.py")) returned one
finding, a textual "importlib.import_module" mention inside the module's
own docstring, because the header frob:waive comment before the docstring
defeated _PY_DOCSTRING_QUERY_SRC's `.` anchor. Confirmed the anchor issue
empirically with tree-sitter Query experiments (grammar does not treat
`comment` as anchor-transparent here) before touching the query.

Fix layer: parse (tree-sitter Query), not lexical -- each
_PY_DOCSTRING_QUERY_SRC pattern now tolerates zero-or-more leading
(comment)* nodes before the anchored string/expression_statement.
_PY_DOC_CAPTURE_FILTER's existing supertype guard (module/block/
expression_statement) is unaffected since the comment node itself is
never captured.

After fix: _opaque_indirection_findings(Path("src/frob/gates/_refs.py"))
returns () -- false positive gone. Verified against
src/frob/app/_config_external.py, check_runner.py, config.py (the other
candidates the ticket named) -- remaining findings there are real getattr
calls in code, not docstring prose.

Evidence:
tests/test_vet_capability.py::TestLeadingCommentDoesNotDefeatDocstringExclusion::test_leading_comment_then_docstring_prose_stays_quiet (must-stay-quiet fixture)
tests/test_vet_capability.py::TestLeadingCommentDoesNotDefeatDocstringExclusion::test_leading_comment_then_real_call_still_fires (must-fire fixture)

Filed: none

Gates: frob check --ticket T-2885 clean for the ticket-scoped families
(gate:SCOPE 0 errors after adding tests/test_vet_capability.py to scope;
gate:PREWORK clean; COV002/TODO001 diff-driven checks show no hits in the
touched files; gate:FMT 0 errors). Other gate families in the output are
repo-wide per the tool's own scope-note and were not newly broken by this
change. frob test --base main: touched=2, both pass.

### Changed
```
 src/frob/vet/_capability_core.py | 32 ++++++++++++++------
 tests/test_vet_capability.py     | 63 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-2885/ticket.md         |  8 +++++
 3 files changed, 94 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 95 error(s), 754 warning(s), 874 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2885, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
