"""Mechanical proof (T-3011) that `.github/workflows/release.yml` cannot be
reached by anything other than a human's explicit manual dispatch, and
that its `upload` job stays behind the consent gate -- see
docs/guides/release.md's "Proof: a normal push does not upload" section.
This parses the REAL workflow files in this repo, not a fixture copy: a
regression here means the actual CI configuration drifted, not a stale
test."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RELEASE_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "release.yml"
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

# GitHub Actions parses the `on:` key as the boolean `True` in plain YAML
# (`on` is a YAML 1.1 boolean alias) -- PyYAML's safe_load reproduces that
# quirk, so the trigger dict is keyed by `True`, not the string "on".
_ON_KEY = True


def _load(path: Path) -> dict:
    """Parse a workflow YAML file -- fails the test loudly (not a skip) if
    either workflow file is missing or unparseable, since that is itself
    exactly the kind of drift this test exists to catch."""
    assert path.exists(), f"expected workflow file missing: {path}"
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    assert isinstance(doc, dict)
    return doc


class TestReleaseWorkflowNoAutomaticTrigger:
    """`release.yml` must declare `workflow_dispatch` and NOTHING else
    under `on:` -- no push, no pull_request, no schedule, no tag, no
    `release` event."""

    def test_only_workflow_dispatch_trigger(self) -> None:
        """The literal acceptance test: a normal push/tag/merge produces
        NO event this workflow listens for."""
        doc = _load(_RELEASE_WORKFLOW)
        triggers = doc[_ON_KEY]
        assert isinstance(triggers, dict), (
            f"expected a mapping of trigger events, got {triggers!r} -- a "
            f"bare string/list form can still smuggle in an unexpected event"
        )
        assert set(triggers) == {"workflow_dispatch"}, (
            f"release.yml's on: block has grown an automatic trigger: "
            f"{set(triggers) - {'workflow_dispatch'}}"
        )

    def test_ci_workflow_never_references_release_or_pypi(self) -> None:
        """The push/PR-triggered `ci.yml` must never call into
        `release.yml`, the `pypi` environment, or a PyPI publish action --
        confirms there is no back-door path from an ordinary push to an
        upload."""
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        for forbidden in ("release.yml", "pypi-publish", "environment: pypi"):
            assert forbidden not in text, (
                f"ci.yml (push/PR triggered) references {forbidden!r} -- "
                f"this would let an ordinary push reach the upload gate"
            )


class TestUploadJobConsentGate:
    """`release.yml`'s `upload` job must stay behind the protected
    `pypi` environment and depend on `build` having actually run."""

    def test_upload_job_requires_pypi_environment(self) -> None:
        """`environment: pypi` is what makes GitHub enforce the required-
        reviewer approval -- losing this line silently turns the gate
        into a no-op."""
        doc = _load(_RELEASE_WORKFLOW)
        upload = doc["jobs"]["upload"]
        assert upload.get("environment") == "pypi", (
            "release.yml's upload job lost its 'environment: pypi' gate -- "
            "this is the ONLY thing that makes GitHub require reviewer "
            "approval before this job can run"
        )

    def test_upload_job_needs_build(self) -> None:
        """`upload` must not be reachable except after `build` (and the
        sdist build) actually produced artifacts -- prevents an upload
        of stale or non-existent artifacts from a differently-ordered
        workflow edit."""
        doc = _load(_RELEASE_WORKFLOW)
        upload = doc["jobs"]["upload"]
        needs = upload.get("needs")
        needs_set = {needs} if isinstance(needs, str) else set(needs or ())
        assert "build" in needs_set

    def test_upload_job_uses_oidc_not_a_stored_token(self) -> None:
        """Trusted publishing: `id-token: write`, and no `password`/token
        input anywhere in the job -- a stored PyPI API token in
        repository secrets is exactly the long-lived-credential risk
        trusted publishing exists to remove."""
        doc = _load(_RELEASE_WORKFLOW)
        upload = doc["jobs"]["upload"]
        assert upload.get("permissions", {}).get("id-token") == "write"
        text = yaml.safe_dump(upload)
        assert "password" not in text and "PYPI_API_TOKEN" not in text

    def test_build_job_has_no_environment_gate(self) -> None:
        """`build` (and `build-sdists`) must NOT carry the `pypi`
        environment gate -- building and retaining wheels as CI artifacts
        is never consent-gated, only the upload is. A gate accidentally
        copied onto `build` would block the "prove it built" half this
        ticket's acceptance requires to run on every dispatch."""
        doc = _load(_RELEASE_WORKFLOW)
        for job_name in ("build", "build-sdists"):
            job = doc["jobs"][job_name]
            assert "environment" not in job, (
                f"release.yml's {job_name} job must not require approval -- "
                f"only upload is consent-gated"
            )


