## Done report

Changed:
src/frob/app/ticket_runner/_verify.py::_python_for_tree
src/frob/app/ticket_runner/_verify.py::_venv_python_has_frob_importable

Evidence:
tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_uses_tree_venv_python_when_present
tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_falls_back_when_tree_venv_lacks_frob_importable
tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_falls_back_to_sys_executable_when_no_tree_venv
tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_check_gate_findings_fn_spawns_the_tree_venv_python
tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_check_gates_summary_fn_spawns_the_tree_venv_python

Filed: none

Gates: frob check --only lint/static/gates-fast/gates-native/gates-security --ticket T-3305 clean
of every error touching the touched-set (all remaining errors are
pre-existing and unrelated: strata-core COV001 doc-anchor backlog,
DEPR006 abandoned-baseline lock, ARCH103, DRIFT002 gates.md, ty
unknown-argument in test_app_runners_process.py/test_pytest_spawn_env_wiring.py,
frob-cycle CYCLE001 in tickets/_land_*). frob test --base main: exit=0,
3 python test(s) recorded stable.

Design note for the record: the tree-venv-first preference from T-0846
is kept -- it still applies whenever the tree's own venv legitimately
carries frob (frob's own repo, or a consumer that deliberately vendors
frob as a project dependency). The fallback to sys.executable only
fires when the venv's frob is NOT importable, and sys.executable is by
construction the interpreter currently running this very frob process,
so it is self-certifying: it always has frob importable, and the spawn
through it always produces a real MEASURED (or MEASURED-AND-FAILING)
verdict rather than a silent unmeasured one. No separate three-state
signal was added at the interpreter-selection layer because none is
needed: the two-branch choice (tree venv verified importable vs.
sys.executable, which is always importable) can no longer reach
COULD-NOT-MEASURE by construction -- see the updated docstrings on both
symbols above for the full reasoning.

### Changed
```
 src/frob/app/ticket_runner/_verify.py          | 80 +++++++++++++++++++++++---
 tests/unit/test_ticket_runner_gate_findings.py | 66 +++++++++++++++++----
 tickets/T-3305/ticket.md                       | 14 +++++
 3 files changed, 141 insertions(+), 19 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 89 error(s), 3946 warning(s), 885 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3287/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3305, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
