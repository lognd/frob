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


def _find_step_by_name_prefix(job: dict, name_prefix: str) -> dict:
    """Return the first step in `job` whose `name` starts with
    `name_prefix`, raising loudly (not returning None) if no step
    matches -- shared lookup so callers do not each re-write their own
    for/if/return-or-raise loop over a job's steps (frob:doc DUP001)."""
    for step in job["steps"]:
        if step.get("name", "").startswith(name_prefix):
            return step
    raise AssertionError(f"no step named {name_prefix!r} found")


def _assert_step_uses_faulthandler_and_marker(name_prefix: str, marker: str) -> None:
    """Shared MUST-STAY-QUIET check (T-3426/T-3482) for the ubuntu/macOS
    Test steps: PYTHONFAULTHANDLER=1 plus each platform's own
    SIGABRT-capable stack-dump trigger (`timeout -s ABRT` on ubuntu,
    `kill -ABRT` on macOS -- `marker` picks which). Extracted so the
    ubuntu/macOS variants of this same assertion do not duplicate each
    other's body (frob:doc DUP001)."""
    doc = _load(_CI_WORKFLOW)
    step = _find_step_by_name_prefix(doc["jobs"]["build"], name_prefix)
    assert step["env"]["PYTHONFAULTHANDLER"] == "1"
    assert marker in step["run"]


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


# frob:ticket T-4263
class TestUploadJobConsentGate:
    """T-4263: the single `upload` job was split into one job per
    distribution (`upload-frob-core`, `upload-frob-strata`,
    `upload-frob`) so each can register its own pending trusted
    publisher -- see the split's own comment block in release.yml. Every
    upload-* job must still depend on `build` having actually run."""

    _UPLOAD_JOBS = ("upload-frob-core", "upload-frob-strata", "upload-frob")

    def test_upload_job_no_longer_exists_as_a_single_job(self) -> None:
        """MUST-STAY-QUIET: guards against a regression back to the
        single-job shape T-4263 fixed."""
        doc = _load(_RELEASE_WORKFLOW)
        assert "upload" not in doc["jobs"], (
            "a single 'upload' job reappeared -- this is exactly the "
            "shape T-4263 split apart because it made all three "
            "distributions claim an identical pending-trusted-publisher "
            "configuration"
        )

    def test_upload_job_requires_pypi_environment(self) -> None:
        """`environment: pypi` is what makes GitHub enforce the required-
        reviewer approval on the application publish -- losing this line
        silently turns the gate into a no-op. T-4263 renamed the single
        `upload` job to `upload-frob` (the application distribution);
        this test's NAME stays as originally bound (T-3011's evidence
        citation), its BODY now points at the renamed job."""
        doc = _load(_RELEASE_WORKFLOW)
        upload = doc["jobs"]["upload-frob"]
        assert upload.get("environment") == "pypi", (
            "release.yml's upload-frob job lost its 'environment: pypi' "
            "gate -- this is the ONLY thing that makes GitHub require "
            "reviewer approval before this job can run"
        )

    def test_kernel_upload_jobs_have_their_own_distinct_environments(self) -> None:
        """T-4263 acceptance #1: each distribution's environment name
        must be distinct from the other two, or the pending-trusted-
        publisher tuple collides again."""
        doc = _load(_RELEASE_WORKFLOW)
        envs = {name: doc["jobs"][name]["environment"] for name in self._UPLOAD_JOBS}
        assert len(set(envs.values())) == 3, (
            f"upload-* jobs must each use a distinct environment name, "
            f"got {envs!r} -- a repeated environment name reproduces the "
            f"pending-trusted-publisher collision T-4263 fixed"
        )

    def test_upload_job_needs_build(self) -> None:
        """Every upload-* job must not be reachable except after `build`
        (and the sdist build) actually produced artifacts -- prevents an
        upload of stale or non-existent artifacts from a differently-
        ordered workflow edit. T-4263 widened this from the single
        `upload` job to all three split jobs; name kept as originally
        bound (T-3011's evidence citation)."""
        doc = _load(_RELEASE_WORKFLOW)
        for name in self._UPLOAD_JOBS:
            needs = doc["jobs"][name].get("needs")
            needs_set = {needs} if isinstance(needs, str) else set(needs or ())
            assert "build" in needs_set, f"{name} must depend on build"

    def test_upload_job_uses_oidc_not_a_stored_token(self) -> None:
        """Trusted publishing: `id-token: write`, and no `password`/token
        input anywhere in any upload-* job -- a stored PyPI API token in
        repository secrets is exactly the long-lived-credential risk
        trusted publishing exists to remove. T-4263 widened this from
        the single `upload` job to all three split jobs; name kept as
        originally bound (T-3011's evidence citation)."""
        doc = _load(_RELEASE_WORKFLOW)
        for name in self._UPLOAD_JOBS:
            job = doc["jobs"][name]
            assert job.get("permissions", {}).get("id-token") == "write"
            text = yaml.safe_dump(job)
            assert "password" not in text and "PYPI_API_TOKEN" not in text

    def test_build_job_has_no_environment_gate(self) -> None:
        """`build` (and `build-sdists`) must NOT carry a `pypi*`
        environment gate -- building and retaining wheels as CI artifacts
        is never consent-gated, only the upload jobs are. A gate
        accidentally copied onto `build` would block the "prove it
        built" half this ticket's acceptance requires to run on every
        dispatch."""
        doc = _load(_RELEASE_WORKFLOW)
        for job_name in ("build", "build-sdists"):
            job = doc["jobs"][job_name]
            assert "environment" not in job, (
                f"release.yml's {job_name} job must not require approval -- "
                f"only the upload-* jobs are consent-gated"
            )


