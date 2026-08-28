## Done report

Evidence:
tests/test_refactor.py::TestVerify::test_module_import_catches_missing_import
tests/test_refactor.py::TestVerify::test_module_import_passes_clean_module
tests/test_refactor.py::TestCommit::test_run_verify_outcomes_runs_requested_checks
(tests/test_refactor_corpus.py's strengthened test also passes directly
via pytest and via `frob test --base main`, both repeatedly, but is NOT
cited as this ticket's own evidence -- see Filed below)
tests/test_refactor.py + tests/test_refactor_corpus.py -- full files, 122
passed (uv run pytest, both bare and with real pyproject addopts/xdist)
frob test --base main -- touched-set selection, exit=0, twice

Filed: T-3133 (frob ticket evidence's individual-reverify path flaked on
the strengthened corpus test 3x in a row while every manual
reconstruction of the identical pytest invocation passed cleanly and
repeatably -- captured as UNCONFIRMED with a candidate mechanism
(run_selected's declared-runner path never calls apply_agent_env, unlike
_run_pytest_directly's own T-3099 fix, so the fleet xdist bound may
never apply there). Routed evidence around it (only the 3 _verify.py/
_commit.py-focused tests cited) rather than block this ticket on an
unconfirmed infra flake in a DIFFERENT module.

Gates: ruff-check/ruff-format/ty clean on every touched source file
(_verify.py, _commit.py, _split.py).

PARSE IS NOT IMPORT closed: verify_module_import (_verify.py) runs a
real interpreter `import <module>` per touched .py file in a fresh
subprocess, appended UNCONDITIONALLY (never gated by any --skip-* flag)
in _commit.py::run_verify_outcomes. run_split's own chunk verify
(_run_chunk_verify in _split.py) used to be an independent duplicate of
the same three-check sequence, which meant this fix alone never reached
the split verb -- discovered live: reverting T-3122's fix and running
the strengthened corpus showed chunk success=True with T-3119's fix
already committed, because run_split never executed that code path.
Fixed by deduping _run_chunk_verify to delegate to run_verify_outcomes
(scope widened to _split.py with a recorded reason). Re-proved after the
dedup: the same revert-T-3122 experiment now correctly reports chunk
success=False, rolled_back=True -- confirming the existing rollback
machinery triggers on the new check's failure with no changes needed to
rollback itself.

T-3110's corpus (tests/test_refactor_corpus.py) strengthened per the
brief: added _assert_all_py_files_importable (real subprocess import,
not ast.parse) plus a MovedEnum(StrEnum) corpus symbol matching T-3122's
exact shape (valid syntax, no local-import-resolution violation,
NameError only at real import time) -- confirmed the OLD parse-only
corpus would NOT have caught this (it only checks syntax).

Also fixed along the way: both the production check and the corpus's
own importability helper were writing __pycache__/.coverage.* files
into the target/fixture repo's own working tree as an import side
effect (PYTHONDONTWRITEBYTECODE + stripped COVERAGE_PROCESS_START/
COVERAGE_FILE now prevent this).

Update: TEST016 flagged the T-3119 dedup change's `pytest_scope_touched_only=True`
argument as confirmatory-only (0/1 mutants killed) -- added
tests/test_refactor.py::TestRunSplit::test_run_chunk_verify_scopes_pytest_collect_to_touched_files,
a direct unit test on _run_chunk_verify's delegation that monkeypatches
verify_pytest_collect and asserts the touched-files list is actually
passed through as targets (not None). Recorded as evidence.

### Changed
```
 docs/commands/refactor.md     |  36 ++++++++++-
 rapid-debt.jsonl              |   1 +
 src/frob/refactor/_commit.py  |  22 +++++--
 src/frob/refactor/_split.py   |  38 ++++++-----
 src/frob/refactor/_verify.py  | 143 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_refactor.py        |  78 ++++++++++++++++++++++-
 tests/test_refactor_corpus.py |  93 ++++++++++++++++++++++++++-
 tickets/T-3119/done-report.md |  78 +++++++++++++++++++++++
 tickets/T-3119/ticket.md      |  23 ++++++-
 tickets/T-3133/ticket.md      |  92 +++++++++++++++++++++++++++
 10 files changed, 576 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestVerify::test_module_import_catches_missing_import` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestVerify::test_module_import_passes_clean_module` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestCommit::test_run_verify_outcomes_runs_requested_checks` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunSplit::test_run_chunk_verify_scopes_pytest_collect_to_touched_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 83 error(s), 714 warning(s), 865 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3119/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3119, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
