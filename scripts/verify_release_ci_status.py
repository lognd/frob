"""Fail-closed CI-status gate for `release.yml`'s `upload` job (T-3251).

WHY THIS EXISTS. `.github/workflows/release.yml` is manually dispatched
(T-3011) and its `upload` job is gated by a required-reviewer GitHub
Environment plus `needs: [build, build-sdists]` -- but neither of those
proves the test suite passed, `frob check` was clean, or the CI matrix
was green on the commit being released. A human could dispatch a release
from a red main and every existing gate would say yes. A PyPI upload is
irreversible (a version number cannot be reused, even after a yank), so
this is the one place in the repo where "a failed measurement reported
as a successful one" -- this repo's own dominant defect class -- cannot
be fixed by a follow-up commit.

This script is the `release.yml` step that stands between `build`/
`build-sdists` finishing and `upload` starting: it resolves `ci.yml`'s
conclusion for THE EXACT COMMIT SHA being released (never a branch name,
never "the most recent run" on any commit), and distinguishes three
outcomes -- GREEN, RED, UNDETERMINED -- printing exactly one of those
words so the run's own log is unambiguous. UNDETERMINED (API error, no
matching run, a run still in progress) is refused exactly like RED: an
unreadable status is never read as green.

An explicit, auditable override exists (`override`, `override_reason`)
for a deliberate release from a known-red main -- never the default,
and refused outright if a reason is not given, so the run's own log
records who (`github.actor`, already on every workflow run) and why.

A plain module-level function returning a pydantic model (`CiStatusResult`)
rather than the script's own `main()` doing everything inline -- this
repo's own convention (CLAUDE.md: "PREFER pydantic and typani") and the
same shape `scripts/branch_stranded_work_analysis.py`'s `BranchResult`
already uses, kept fully unit-testable via `_load_script` (tests/unit/
conftest.py) without a real `gh` binary or network access.

Usage (from a `release.yml` step):
    python3 scripts/verify_release_ci_status.py \\
        --repo "$GITHUB_REPOSITORY" --sha "$GITHUB_SHA" \\
        --override "$OVERRIDE_RED_CI" --override-reason "$OVERRIDE_REASON"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable

from pydantic import BaseModel

#: The three, and only three, outcomes this gate can report -- never a
#: fourth "unknown" spelling and never collapsing UNDETERMINED into RED
#: or GREEN anywhere in this module.
_STATUSES = ("green", "red", "undetermined")


# frob:doc docs/guides/release.md#verify-ci-status
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_green_on_success_conclusion kind="unit"  # noqa: E501
class CiStatusResult(BaseModel):
    """One CI-status determination for a single commit SHA: `status` is
    exactly one of `"green"`, `"red"`, `"undetermined"` (`_STATUSES`);
    `detail` is the human-facing reason, always populated (never a bare
    status with no explanation of what was checked or why it failed)."""

    model_config = {}

    status: str
    detail: str

    # frob:doc docs/guides/release.md#verify-ci-status
    # frob:tests tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant.test_valid_status_literal_constructs kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant.test_invalid_status_literal_raises kind="unit"  # noqa: E501
    def model_post_init(self, __context: object) -> None:
        """Guard against a typo'd status literal slipping past review --
        this is an internal invariant, not user input, so an assertion
        (not a typani Result) is the right failure mode."""
        assert self.status in _STATUSES, (
            f"invalid CiStatusResult.status: {self.status!r}"
        )


#: `(argv) -> (returncode, stdout, stderr)` -- the one seam every `gh`
#: call in this module goes through, so tests substitute a fake without
#: a real `gh` binary or network access (mirrors `scripts/branch_
#: stranded_work_analysis.py::_run`'s identical shape for `git`).
_GhRunner = Callable[[tuple[str, ...]], tuple[int, str, str]]


# frob:tests tests/unit/test_verify_release_ci_status.py::TestRunGh.test_spawn_failure_reports_as_nonzero_with_stderr kind="unit"  # noqa: E501
def _run_gh(argv: tuple[str, ...]) -> tuple[int, str, str]:
    """Run a `gh` CLI subprocess, returning `(returncode, stdout, stderr)`
    -- never raises; a spawn failure (missing binary, timeout) reports as
    `(1, "", str(exc))` so callers have one failure shape to branch on,
    matching `ghio.py`'s own established `gh` invocation convention."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