# frob:ticket T-4263
class TestUploadSplitPerDistribution:
    """T-4263 acceptance #2: preserves the ordering contract (the
    application pins both kernels by exact version, so an application
    published without them is uninstallable) as an explicit job
    dependency rather than in-job step order."""

    def test_application_upload_needs_both_kernel_uploads(self) -> None:
        """MUST-FIRE: `upload-frob`'s needs: must name both kernel
        upload jobs -- GitHub Actions skips a job whose `needs:` entry
        failed or was skipped, so this is what makes a kernel publish
        failure prevent the application from publishing at all."""
        doc = _load(_RELEASE_WORKFLOW)
        needs = doc["jobs"]["upload-frob"]["needs"]
        needs_set = {needs} if isinstance(needs, str) else set(needs)
        assert {"upload-frob-core", "upload-frob-strata"} <= needs_set, (
            f"upload-frob must depend on both kernel upload jobs to "
            f"preserve the ordering contract, got needs={needs_set!r}"
        )

    def test_kernel_upload_jobs_do_not_depend_on_the_application(self) -> None:
        """MUST-STAY-QUIET: the dependency is one-directional -- a kernel
        job must never need the application job, or the ordering
        contract (kernels before application) would be reversed/cyclic."""
        doc = _load(_RELEASE_WORKFLOW)
        for name in ("upload-frob-core", "upload-frob-strata"):
            needs = doc["jobs"][name].get("needs")
            needs_set = {needs} if isinstance(needs, str) else set(needs or ())
            assert "upload-frob" not in needs_set


