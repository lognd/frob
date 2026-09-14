## Done report

Added a follow-up job-summary step to .github/workflows/ci.yml (shell: bash, if: always()) that re-runs frob check --json (cheap T-2585 replay-cache hit) and appends gate-summary counts, FAIL gate rows, and up to 40 error findings to $GITHUB_STEP_SUMMARY on every leg; the self-gate step now tees its own output to $RUNNER_TEMP/frob-check.log under set -o pipefail/shell: bash so its exit code is unchanged. tests/test_ci_workflow_job_summary.py (new, 11 tests) locks step existence/ordering/always()/shell/no-hard-fail and validates the embedded Python heredoc parses. docs/commands/check.md documents the summary. BUG002 waived (CI-config change, same shape as T-4430). Known gap NOT fixed in-ticket (out of declared scope, design/frob.strata not in scope list): gate:SELFAUDIT reports 2 SYS100/SELFAUDIT001 findings (fs.read observed but not declared for the new test file) -- this detector is suppressible only via a design/frob.strata may-clause on the testsuite node, not via a code-level frob:waive comment (confirmed against src/frob/gates/_fix_engine_sync.py's own doc note); coordinator should file a follow-up ticket scoped to design/frob.strata to add the via-list entry. All other frob check --ticket T-4460 FAIL rows (gate:DRIFT on doctor.py, gate:REF on docs/design/macos-portability.md, ruff-format on tests/test_tickets_triage_dates.py) are pre-existing and untouched by this diff.

### Changed
```
 .github/workflows/ci.yml              | 104 +++++++++++++++++-
 docs/commands/check.md                |  18 ++++
 tests/test_ci_workflow_job_summary.py | 197 ++++++++++++++++++++++++++++++++++
 tickets/T-4460/ticket.md              |  12 +++
 4 files changed, 330 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_job_summary.py::TestSelfGateStepCapturesItsOutput::test_self_gate_step_uses_bash` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestSelfGateStepCapturesItsOutput::test_self_gate_step_tees_to_runner_temp_with_pipefail` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestSelfGateStepCapturesItsOutput::test_self_gate_step_still_runs_frob_check` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_exists` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_is_always` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_uses_bash` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_is_separate_and_runs_after_self_gate` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_reads_json_not_the_human_log` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_python_is_syntactically_valid` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_never_fails_the_job` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_job_summary.py::TestJobSummaryDocumented::test_check_docs_mention_the_job_summary` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 4 error(s), 4868 warning(s), 969 waived
- error-findings: DRIFT001@src/frob/doctor.py, PRE001@tickets/T-4460, REF002@docs/design/macos-portability.md, SELFAUDIT001@tests/test_ci_workflow_job_summary.py