# frob:ticket T-3251
class TestCiStatusGate:
    """T-3251: `upload` must not run against a commit whose CI is not
    provably green -- a fourth gate ADDED alongside T-3011's three
    (consent/needs-build/manual-dispatch-only), never a replacement for
    any of them."""

    def test_verify_ci_status_job_exists_with_actions_read_permission(self) -> None:
        doc = _load(_RELEASE_WORKFLOW)
        job = doc["jobs"]["verify-ci-status"]
        assert job.get("permissions", {}).get("actions") == "read", (
            "verify-ci-status needs actions:read to query ci.yml's runs "
            "via the GitHub API"
        )

    def test_verify_ci_status_job_has_no_pypi_environment_gate(self) -> None:
        """This job must stay UNgated itself (no reviewer approval to
        merely CHECK a status) -- only `upload` carries the `pypi`
        environment; the whole point is refusing automatically, not
        adding a second human approval step."""
        doc = _load(_RELEASE_WORKFLOW)
        job = doc["jobs"]["verify-ci-status"]
        assert "environment" not in job

    def test_upload_needs_verify_ci_status_in_addition_to_existing_needs(self) -> None:
        """T-3251 ADDS to `needs:`, it does not replace `build`/
        `build-sdists` -- losing either of those would reintroduce the
        stale/non-existent-artifact risk `test_upload_job_needs_build`
        above already guards."""
        doc = _load(_RELEASE_WORKFLOW)
        needs = doc["jobs"]["upload"]["needs"]
        needs_set = {needs} if isinstance(needs, str) else set(needs)
        assert needs_set == {"build", "build-sdists", "verify-ci-status"}

    def test_override_input_declared_and_defaults_to_false(self) -> None:
        """The escape hatch exists, but its default must be false (never
        the implicit path) and it must require a reason input alongside
        it -- an override with no way to record why would be exactly the
        silent workaround this gate exists to prevent."""
        doc = _load(_RELEASE_WORKFLOW)
        inputs = doc[_ON_KEY]["workflow_dispatch"]["inputs"]
        assert inputs["override_red_ci"]["default"] is False
        assert inputs["override_red_ci"]["type"] == "boolean"
        assert "override_reason" in inputs

    def test_only_workflow_dispatch_trigger_still_holds_with_inputs(self) -> None:
        """Adding `inputs:` under `workflow_dispatch` must not smuggle in
        a second top-level trigger key -- re-asserts
        TestReleaseWorkflowNoAutomaticTrigger's own invariant after this
        ticket's edit, since that class's fixture predates `inputs:`
        existing at all."""
        doc = _load(_RELEASE_WORKFLOW)
        assert set(doc[_ON_KEY]) == {"workflow_dispatch"}