# frob:ticket T-4263
class TestApprovalGateDecisionIsRecorded:
    """T-4263 acceptance #3: the split's approval-gate decision (only the
    application requires a reviewer; the two kernel environments
    deliberately do not) must be recorded in the workflow file itself,
    not only in the ticket -- so the next person editing release.yml
    reads it in place."""

    def test_workflow_records_which_distributions_require_a_reviewer(self) -> None:
        """MUST-FIRE: a comment naming the decision must exist directly
        above the split jobs -- not merely true by construction, but
        actually written down where the next editor will see it."""
        text = _RELEASE_WORKFLOW.read_text(encoding="utf-8")
        assert "APPROVAL-GATE DECISION" in text, (
            "release.yml must record, in a comment, the decision about "
            "which upload-* jobs require a reviewer -- three environments "
            "can otherwise mean three approval prompts for one release "
            "with no record of why"
        )
        assert "required-reviewer environment" in text, (
            "release.yml's recorded decision must name which job(s) carry "
            "the required-reviewer environment"
        )

    def test_only_application_environment_is_the_pre_existing_protected_one(
        self,
    ) -> None:
        """MUST-STAY-QUIET: the decision text above is backed by the
        actual config -- `upload-frob` keeps the original `pypi`
        environment name (the one already configured with a required
        reviewer in this repo's Settings > Environments before this
        split), while the two new kernel environments use NEW names that
        cannot already carry that protection."""
        doc = _load(_RELEASE_WORKFLOW)
        assert doc["jobs"]["upload-frob"]["environment"] == "pypi"
        for name in ("upload-frob-core", "upload-frob-strata"):
            env = doc["jobs"][name]["environment"]
            assert env != "pypi", (
                f"{name} must not reuse the 'pypi' environment name -- "
                f"doing so would either collide with the application's "
                f"protected environment or silently inherit its reviewer "
                f"gate depending on GitHub's settings, neither of which "
                f"is the deliberate decision recorded above"
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

    def test_upload_needs_verify_ci_status_in_addition_to_existing_needs(
        self,
    ) -> None:
        """T-3251/T-3884 ADD to `needs:`, neither replaces `build`/
        `build-sdists` -- losing either of those would reintroduce the
        stale/non-existent-artifact risk `test_upload_job_needs_build`
        above already guards. T-4263 split `upload` into three jobs;
        the two kernel jobs must carry exactly the original four-entry
        needs set, while `upload-frob` ADDS the two kernel jobs on top
        (checked separately by
        TestUploadSplitPerDistribution.test_application_upload_needs_both_kernel_uploads)."""
        doc = _load(_RELEASE_WORKFLOW)
        base_needs = {"build", "build-sdists", "verify-ci-status", "artifact-smoke"}
        for name in ("upload-frob-core", "upload-frob-strata"):
            needs = doc["jobs"][name]["needs"]
            needs_set = {needs} if isinstance(needs, str) else set(needs)
            assert needs_set == base_needs, f"{name}: needs={needs_set!r}"
        upload_frob_needs = set(doc["jobs"]["upload-frob"]["needs"])
        assert base_needs <= upload_frob_needs

    def test_artifact_smoke_job_needs_build_and_build_sdists(self) -> None:
        """T-3884: `artifact-smoke` must depend on `build` (this
        platform's frob-core/strata-core wheels) AND `build-sdists` (the
        universal frob wheel) -- either missing would make it install a
        stale or nonexistent artifact."""
        doc = _load(_RELEASE_WORKFLOW)
        needs = doc["jobs"]["artifact-smoke"]["needs"]
        needs_set = {needs} if isinstance(needs, str) else set(needs)
        assert needs_set == {"build", "build-sdists"}

    # T-4470: macos-x86_64 is a CROSS build on the arm64 macos-latest
    # runner -- see `build`'s matrix comment. `artifact-smoke` does more
    # than import the wheel (it installs into a clean venv and RUNS real
    # `frob` commands via artifact_smoke.py), which needs a genuinely
    # executable x86_64 interpreter this repo has no verified way to get
    # on that runner, so this one target is deliberately excluded from
    # smoke coverage (docs/guides/release.md documents the boundary).
    _SMOKE_EXEMPT_TARGETS = frozenset({"macos-x86_64"})

    def test_artifact_smoke_covers_every_build_target(self) -> None:
        """T-3884: a linux-only smoke test would not catch a
        Windows-only packaging fault -- `artifact-smoke`'s matrix must
        cover every target `build`'s own matrix covers, except the
        documented cross-build exemption above."""
        doc = _load(_RELEASE_WORKFLOW)
        build_targets = {
            entry["target"]
            for entry in doc["jobs"]["build"]["strategy"]["matrix"]["include"]
        }
        smoke_targets = {
            entry["target"]
            for entry in doc["jobs"]["artifact-smoke"]["strategy"]["matrix"]["include"]
        }
        assert smoke_targets == build_targets - self._SMOKE_EXEMPT_TARGETS
        assert smoke_targets.isdisjoint(self._SMOKE_EXEMPT_TARGETS)

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


# frob:ticket T-3512
# frob:tests TestCiWindowsLegAdvisoryOnly
class TestCiWindowsLegAdvisoryOnly:
    """T-3512 (closing T-3425): windows-latest is a normal, blocking
    matrix leg again -- the job-level `continue-on-error` advisory flag
    was removed once CI run 34758499278 (head 020d2db1f, 2026-09-13)
    measured green on all three legs. ubuntu-latest and macos-latest
    were never advisory and remain unaffected. See
    docs/design/windows-portability.md."""

    def test_build_job_continue_on_error_is_windows_only(self) -> None:
        """MUST-FIRE regression guard: the job-level `continue-on-error`
        key must be ABSENT from the build job -- if it ever reappears,
        this must fail so reintroducing the advisory carve-out requires
        a ticket, not a silent edit."""
        doc = _load(_CI_WORKFLOW)
        job = doc["jobs"]["build"]
        assert "continue-on-error" not in job, (
            "the T-3425 windows-latest advisory flag was removed under "
            "T-3512 (2026-09-13, CI run 34758499278) -- it must not be "
            "reintroduced without a ticket; see "
            "docs/design/windows-portability.md"
        )

    def test_matrix_still_includes_all_three_platforms(self) -> None:
        """MUST-STAY-QUIET companion: the advisory flag must not have been
        achieved by dropping windows-latest from the matrix instead --
        the job must still run (and report) on all three platforms."""
        doc = _load(_CI_WORKFLOW)
        matrix_os = doc["jobs"]["build"]["strategy"]["matrix"]["os"]
        assert set(matrix_os) == {"ubuntu-latest", "windows-latest", "macos-latest"}

    # frob:ticket T-3756
    def test_no_step_level_continue_on_error_smuggled_onto_other_legs(self) -> None:
        """MUST-STAY-QUIET: no individual step in the build job may carry
        its own unconditional continue-on-error, with ONE sanctioned
        exception -- T-3756's coverage-stamp step (T-1366), which is a
        separate, non-blocking best-effort MEASUREMENT step, not the
        pass/fail gate (that stays the ubuntu Test step's coverage-free
        `pytest -q`, unaffected by this exception). Now that the job-level
        windows-only advisory flag is gone (T-3512), no step-level
        continue-on-error may exist at all outside that one sanctioned
        exception."""
        doc = _load(_CI_WORKFLOW)
        sanctioned = "coverage stamp + delta baseline must be freshly measurable and clean (T-1366)"
        for step in doc["jobs"]["build"].get("steps", []):
            if step.get("name") == sanctioned:
                continue
            assert "continue-on-error" not in step, (
                f"unexpected step-level continue-on-error on step "
                f"{step.get('name', '<unnamed>')!r} -- windows-latest is "
                f"a normal blocking leg again (T-3512); only the "
                f"T-3756-sanctioned coverage step may carry this"
            )


class TestCiUbuntuTestBudgetRaised:
    """T-3426: run 33277131782 proved the ubuntu Test step's 25m budget was
    too tight for a PASSING run (99% at ~20m, killed at 25m mid-self-scan-
    test, not blocked on a lock). The step budget must be raised to at
    least 40m and the job-level ceiling must stay strictly above it, so
    the step's own stack-dump-on-hang fires first on a genuine hang.

    T-3482: the same class of miss recurred on macOS (run 33308245923,
    killed at [67%], not hung, on a suite grown to 12816 tests) while
    ubuntu's own T-3426 raise stayed correct -- the two platforms had
    drifted apart. macOS's budget is now raised to the same 40m floor,
    plus an explicit cross-platform parity assertion below, so one
    platform's budget can never silently regress below the other's
    again."""

    # frob:ticket T-3756
    def test_ubuntu_test_step_budget_at_least_40_minutes(self) -> None:
        """MUST-FIRE: the ubuntu Test step's `timeout -s ABRT <N>m` budget
        must be >= 40m. T-3756 (revert of T-3748): ubuntu's Test step runs a
        coverage-free `pytest -q`, matching macOS's own intent, so its
        pass/fail gate is not coverage-sensitive."""
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"timeout -s ABRT (\d+)m uv run pytest -q",
            text,
        )
        assert match, (
            "expected ubuntu's `timeout -s ABRT <N>m uv run pytest -q` step (T-3756)"
        )
        assert int(match.group(1)) >= 40, (
            f"ubuntu Test step budget regressed below 40m: {match.group(0)!r}"
        )

    # frob:ticket T-3756
    def test_job_timeout_minutes_exceeds_ubuntu_step_budget(self) -> None:
        """MUST-FIRE: the job-level ceiling must remain strictly greater
        than the ubuntu step budget, so the step's own instrumented
        timeout (with a stack dump) fires before the bare job ceiling."""
        doc = _load(_CI_WORKFLOW)
        job_timeout = doc["jobs"]["build"]["timeout-minutes"]
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"timeout -s ABRT (\d+)m uv run pytest -q",
            text,
        )
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
        _assert_step_uses_faulthandler_and_marker("Test (ubuntu", "timeout -s ABRT")

    def test_macos_step_budget_at_least_40_minutes(self) -> None:
        """MUST-FIRE (T-3482): the macOS Test step's `budget=<N>` (seconds)
        watcher must be >= 2400 (40m) -- the same class of miss T-3426
        fixed for ubuntu, now closed for macOS too so the two platforms
        cannot drift apart again."""
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        match = re.search(r"budget=(\d+)\s", text)
        assert match, "expected macOS's `budget=<N>` watcher assignment"
        assert int(match.group(1)) >= 2400, (
            f"macOS Test step budget regressed below 2400s (40m): {match.group(0)!r}"
        )

    def test_job_timeout_minutes_exceeds_macos_step_budget(self) -> None:
        """MUST-FIRE: the job-level ceiling must remain strictly greater
        than the macOS step budget (in minutes), so the step's own
        instrumented SIGABRT-then-KILL watcher fires before the bare job
        ceiling."""
        doc = _load(_CI_WORKFLOW)
        job_timeout = doc["jobs"]["build"]["timeout-minutes"]
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        match = re.search(r"budget=(\d+)\s", text)
        assert match
        step_budget_minutes = int(match.group(1)) / 60
        assert job_timeout > step_budget_minutes, (
            f"job timeout-minutes ({job_timeout}) must exceed the macOS "
            f"step budget ({step_budget_minutes}m)"
        )

    def test_macos_step_still_uses_faulthandler_and_sigabrt(self) -> None:
        """MUST-STAY-QUIET: the budget raise must not have dropped the
        stack-dump-on-hang mechanism (PYTHONFAULTHANDLER=1 + `kill -ABRT`,
        macOS's SIGABRT-capable equivalent of ubuntu's `timeout -s ABRT`)."""
        _assert_step_uses_faulthandler_and_marker("Test (macos", "kill -ABRT")

    # frob:ticket T-3756
    def test_macos_and_ubuntu_step_budgets_match(self) -> None:
        """MUST-FIRE: guard against a Test-step budget silently regressing.

        T-3482 originally required the two platforms' budgets to be EQUAL
        (40m each). T-3748 temporarily broke that equality by making ubuntu
        run the suite once under coverage; T-3756 reverted that (ubuntu's
        pass/fail gate must be coverage-free like macOS's, see the Test
        step's own comment), so both platforms are back to running a bare
        `pytest -q` and the original equal-budgets invariant holds again."""
        text = _CI_WORKFLOW.read_text(encoding="utf-8")
        ubuntu_match = re.search(
            r"timeout -s ABRT (\d+)m uv run pytest -q",
            text,
        )
        macos_match = re.search(r"budget=(\d+)\s", text)
        assert ubuntu_match and macos_match
        ubuntu_minutes = int(ubuntu_match.group(1))
        macos_minutes = int(macos_match.group(1)) / 60
        assert macos_minutes >= 40, f"macOS budget below 40m floor: {macos_minutes}m"
        assert ubuntu_minutes >= 40, f"ubuntu budget below 40m floor: {ubuntu_minutes}m"
        assert ubuntu_minutes == macos_minutes, (
            f"ubuntu Test step budget ({ubuntu_minutes}m) and macOS's "
            f"({macos_minutes}m) must match now that both run a bare "
            f"`pytest -q` (T-3756)"
        )


