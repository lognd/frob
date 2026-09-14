---
id: T-4460
title: 'CI: write the self-gate and test results to the GitHub job summary'
state: done
kind: feature
origin: human
created: '2026-09-13'
priority: medium
parent: null
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow*.py
- docs/commands/check.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'SYS100: testsuite fs.read via-list for tests/test_ci_workflow_job_summary.py'
  actor: logan
  at: '2026-09-14'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: 'SYS100: testsuite fs.read via-list for tests/test_ci_workflow_job_summary.py'
  actor: logan
  at: '2026-09-14'
evidence:
- tests/test_ci_workflow_job_summary.py::TestSelfGateStepCapturesItsOutput::test_self_gate_step_uses_bash
- tests/test_ci_workflow_job_summary.py::TestSelfGateStepCapturesItsOutput::test_self_gate_step_tees_to_runner_temp_with_pipefail
- tests/test_ci_workflow_job_summary.py::TestSelfGateStepCapturesItsOutput::test_self_gate_step_still_runs_frob_check
- tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_exists
- tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_is_always
- tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_uses_bash
- tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_is_separate_and_runs_after_self_gate
- tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_reads_json_not_the_human_log
- tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_python_is_syntactically_valid
- tests/test_ci_workflow_job_summary.py::TestJobSummaryStepExists::test_summary_step_never_fails_the_job
- tests/test_ci_workflow_job_summary.py::TestJobSummaryDocumented::test_check_docs_mention_the_job_summary
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User request 2026-09-12: the ubuntu self-gate step failed in CI and the run page showed no summary -- the per-gate rows and the gate-summary line only exist inside the step log (thousands of lines up), and nothing writes $GITHUB_STEP_SUMMARY. ACCEPTANCE: (1) the self-gate step (and the Test step's SUITE-RESULT lines) append a compact Markdown block to $GITHUB_STEP_SUMMARY on every leg: gate-summary counts, the FAIL gate rows, and up to N error findings with rule id + file:line, plus the failed test node ids; (2) written even when the step fails (use `if: always()` on a follow-up step that reads a saved JSON, not the failing step itself); (3) tests/test_ci_workflow*.py assert the summary step exists on all legs and runs after the self-gate with always(); (4) docs/commands/check.md mentions the summary. Sprint v0.532.0.