---
id: T-4265
title: delete the thirteen obsolete windows hang-diagnosis step blocks from the integration
  workflow, whose six tickets are all closed
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_is_gated_to_ubuntu_only
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_does_not_shell_to_make
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_stamp_baseline_is_bare_not_chunked_by_only
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_calls_frob_coverage_full
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_suite_runs_under_coverage_once_not_twice
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_ignore_console_ctrl
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_hard_exit
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_midrun_watchdog_seconds
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_raises_per_test_timeout_to_600
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_surfaces_failure_tracebacks
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_is_untouched_and_still_windows_only
- tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_ubuntu_test_step_no_reruns_flakes
- tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_macos_test_step_no_reruns_flakes
- tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_windows_test_step_no_reruns_flakes
designated_repro_test: null
acceptance:
- text: given the integration workflow, when the cleanup lands, then no diagnostic
    step block remains whose originating ticket is closed, and each removal was confirmed
    against that ticket individually
  evidence:
  - tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
  - tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos
  - tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_is_gated_to_ubuntu_only
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_does_not_shell_to_make
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_stamp_baseline_is_bare_not_chunked_by_only
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_calls_frob_coverage_full
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_suite_runs_under_coverage_once_not_twice
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_ignore_console_ctrl
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_hard_exit
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_midrun_watchdog_seconds
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_raises_per_test_timeout_to_600
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_surfaces_failure_tracebacks
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_is_untouched_and_still_windows_only
  - tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_ubuntu_test_step_no_reruns_flakes
  - tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_macos_test_step_no_reruns_flakes
  - tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_windows_test_step_no_reruns_flakes
- text: given the workflow's own matrix test, when steps are removed, then its assertions
    are updated to reflect a deliberate decision about each pinned step rather than
    deleted to match the new file
  evidence:
  - tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
  - tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos
  - tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_is_gated_to_ubuntu_only
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_does_not_shell_to_make
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_stamp_baseline_is_bare_not_chunked_by_only
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_calls_frob_coverage_full
  - tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_suite_runs_under_coverage_once_not_twice
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_ignore_console_ctrl
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_hard_exit
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_midrun_watchdog_seconds
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_raises_per_test_timeout_to_600
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_surfaces_failure_tracebacks
  - tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_is_untouched_and_still_windows_only
  - tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_ubuntu_test_step_no_reruns_flakes
  - tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_macos_test_step_no_reruns_flakes
  - tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_windows_test_step_no_reruns_flakes
- text: given the windows leg, when the cleanup lands, then its wall-clock duration
    before and after is reported, including the case where it did not improve
  evidence:
  - tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REMOVE THE OBSOLETE WINDOWS HANG-DIAGNOSIS SCAFFOLDING FROM THE INTEGRATION
WORKFLOW. Thirteen separate diagnostic step blocks remain in the workflow, each
gated to the windows runner, each a variant of the same investigation into a
hang that has since been fixed. Every one of the six tickets that added them is
closed.

WHY THIS IS NOT MERELY TIDINESS. Several of those variants invoke the check
command themselves, with different mitigations enabled or disabled, before the
real test and gate steps run. On the run measured while filing this, the linux
leg finished in about thirty minutes, the macos leg in about thirty-nine, and
the windows leg had not finished after more than an hour. The scaffolding is a
plausible large share of that gap, and the windows leg's duration is currently
one of the practical obstacles to getting a green result at all.

THE TICKETS THAT ADDED THEM ARE ALL DONE. Confirm each individually before
deleting its block rather than trusting this list, but the investigation series
is closed and its conclusions already landed as real fixes and guards elsewhere
in the tree. A diagnostic that exists to characterise a resolved defect is
answered evidence, not a check.

DELETE, DO NOT DISABLE. Commenting the blocks out or gating them behind a flag
keeps the maintenance burden and the reading cost while removing the value. If a
future hang needs this apparatus it can be recovered from history, which is what
history is for.

BEWARE THE WORKFLOW'S OWN VALIDATOR. A test file asserts against the workflow
matrix's content, and several of the closed tickets list both that test and the
workflow in their scope. Removing steps will very likely break assertions there.
That test is the thing that will tell you whether you removed something load-
bearing, so read its failures carefully rather than deleting assertions to match
the new file. If an assertion pinned a diagnostic step deliberately, decide
whether the intent survives the diagnostic.

DO NOT TOUCH THE ADVISORY FLAG ON THE WINDOWS JOB IN THIS TICKET. Removing that
flag is the finish line of a separate epic and depends on the windows failure set
reaching zero, which is not what this ticket does.

MEASURE THE RESULT. Report the windows leg's wall-clock duration before and
after. If removing the scaffolding does not measurably shorten it, say so
plainly -- the cleanup is still worth doing, but the timing claim above would
then be wrong and should be corrected rather than repeated.