# frob:ticket T-4464
class TestManylinuxPinAndWindowsSmoke:
    """T-4464: release run 34769124533 failed the import smoke on
    manylinux-x86_64/aarch64 (undefined symbol: le16toh -- tree-sitter
    0.25.10's build.rs compiles with -std=c11 -D_DEFAULT_SOURCE, and
    manylinux2014's glibc 2.17 predates _DEFAULT_SOURCE as a feature-test
    macro) and on windows-x86_64 (the smoke step hardcoded the POSIX
    bin/python venv layout, so uv found no interpreter)."""

    def test_manylinux_targets_pin_2_28(self) -> None:
        """MUST-FIRE: both Linux matrix entries must pin manylinux: 2_28,
        not 'auto' (manylinux2014/glibc 2.17, where the endian macros
        stay hidden and le16toh is unresolved at import time)."""
        doc = _load(_RELEASE_WORKFLOW)
        matrix = doc["jobs"]["build"]["strategy"]["matrix"]["include"]
        linux_entries = {
            entry["target"]: entry
            for entry in matrix
            if entry["target"].startswith("manylinux-")
        }
        assert set(linux_entries) == {"manylinux-x86_64", "manylinux-aarch64"}
        for target, entry in linux_entries.items():
            assert entry["manylinux"] == "2_28", (
                f"{target} must pin manylinux: 2_28 (glibc 2.28, which "
                f"defines the _DEFAULT_SOURCE endian macros tree-sitter "
                f"0.25.10 needs) -- got {entry['manylinux']!r}"
            )

    def test_manylinux_pin_reason_is_documented(self) -> None:
        """MUST-FIRE: the glibc/_DEFAULT_SOURCE reasoning must be recorded
        as a comment directly in the workflow, not only in the ticket."""
        text = _RELEASE_WORKFLOW.read_text(encoding="utf-8")
        assert "le16toh" in text
        assert "_DEFAULT_SOURCE" in text
        assert "2.28" in text or "2_28" in text

    def test_smoke_step_is_os_aware(self) -> None:
        """MUST-FIRE: the import smoke step must branch on RUNNER_OS and
        use Scripts/python.exe on Windows rather than hardcoding the
        POSIX bin/python layout, and must place the venv under
        $RUNNER_TEMP rather than a hardcoded /tmp path."""
        doc = _load(_RELEASE_WORKFLOW)
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "Install the just-built wheels into a clean venv"
        )
        run = step["run"]
        assert "RUNNER_OS" in run, (
            "smoke step must branch on RUNNER_OS to pick the "
            "per-platform interpreter path"
        )
        assert "Scripts/python.exe" in run, (
            "smoke step must use Scripts/python.exe on Windows"
        )
        assert "RUNNER_TEMP" in run, (
            "smoke step must place the venv under $RUNNER_TEMP, "
            "not a hardcoded POSIX /tmp path"
        )
        assert "/tmp/native-check-venv" not in run, (
            "smoke step must not hardcode a POSIX /tmp venv path"
        )