class TestCiWindowsLegAdvisoryOnly:
    """T-3425: only the windows-latest matrix leg may be advisory
    (continue-on-error) in ci.yml's build job -- ubuntu-latest and
    macos-latest must still fail the workflow on a test failure. See
    docs/design/windows-portability.md."""

    def test_build_job_continue_on_error_is_windows_only(self) -> None:
        """MUST-FIRE: the job-level `continue-on-error` expression must
        name matrix.os == 'windows-latest' and nothing broader (e.g. not
        an unconditional `true`, which would silence ubuntu/macOS too)."""
        doc = _load(_CI_WORKFLOW)
        job = doc["jobs"]["build"]
        assert "continue-on-error" in job, (
            "expected T-3425's windows-latest advisory flag on the build "
            "job -- see docs/design/windows-portability.md"
        )
        expr = job["continue-on-error"]
        assert isinstance(expr, str)
        assert "matrix.os" in expr and "windows-latest" in expr, (
            f"continue-on-error must be conditioned on matrix.os == "
            f"'windows-latest', got: {expr!r}"
        )
        assert "ubuntu-latest" not in expr and "macos-latest" not in expr, (
            f"continue-on-error must not also cover ubuntu/macos: {expr!r}"
        )

    def test_matrix_still_includes_all_three_platforms(self) -> None:
        """MUST-STAY-QUIET companion: the advisory flag must not have been
        achieved by dropping windows-latest from the matrix instead --
        the job must still run (and report) on all three platforms."""
        doc = _load(_CI_WORKFLOW)
        matrix_os = doc["jobs"]["build"]["strategy"]["matrix"]["os"]
        assert set(matrix_os) == {"ubuntu-latest", "windows-latest", "macos-latest"}

    def test_no_step_level_continue_on_error_smuggled_onto_other_legs(self) -> None:
        """MUST-STAY-QUIET: no individual step in the build job may carry
        its own unconditional continue-on-error -- the only advisory
        surface is the single job-level expression asserted above."""
        doc = _load(_CI_WORKFLOW)
        for step in doc["jobs"]["build"].get("steps", []):
            assert "continue-on-error" not in step, (
                f"unexpected step-level continue-on-error on step "
                f"{step.get('name', '<unnamed>')!r} -- the advisory "
                f"boundary must stay job-level and windows-only"
            )


class TestCiUbuntuTestBudgetRaised:
    """T-3426: run 33277131782 proved the ubuntu Test step's 25m budget was
    too tight for a PASSING run (99% at ~20m, killed at 25m mid-self-scan-
    test, not blocked on a lock). The step budget must be raised to at
    least 40m and the job-level ceiling must stay strictly above it, so
    the step's own stack-dump-on-hang fires first on a genuine hang."""

    def test_ubuntu_test_step_budget_at_least_40_minutes(self) -> None:
        """MUST-FIRE: the ubuntu Test step's `timeout -s ABRT <N>m` budget
        must be >= 40m."""
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"timeout -s ABRT (\d+)m uv run pytest -q", text
        )
        assert match, "expected ubuntu's `timeout -s ABRT <N>m uv run pytest -q` step"
        assert int(match.group(1)) >= 40, (
            f"ubuntu Test step budget regressed below 40m: {match.group(0)!r}"
        )

    def test_job_timeout_minutes_exceeds_ubuntu_step_budget(self) -> None:
        """MUST-FIRE: the job-level ceiling must remain strictly greater
        than the ubuntu step budget, so the step's own instrumented
        timeout (with a stack dump) fires before the bare job ceiling."""
        doc = _load(_CI_WORKFLOW)
        job_timeout = doc["jobs"]["build"]["timeout-minutes"]
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        match = re.search(r"timeout -s ABRT (\d+)m uv run pytest -q", text)
        assert match
        step_budget = int(match.group(1))
        assert job_timeout > step_budget, (
            f"job timeout-minutes ({job_timeout}) must exceed the ubuntu "
            f"step budget ({step_budget}m)"
        )

    def test_ubuntu_step_still_uses_faulthandler_and_sigabrt(self) -> None:
        """MUST-STAY-QUIET: the budget raise must not have dropped the
        stack-dump-on-hang mechanism (PYTHONFAULTHANDLER=1 + `timeout -s
        ABRT`, not the default SIGTERM)."""
        doc = _load(_CI_WORKFLOW)
        for step in doc["jobs"]["build"]["steps"]:
            if step.get("name", "").startswith("Test (ubuntu"):
                assert step["env"]["PYTHONFAULTHANDLER"] == "1"
                assert "timeout -s ABRT" in step["run"]
                return
        raise AssertionError("no ubuntu Test step found")