# frob:doc docs/guides/release.md#verify-ci-status
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_green_on_success_conclusion kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_red_on_failure_conclusion kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_api_error kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_no_matching_run kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_unparseable_json kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_run_still_in_progress kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_resolves_by_exact_sha_not_branch_or_latest kind="unit"  # noqa: E501
def determine_ci_status(
    repo: str,
    sha: str,
    *,
    workflow: str = "ci.yml",
    run_gh: _GhRunner = _run_gh,
) -> CiStatusResult:
    """Resolve `workflow`'s (default `ci.yml`) most recent conclusion for
    THE EXACT COMMIT `sha` in `repo` (`owner/name`) -- queries GitHub's
    `workflow runs` REST API filtered by `head_sha=<sha>`, never by
    branch name and never "the latest run" unfiltered, so a run on a
    different commit passing can never be read as this commit passing.

    FAILS CLOSED at every step: a `gh api` non-zero exit, unparseable
    JSON, zero matching runs, or a matching run whose `status` is not yet
    `"completed"` are all `"undetermined"` -- never silently treated as
    green. Only a completed run whose `conclusion` is exactly `"success"`
    returns `"green"`; any other completed conclusion (`"failure"`,
    `"cancelled"`, `"timed_out"`, ...) is `"red"`."""
    returncode, stdout, stderr = run_gh(
        (
            "gh",
            "api",
            f"repos/{repo}/actions/workflows/{workflow}/runs"
            f"?head_sha={sha}&per_page=10",
        )
    )
    if returncode != 0:
        return CiStatusResult(
            status="undetermined",
            detail=(
                f"gh api call to list {workflow} runs for commit {sha} "
                f"failed (exit={returncode}): {stderr.strip() or '<no stderr>'}"
            ),
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return CiStatusResult(
            status="undetermined",
            detail=f"gh api returned unparseable JSON for commit {sha}: {exc}",
        )
    runs = payload.get("workflow_runs") or []
    if not runs:
        return CiStatusResult(
            status="undetermined",
            detail=(
                f"no {workflow} run found for commit {sha} -- this exact "
                f"commit may never have been pushed through CI"
            ),
        )
    # GitHub's `runs?head_sha=` response is already newest-first; the
    # first entry is the most recent run for this exact SHA.
    run = runs[0]
    run_status = run.get("status")
    if run_status != "completed":
        return CiStatusResult(
            status="undetermined",
            detail=(
                f"latest {workflow} run for commit {sha} has status "
                f"{run_status!r}, not 'completed' yet"
            ),
        )
    conclusion = run.get("conclusion")
    if conclusion == "success":
        return CiStatusResult(
            status="green",
            detail=f"{workflow} run {run.get('id')} for commit {sha} concluded success",
        )
    return CiStatusResult(
        status="red",
        detail=(
            f"{workflow} run {run.get('id')} for commit {sha} concluded "
            f"{conclusion!r}, not success"
        ),
    )


# frob:doc docs/guides/release.md#verify-ci-status
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_green_always_proceeds kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_red_without_override_refuses kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_undetermined_without_override_refuses kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_red_with_override_and_reason_proceeds kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_override_without_reason_is_refused_even_when_requested kind="unit"  # noqa: E501
def decide(
    result: CiStatusResult, *, override: bool, override_reason: str
) -> tuple[int, str]:
    """Turn one `CiStatusResult` plus the operator's override request into
    `(exit_code, message)` -- `exit_code=0` means the calling workflow
    step proceeds (to `upload`'s own separate, unweakened T-3011 consent
    gate), `exit_code=1` means it refuses.

    GREEN always proceeds (exit 0), override or not -- there is nothing
    to override when CI is already green. RED/UNDETERMINED refuse
    (exit 1) UNLESS `override=True` AND `override_reason` is a non-empty,
    non-whitespace string -- an override request with no reason is
    refused exactly like no override at all, so a deliberate red-main
    release can never be silent about why. The refusal/override message
    always names the status explicitly (never a bare "failed")."""
    if result.status == "green":
        return 0, f"CI status GREEN -- proceeding. {result.detail}"
    if override and override_reason.strip():
        return (
            0,
            f"CI status {result.status.upper()} -- OVERRIDDEN by explicit operator "
            f"request. {result.detail} override_reason={override_reason!r}",
        )
    if override and not override_reason.strip():
        return (
            1,
            f"CI status {result.status.upper()} -- override was requested but no "
            f"override_reason was given; refusing. {result.detail}",
        )
    return (
        1,
        f"CI status {result.status.upper()} -- refusing to release. {result.detail}",
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """CLI surface for the `release.yml` step: `--repo owner/name --sha
    <full-sha> [--workflow ci.yml] [--override true|false] [--override-
    reason TEXT]` -- deliberately explicit args rather than reading
    `GITHUB_REPOSITORY`/`GITHUB_SHA` directly inside testable functions,
    matching `determine_ci_status`/`decide`'s own env-free signatures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--sha", required=True, help="the exact commit SHA to check")
    parser.add_argument("--workflow", default="ci.yml")
    parser.add_argument(
        "--override",
        default="false",
        help="'true' to explicitly override a non-green CI status (requires "
        "--override-reason)",
    )
    parser.add_argument("--override-reason", default="")
    return parser.parse_args(argv)


# frob:doc docs/guides/release.md#verify-ci-status
# frob:tests tests/unit/test_verify_release_ci_status.py::TestMain.test_green_path_prints_green_and_exits_zero kind="unit"  # noqa: E501
# frob:tests tests/unit/test_verify_release_ci_status.py::TestMain.test_red_path_without_override_exits_nonzero kind="unit"  # noqa: E501
def main(argv: list[str] | None = None) -> int:
    """Entry point: resolve CI status for `--sha`, decide, print the
    message, and return the exit code `release.yml`'s step should exit
    with (non-zero fails the step, which fails the job, which blocks
    `upload` via `needs:` -- no separate wiring required)."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    # `run_gh=_run_gh` explicit (not the default parameter binding) so a
    # test monkeypatching the MODULE-level `_run_gh` name reaches this
    # call -- a default arg is bound once at import time and would not
    # observe a later `monkeypatch.setattr(module, "_run_gh", ...)`.
    result = determine_ci_status(
        args.repo, args.sha, workflow=args.workflow, run_gh=_run_gh
    )
    override = args.override.strip().lower() in ("true", "1", "yes")
    exit_code, message = decide(
        result, override=override, override_reason=args.override_reason
    )
    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, same as \
    # scripts/branch_stranded_work_analysis.py's own identical bare-print waivers -- \
    # this runs as a release.yml step, not through frob's own gate-rendered output \
    # surface"
    print(message)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