# frob:ticket T-4470
class TestNoRetiredRunnerImages:
    """T-4470: run 34769124533 queued 4h18m against a `build` matrix
    entry pinned to macos-13 -- GitHub retired that hosted image, so the
    job never got scheduled, and because release.yml's concurrency
    group has `cancel-in-progress: false`, every later dispatch queued
    behind the stuck one forever. Guards against this whole class of
    retired-image regression, not just the one label that bit us."""

    # GitHub's own retirement notices, as of this ticket's fix.
    _RETIRED_IMAGES = frozenset(
        {"macos-13", "macos-12", "ubuntu-20.04", "windows-2019"}
    )

    def _all_os_labels(self, doc: dict) -> set[str]:
        """Every `os:`/`runs-on:` value reachable in release.yml, both
        matrix entries and plain job-level `runs-on:` strings."""
        labels: set[str] = set()
        for job in doc["jobs"].values():
            matrix = job.get("strategy", {}).get("matrix", {})
            for entry in matrix.get("include", []):
                if "os" in entry:
                    labels.add(entry["os"])
            runs_on = job.get("runs-on")
            if isinstance(runs_on, str) and "matrix.os" not in runs_on:
                labels.add(runs_on)
        return labels

    def test_no_matrix_entry_uses_a_retired_image(self) -> None:
        """MUST-FIRE: no `os:` in any matrix `include` entry, and no
        plain `runs-on:` string, names a hosted image GitHub has
        retired."""
        doc = _load(_RELEASE_WORKFLOW)
        labels = self._all_os_labels(doc)
        retired_in_use = labels & self._RETIRED_IMAGES
        assert not retired_in_use, (
            f"release.yml pins a retired hosted image: {retired_in_use!r} "
            f"-- it will never schedule a runner and, under this "
            f"workflow's cancel-in-progress: false concurrency group, "
            f"will block every later dispatch (T-4470)"
        )

    def test_build_and_artifact_smoke_jobs_have_timeout_minutes(self) -> None:
        """MUST-FIRE: `build` and `artifact-smoke` are both matrix jobs
        whose `os:` labels can drift to an unschedulable image again --
        each must declare `timeout-minutes` so that failure mode fails
        the job instead of holding the release concurrency group open
        indefinitely."""
        doc = _load(_RELEASE_WORKFLOW)
        for name in ("build", "artifact-smoke"):
            job = doc["jobs"][name]
            assert "timeout-minutes" in job, (
                f"jobs.{name} must declare timeout-minutes (T-4470)"
            )
            assert isinstance(job["timeout-minutes"], int)
            assert job["timeout-minutes"] > 0


