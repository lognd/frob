## Done report

Changed:
.github/workflows/release.yml::jobs.upload-frob-core
.github/workflows/release.yml::jobs.upload-strata-core
.github/workflows/release.yml::jobs.upload-frob
tests/unit/test_release_workflow_gate.py::TestUploadJobConsentGate
tests/unit/test_release_workflow_gate.py::TestUploadSplitPerDistribution
tests/unit/test_release_workflow_gate.py::TestApprovalGateDecisionIsRecorded

Evidence:
tests/unit/test_release_workflow_gate.py::TestUploadJobConsentGate::test_upload_job_no_longer_exists_as_a_single_job
tests/unit/test_release_workflow_gate.py::TestUploadJobConsentGate::test_kernel_upload_jobs_have_their_own_distinct_environments
tests/unit/test_release_workflow_gate.py::TestUploadSplitPerDistribution::test_application_upload_needs_both_kernel_uploads
tests/unit/test_release_workflow_gate.py::TestUploadSplitPerDistribution::test_kernel_upload_jobs_do_not_depend_on_the_application
tests/unit/test_release_workflow_gate.py::TestApprovalGateDecisionIsRecorded::test_workflow_records_which_distributions_require_a_reviewer
tests/unit/test_release_workflow_gate.py::TestApprovalGateDecisionIsRecorded::test_only_application_environment_is_the_pre_existing_protected_one

Plus (not pytest-bound, recorded here as supporting proof): a nektos/act
0.2.89 run of a job-graph-only simulation of the split (identical
needs:/environment: graph, every step body stubbed to a non-network
no-op) forcing upload-frob-core to fail. Result: upload-strata-core
still ran and succeeded independently; upload-frob never started at
all -- act reports `Error: Job 'upload-frob-core' failed` and exits
without ever logging a Main step for upload-frob, even when explicitly
targeted with `--job upload-frob`. This exercises the real GitHub
Actions dependency-resolution engine's `needs:` skip semantics against
this exact job graph. No network call to PyPI, and no real GitHub
Actions dispatch against this repo, was made anywhere in this
ticket's verification (per the ticket's own "verify without
publishing" instruction).

Filed: T-4276 -- docs/guides/release.md still describes the
old single-`upload`-job shape throughout (job-graph description, the
"Proof: a normal push does not upload" section, the release-cut
procedure's step list, Decision 3/4 discussions); none of that is
wrong in substance but the job name it names no longer exists. Out of
this ticket's `.github/workflows/release.yml`-only scope, so filed
rather than fixed here.

Gates: `frob check --ticket T-4263` (chunked via `--only
gates-fast/gates-native/gates-security/lint/static`, per T-0627's
foreground-cap guidance) shows this ticket's own scope/pre-work/
diff-driven gates (SCOPE, PRE, and the ticket-scoped slice of COV/FMT/
AFFECT) clean, with zero hits for T-4263, T-3011, release.yml, or
test_release_workflow_gate.py in any FAILing gate family across all
five runs. The FAILing families present (gate:COV 8 errors -- all
T-4178, an unrelated ticket's stale evidence; gate:DRIFT 3 errors --
all internal src/frob/gates and src/frob/tickets symbols; gate:ARCH 1
error; a repo-wide `ruff-format` count of 32 files) are pre-existing,
repo-wide baseline state this ticket did not touch and is not
responsible for.

pytest tests/unit/test_release_workflow_gate.py -q -p no:xdist: 29
passed, 0 failed (27 pre-existing + 2 renamed-in-place to preserve
T-3011/T-3251/T-3884's exact bound evidence node ids, plus 5 new for
this ticket's three acceptance criteria).
