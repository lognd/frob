## Done report

This ticket's diff touches `.github/workflows/release.yml` (new
`verify-ci-status` job; `upload`'s `needs:` gains it; `workflow_dispatch`
gains `override_red_ci`/`override_reason` inputs), the new `scripts/
verify_release_ci_status.py`, the new `tests/unit/test_verify_release_
ci_status.py`, a new `TestCiStatusGate` class in `tests/unit/test_
release_workflow_gate.py`, and `docs/guides/release.md` (new "Decision
4" section, workflow-structure paragraph updated for the third job) --
the auto-filled Changed section below has the exact file list.

Root cause (as filed): `upload`'s only gates were T-3011's three
(manual-dispatch-only trigger, `needs: [build, build-sdists]`, the
`pypi` environment's required reviewer) -- none of which proves the
released commit's CI was green. A human could dispatch a release from a
red main and every existing gate would say yes.

Fix: a fourth job, `verify-ci-status`, added to `upload`'s `needs:`
(never replacing any of the three existing gates -- confirmed by
`TestCiStatusGate::test_upload_needs_verify_ci_status_in_addition_to_
existing_needs` asserting the FULL set, and `test_only_workflow_
dispatch_trigger_still_holds_with_inputs`/the untouched `test_upload_
job_requires_pypi_environment`/`test_upload_job_uses_oidc_not_a_stored_
token` tests all still passing unmodified). The actual determination
logic lives in `scripts/verify_release_ci_status.py` (a plain,
pydantic-modeled, fully unit-tested Python script -- not embedded
bash+jq in the workflow YAML -- following this repo's own `scripts/*.py`
convention, e.g. `branch_stranded_work_analysis.py`'s `BranchResult`),
so GREEN/RED/UNDETERMINED and the override refusal logic are
deterministically testable without a real `gh` binary or network
access.

`determine_ci_status(repo, sha, workflow="ci.yml")` resolves by
`head_sha=<sha>` (never branch name, never "latest run" unfiltered --
`test_resolves_by_exact_sha_not_branch_or_latest` asserts the exact argv
`gh` is invoked with). Three outcomes, never collapsed:
- GREEN: matching run `status=completed`, `conclusion=success`.
- RED: matching run completed with any other conclusion.
- UNDETERMINED: `gh api` failure, unparseable JSON, no matching run, or
  a run not yet `completed` -- fails CLOSED exactly like RED, never read
  as green.

`decide()` turns a result + override request into `(exit_code,
message)`: GREEN always proceeds; RED/UNDETERMINED refuse UNLESS
`override=True` AND `override_reason` is non-empty (an override with no
reason is refused exactly like no override at all). The workflow's
`override_red_ci` input defaults to `false` (never the default path).

Checked explicitly that no existing T-3011 gate was weakened: `build`/
`build-sdists` still carry no `environment` gate (unchanged tests
`test_build_job_has_no_environment_gate` pass); `upload` still requires
`environment: pypi` and OIDC (`test_upload_job_requires_pypi_
environment`, `test_upload_job_uses_oidc_not_a_stored_token`, both
pre-existing, both still pass unmodified); the `on:` block still
declares only `workflow_dispatch` (`test_only_workflow_dispatch_
trigger` -- pre-existing test, still passes; re-asserted again in the
new `test_only_workflow_dispatch_trigger_still_holds_with_inputs` after
adding `inputs:`).

Fixtures required by the ticket, all present:
- MUST-FIRE (RED refused): `TestDetermineCiStatus::test_red_on_failure_
  conclusion` + `TestDecide::test_red_without_override_refuses` +
  `TestMain::test_red_path_without_override_exits_nonzero`.
- MUST-STAY-QUIET (GREEN proceeds): `TestDetermineCiStatus::test_green_
  on_success_conclusion` + `TestDecide::test_green_always_proceeds` +
  `TestMain::test_green_path_prints_green_and_exits_zero`.
- THIRD FIXTURE (UNDETERMINED refused, never read as green):
  `TestDetermineCiStatus::test_undetermined_on_api_error` /
  `test_undetermined_on_no_matching_run` / `test_undetermined_on_
  unparseable_json` / `test_undetermined_on_run_still_in_progress` +
  `TestDecide::test_undetermined_without_override_refuses`.

Filed: none.

Evidence: 22 node ids bound (`frob ticket evidence T-3251`).

Gates: `frob check --ticket T-3251` for scope/prework/test all clean
(0 errors on gate:SCOPE, gate:PRE, gate:TEST -- confirmed after `git
add`-ing the new files, since this repo's diff-driven gates read the
git index; the two remaining FAILs in a full `--budget` run, gate:DRIFT
and gate:DSL, are pre-existing repo-wide findings unrelated to any file
this ticket touched). `ruff check`/`ruff format --check`/`ty check`
clean on both new files.

### Changed
```
 tickets/T-3251/done-report.md | 120 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3251/ticket.md      |  52 ++++++++++++++++++
 2 files changed, 172 insertions(+)
```

### Evidence
- `tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_green_on_success_conclusion` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_red_on_failure_conclusion` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_api_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_no_matching_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_unparseable_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_run_still_in_progress` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_resolves_by_exact_sha_not_branch_or_latest` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDecide::test_green_always_proceeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDecide::test_red_without_override_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDecide::test_undetermined_without_override_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDecide::test_red_with_override_and_reason_proceeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestDecide::test_override_without_reason_is_refused_even_when_requested` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestRunGh::test_spawn_failure_reports_as_nonzero_with_stderr` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant::test_valid_status_literal_constructs` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant::test_invalid_status_literal_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestMain::test_green_path_prints_green_and_exits_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_release_ci_status.py::TestMain::test_red_path_without_override_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_verify_ci_status_job_exists_with_actions_read_permission` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_verify_ci_status_job_has_no_pypi_environment_gate` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_upload_needs_verify_ci_status_in_addition_to_existing_needs` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_override_input_declared_and_defaults_to_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_only_workflow_dispatch_trigger_still_holds_with_inputs` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 22 passed (from 22 evidence id(s))
- gates: 100 error(s), 3990 warning(s), 878 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@scripts/verify_release_ci_status.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3262/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE001@scripts/verify_release_ci_status.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