# frob:ticket T-4470
class TestCrossBuiltTargetsSkipImportSmoke:
    """Coordinator addendum to T-4470 (run 34781548188): manylinux-aarch64
    is cross-built via QEMU/the manylinux container on an x86_64
    ubuntu-latest host, so `build`'s import-smoke step failed installing
    the aarch64 wheel into the x86_64 host venv ("Failed to determine
    installation plan") -- the identical architecture-mismatch class as
    macos-x86_64 cross-built on arm64 macos-latest. Both are marked
    `cross: true` in `build`'s matrix and the import-smoke step branches
    on that field, not a hardcoded target name."""

    _EXPECTED_CROSS_TARGETS = frozenset({"manylinux-aarch64", "macos-x86_64"})

    def _build_matrix(self, doc: dict) -> list[dict]:
        return doc["jobs"]["build"]["strategy"]["matrix"]["include"]

    def test_expected_targets_are_marked_cross(self) -> None:
        """MUST-FIRE: exactly the known cross-built targets carry
        `cross: true` -- a target silently missing the flag would fall
        through to a real import call and fail for an architecture
        reason that looks like a genuine defect."""
        doc = _load(_RELEASE_WORKFLOW)
        cross_targets = {
            entry["target"]
            for entry in self._build_matrix(doc)
            if entry.get("cross") is True
        }
        assert cross_targets == self._EXPECTED_CROSS_TARGETS

    def test_native_targets_are_not_marked_cross(self) -> None:
        """The three native (host-architecture-matching) targets must
        NOT carry `cross: true` -- they still get a real import smoke."""
        doc = _load(_RELEASE_WORKFLOW)
        for entry in self._build_matrix(doc):
            if entry["target"] not in self._EXPECTED_CROSS_TARGETS:
                assert entry.get("cross") is not True, (
                    f"{entry['target']} is native but marked cross: true"
                )

    def test_import_smoke_step_branches_on_matrix_cross(self) -> None:
        """MUST-FIRE: the import-smoke step must key its skip on
        `matrix.cross`, not a hardcoded single target name -- a
        hardcoded check would silently miss the next cross-built target
        added to the matrix."""
        doc = _load(_RELEASE_WORKFLOW)
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "Install the just-built wheels into a clean venv"
        )
        run = step["run"]
        assert "matrix.cross" in run, (
            "import-smoke step must branch on matrix.cross, not a hardcoded target name"
        )
        assert "matrix.target }} = 'macos-x86_64'" not in run.replace('"', "'"), (
            "import-smoke step must not hardcode a single cross target"
        )

    # frob:ticket T-4472
    def test_install_only_runs_inside_the_non_cross_branch(self) -> None:
        """Asserts `uv pip install` (and the venv creation feeding it)
        appears only inside the `else` (non-cross) arm of the `if
        matrix.cross` block, never before the `if` and never inside the
        cross arm, so a foreign-arch wheel install cannot run
        unconditionally ahead of the skip branch. See T-4472 for the
        design rationale."""
        doc = _load(_RELEASE_WORKFLOW)
        step = _find_step_by_name_prefix(
            doc["jobs"]["build"], "Install the just-built wheels into a clean venv"
        )
        run = step["run"]
        # Strip full-line comments so a comment MENTIONING "uv pip
        # install" (as this very test's own explanatory comment in the
        # workflow does) does not get counted as the real command.
        lines = [line for line in run.splitlines() if not line.strip().startswith("#")]

        if_idx = next(i for i, line in enumerate(lines) if "matrix.cross" in line)
        else_idx = next(
            i for i, line in enumerate(lines) if i > if_idx and line.strip() == "else"
        )
        # The non-cross arm nests its own if/fi (RUNNER_OS), so find the
        # matching OUTER `fi` by depth-tracking, not the first `fi` seen.
        depth = 0
        fi_idx = None
        for i in range(else_idx + 1, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("if "):
                depth += 1
            elif stripped == "fi":
                if depth == 0:
                    fi_idx = i
                    break
                depth -= 1
        assert fi_idx is not None, "could not find the outer fi closing the else arm"

        before_if = "\n".join(lines[:if_idx])
        cross_arm = "\n".join(lines[if_idx : else_idx + 1])
        non_cross_arm = "\n".join(lines[else_idx : fi_idx + 1])

        assert "uv pip install" not in before_if, (
            "uv pip install must not run before the matrix.cross branch"
        )
        assert "uv pip install" not in cross_arm, (
            "uv pip install must not run in the cross (skip) arm"
        )
        assert "uv pip install" in non_cross_arm, (
            "uv pip install must run inside the non-cross (native) arm"
        )
        assert "uv venv" not in before_if, (
            "the venv used for install must not be created before the "
            "matrix.cross branch"
        )
        assert "uv venv" in non_cross_arm, (
            "the venv must be created inside the non-cross (native) arm"
        )


# frob:ticket T-4476
class TestArtifactSmokeAarch64UsesNativeArmRunner:
    """Asserts `artifact-smoke`'s manylinux-aarch64 leg runs on GitHub's
    hosted native arm64 Linux image (`ubuntu-24.04-arm`, free for public
    repos), rather than ubuntu-latest (x86_64) installing the aarch64
    wheel into a mismatched host venv, keeping the smoke test real
    instead of falling back to the PLATFORM001 wheel-existence-only
    boundary. See T-4476/T-4470 for the design rationale."""

    def test_manylinux_aarch64_smoke_runs_on_a_native_arm_image(self) -> None:
        """MUST-FIRE: `artifact-smoke`'s manylinux-aarch64 entry must
        run on an arm64 hosted image, not ubuntu-latest (x86_64) -- a
        regression back to ubuntu-latest reproduces run 34799974130's
        failure exactly."""
        doc = _load(_RELEASE_WORKFLOW)
        entries = {
            entry["target"]: entry
            for entry in doc["jobs"]["artifact-smoke"]["strategy"]["matrix"]["include"]
        }
        assert "manylinux-aarch64" in entries, (
            "manylinux-aarch64 must still be covered by artifact-smoke "
            "(T-4476 keeps the smoke real via a native arm runner, "
            "unlike T-4470's macos-x86_64 drop)"
        )
        os_label = entries["manylinux-aarch64"]["os"]
        assert os_label != "ubuntu-latest", (
            "manylinux-aarch64's artifact-smoke leg must not run on "
            "ubuntu-latest (x86_64) -- it cannot install the aarch64 "
            "wheel there (T-4476, run 34799974130)"
        )
        assert "arm" in os_label, (
            f"manylinux-aarch64's artifact-smoke os ({os_label!r}) must "
            f"be an arm64 hosted image"
        )

    def test_manylinux_aarch64_not_in_smoke_exempt_targets(self) -> None:
        """manylinux-aarch64 gets a real native runner, not the
        PLATFORM001 documented-boundary drop macos-x86_64 uses -- it
        must NOT be added to `TestCiStatusGate._SMOKE_EXEMPT_TARGETS`."""
        assert "manylinux-aarch64" not in TestCiStatusGate._SMOKE_EXEMPT_TARGETS
