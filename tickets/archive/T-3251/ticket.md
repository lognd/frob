---
id: T-3251
title: 'Release can be dispatched from a red main: nothing gates the PyPI upload on
  green CI for the released commit'
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/release.yml
- tests/unit/test_release_workflow_gate.py
- scripts/verify_release_ci_status.py
- tests/unit/test_verify_release_ci_status.py
- docs/guides/release.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/verify_release_ci_status.py
  reason: 'T-3251: the CI-status determination/decide logic is implemented as its
    own testable Python script (scripts/verify_release_ci_status.py, matching this
    repo''s existing scripts/*.py convention) rather than embedded bash+jq in release.yml,
    so it can be deterministically unit-tested without a real gh binary or network
    access'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_verify_release_ci_status.py
  reason: 'T-3251: the CI-status determination/decide logic is implemented as its
    own testable Python script (scripts/verify_release_ci_status.py, matching this
    repo''s existing scripts/*.py convention) rather than embedded bash+jq in release.yml,
    so it can be deterministically unit-tested without a real gh binary or network
    access'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/guides/release.md
  reason: 'T-3251: DOCUMENT AS YOU GO -- the new verify-ci-status job/script''s frob:doc
    anchors point here; added a Decision 4 section explaining the fourth gate, the
    three outcomes, and the override'
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_green_on_success_conclusion
- tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_red_on_failure_conclusion
- tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_api_error
- tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_no_matching_run
- tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_unparseable_json
- tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_undetermined_on_run_still_in_progress
- tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus::test_resolves_by_exact_sha_not_branch_or_latest
- tests/unit/test_verify_release_ci_status.py::TestDecide::test_green_always_proceeds
- tests/unit/test_verify_release_ci_status.py::TestDecide::test_red_without_override_refuses
- tests/unit/test_verify_release_ci_status.py::TestDecide::test_undetermined_without_override_refuses
- tests/unit/test_verify_release_ci_status.py::TestDecide::test_red_with_override_and_reason_proceeds
- tests/unit/test_verify_release_ci_status.py::TestDecide::test_override_without_reason_is_refused_even_when_requested
- tests/unit/test_verify_release_ci_status.py::TestRunGh::test_spawn_failure_reports_as_nonzero_with_stderr
- tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant::test_valid_status_literal_constructs
- tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant::test_invalid_status_literal_raises
- tests/unit/test_verify_release_ci_status.py::TestMain::test_green_path_prints_green_and_exits_zero
- tests/unit/test_verify_release_ci_status.py::TestMain::test_red_path_without_override_exits_nonzero
- tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_verify_ci_status_job_exists_with_actions_read_permission
- tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_verify_ci_status_job_has_no_pypi_environment_gate
- tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_upload_needs_verify_ci_status_in_addition_to_existing_needs
- tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_override_input_declared_and_defaults_to_false
- tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_only_workflow_dispatch_trigger_still_holds_with_inputs
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 159251143da3feaf975d87513b2b80da446c226f
---
OWNER DECISION, 2026-08-28: the goal is a fully green CI matrix and a working
`frob` on PyPI before 1.0.0. PyPI currently serves 0.0.9 and is badly stale. The
owner chose to publish at the repo's existing version authority, 0.530.0, as-is
-- NOT renumbered -- because `.frob-release.json` (REL001 mechanical semver from
public-API digests) already computed it, VERSION001's exact-pin coupling across
frob/frob-core/strata-core already holds at that number, and renumbering would
desync the mechanical-semver chain for cosmetic reasons. This ticket does not
reopen that decision.

THE GAP. `.github/workflows/release.yml` is already well gated for CONSENT
(T-3011): manual `workflow_dispatch` only, no push/tag/schedule trigger, the
upload job needs a `pypi` GitHub Environment with a required reviewer, and it
uses OIDC trusted publishing rather than a stored token. All of that is sound
and must not be weakened.

But NOTHING checks that the commit being released has GREEN CI. The upload job's
`needs: [build, build-sdists]` proves wheels built and import cleanly on each
platform -- it does NOT prove the test suite passed, that `frob check` was
clean, or that the CI matrix was green on that commit. A human can dispatch a
release from a red main and every existing gate says yes.

That is exactly the situation today: the CI matrix has been red or hung on all
three platforms (T-3246, T-3247, T-3250), and nothing in the release path knows
it.

WHY THIS MATTERS MORE THAN USUAL HERE. A PyPI upload is IRREVERSIBLE -- a
version number cannot be reused, even after a yank. This is the one workflow in
the repo where a bad run cannot be fixed by landing a follow-up commit. Every
other gate in this project exists to make unaccounted-for work a build failure;
the one path that publishes to the world is the one with no such gate.

WHAT TO BUILD:
  1. A job that the upload depends on, which refuses unless the CI workflow's
     latest conclusion for THE EXACT COMMIT BEING RELEASED is success on every
     platform in the matrix. Resolve by commit SHA, not by branch name and not
     by "the most recent run" -- a run on a different commit passing is not this
     commit passing.
  2. It must fail CLOSED. If the CI status cannot be determined (API error, no
     run found, run still in progress), REFUSE and say the status is
     UNREADABLE. Do not treat an unreadable status as green. This repo's
     dominant defect class is a failed measurement reported as a successful one,
     and a release is the worst possible place to repeat it. State the three
     outcomes distinctly: GREEN, RED, UNDETERMINED.
  3. Do NOT weaken any existing T-3011 gate to add this. This is a fourth gate,
     not a replacement for one.
  4. There must be a documented, auditable override for a deliberate release
     from a known-red main (a workflow input, recorded on the run) -- but it
     must be explicit, never the default, and the run must record who set it and
     why. An emergency path that does not exist gets worked around by disabling
     the gate.

MUST-FIRE FIXTURE: a dispatch against a commit whose CI failed is refused.
MUST-STAY-QUIET FIXTURE: a dispatch against a commit whose CI passed on all
platforms proceeds to the existing reviewer gate unchanged.
THIRD FIXTURE (the one that matters): a commit whose CI status cannot be
determined is REFUSED with an UNDETERMINED message, never allowed through and
never reported as green.

`tests/unit/test_release_workflow_gate.py` already mechanically asserts that no
automatic trigger exists in this workflow. Extend that file rather than starting
a parallel one, and keep its existing assertions passing.

ACCEPTANCE
- Upload cannot run against a commit without a green CI conclusion for that SHA.
- The three outcomes are distinguished in code and in the operator-facing
  message.
- An explicit, recorded override exists and is not the default.
- All three fixtures present.
- No existing T-3011 consent gate weakened; say explicitly that you checked.