"""`frob release publish` (T-2242): compose bump+stamp+sync+commit+push+
build+publish into one verb, replacing Makefile's `upload:` bash recipe
(`set -a && . ./.env && set +a`, `uv run python scripts/bump_version.py`,
`frob release stamp`/`sync`, a hand-rolled `git add`/`commit`/`push`, then
`uv build && uv publish`).

Every subprocess call is an argv list (`frob.gitio.run_argv`, never
`shell=True`, never `bash -c`) so this runs identically on Windows. `.env`
is loaded via `python-dotenv`'s `load_dotenv()` at the top of a REAL
(non-dry-run) publish only -- never read/echoed/logged by this module,
and a `--dry-run` call never touches `.env` at all since it never needs a
token it will never use.

`--dry-run` is the acceptance-provable path (T-2242's own mandatory
route): it computes and returns the exact `PublishPlan` -- the version
this would bump to, the files it would commit -- WITHOUT writing
`pyproject.toml`, without a git commit, without a push, without a build,
and without a publish. `publish(root, snapshot, dry_run=True)` is
side-effect-free start to finish; this is proven by test
(`tests/test_release.py::TestPublish::test_dry_run_does_not_mutate_
anything`), not just by inspection."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.release import (
    ReleaseError,
    bump_patch_version,
    changelog_skeleton_entry,
    current_version,
    next_patch_version,
    rewrite_pyproject_version,
    stamp,
)

_log = get_logger(__name__)

#: The files `upload:`'s old recipe staged before committing a version
#: bump -- unchanged by this migration.
_COMMIT_FILES = ("pyproject.toml", "uv.lock", "CHANGELOG.md", ".frob-release.json")


# frob:doc docs/modules/release.md#frob-release-publish-t-2242
# frob:tests \
# tests/test_release.py::TestPublish.test_dry_run_does_not_mutate_anything  # noqa: E501
class PublishPlan(BaseModel):
    """The publish sequence's plan (T-2242): the version it would bump to
    and the files it would touch/push/publish. Computed identically
    whether or not the caller actually executes it -- `--dry-run` reports
    exactly this and nothing else."""

    model_config = {}

    current_version: str
    new_version: str
    files_to_commit: tuple[str, ...] = _COMMIT_FILES
    would_push: bool = True
    would_build: bool = True
    would_publish: bool = True


# frob:doc docs/modules/release.md#frob-release-publish-t-2242
# frob:tests \
# tests/test_release.py::TestPublish.test_real_run_composes_every_step_in_order  # noqa: E501
class PublishReport(BaseModel):
    """One `publish()` call's outcome: the plan it computed, whether it
    was a dry run, and (for a real run) which steps actually executed, in
    order -- empty for a dry run, since nothing executed."""

    model_config = {}

    plan: PublishPlan
    dry_run: bool
    executed_steps: tuple[str, ...] = ()


def _compute_plan(root: Path) -> Result[PublishPlan, ReleaseError]:
    """The plan `publish()` reports (and, for a real run, then acts on) --
    read-only: reads `pyproject.toml`'s current version and computes the
    next patch version, never writes anything."""
    current = current_version(root)
    if current.is_err:
        return Err(current.danger_err)
    nxt = next_patch_version(current.danger_ok)
    if nxt.is_err:
        return Err(nxt.danger_err)
    return Ok(PublishPlan(current_version=current.danger_ok, new_version=nxt.danger_ok))


def _sync_derived_artifacts(root: Path, version: str) -> Result[None, ReleaseError]:
    """The `frob release sync` steps `publish` needs inline (T-1009's
    `rewrite_pyproject_version`/`changelog_skeleton_entry`, plus `uv
    lock`) -- reused directly rather than shelling out to `frob release
    sync` as a nested subprocess, so a real failure surfaces as this
    module's own typed `Result` instead of a second process's exit code.
    `rewrite_pyproject_version` is a no-op here in practice (`bump_patch_
    version` already wrote the same `version`) but is called anyway for
    the same idempotent-by-construction posture `frob release sync`
    itself has."""
    from frob.gitio import run_argv

    rewritten = rewrite_pyproject_version(root, version)
    if rewritten.is_err:
        return Err(rewritten.danger_err)

    if (root / "pyproject.toml").exists():
        locked = run_argv(["uv", "lock"], cwd=root, timeout_s=120.0)
        if locked.is_err or locked.danger_ok.returncode != 0:
            _log.error(
                "release publish: uv lock failed -- %s",
                locked.danger_err if locked.is_err else locked.danger_ok.stderr,
            )
            return Err(ReleaseError.SyncFailed)

    changelog_skeleton_entry(root, version)
    return Ok(None)


def _run_step(
    argv: list[str], *, cwd: Path, on_fail: ReleaseError, timeout_s: float = 60.0
) -> Result[None, ReleaseError]:
    """Run one argv-list subprocess step (T-2242: never `shell=True`,
    never `bash -c`) and translate a spawn failure OR a nonzero exit into
    `on_fail` -- the one place every git/uv step in `publish` shares its
    error-translation shape."""
    from frob.gitio import run_argv

    ran = run_argv(argv, cwd=cwd, timeout_s=timeout_s)
    if ran.is_err:
        _log.error("release publish: %s failed to spawn: %s", argv, ran.danger_err)
        return Err(on_fail)
    if ran.danger_ok.returncode != 0:
        _log.error(
            "release publish: %s exited %d -- %s",
            argv,
            ran.danger_ok.returncode,
            ran.danger_ok.stderr,
        )
        return Err(on_fail)
    return Ok(None)


# frob:ticket T-2242
def _run_git_publish_steps(
    root: Path, plan: PublishPlan, new_version: str
) -> Result[tuple[str, ...], ReleaseError]:
    """The commit/push/build/publish tail of a real `publish()` run, split
    out to keep `publish` itself under ARCH001's line threshold -- bump
    and stamp/sync already ran by the time this is called. Returns the
    step names that ran, in order, up to and including `"uv-publish"`."""
    executed: list[str] = []

    added = _run_step(
        ["git", "add", *plan.files_to_commit],
        cwd=root,
        on_fail=ReleaseError.GitAddFailed,
    )
    if added.is_err:
        return Err(added.danger_err)
    executed.append("git-add")

    committed = _run_step(
        ["git", "commit", "-m", f"chore: bump version to {new_version}"],
        cwd=root,
        on_fail=ReleaseError.GitCommitFailed,
    )
    if committed.is_err:
        return Err(committed.danger_err)
    executed.append("git-commit")

    pushed = _run_step(["git", "push"], cwd=root, on_fail=ReleaseError.GitPushFailed)
    if pushed.is_err:
        return Err(pushed.danger_err)
    executed.append("git-push")

    built = _run_step(
        ["uv", "build"], cwd=root, on_fail=ReleaseError.BuildFailed, timeout_s=300.0
    )
    if built.is_err:
        return Err(built.danger_err)
    executed.append("uv-build")

    published = _run_step(
        ["uv", "publish"],
        cwd=root,
        on_fail=ReleaseError.PublishFailed,
        timeout_s=300.0,
    )
    if published.is_err:
        return Err(published.danger_err)
    executed.append("uv-publish")

    return Ok(tuple(executed))


# frob:doc docs/modules/release.md#frob-release-publish-t-2242
# frob:tests \
# tests/test_release.py::TestPublish.test_dry_run_does_not_mutate_anything  # noqa: E501
# frob:tests \
# tests/test_release.py::TestPublish.test_real_run_composes_every_step_in_order  # noqa: E501
# frob:tests tests/test_release.py::TestPublish.test_env_only_loaded_on_a_real_run  # noqa: E501
def publish(
    root: Path, snapshot, *, dry_run: bool
) -> Result[PublishReport, ReleaseError]:
    """`frob release publish` (T-2242): bump the patch version, stamp +
    sync the release, commit `pyproject.toml`/`uv.lock`/`CHANGELOG.md`/
    `.frob-release.json`, push, build, and publish -- the same net effect
    as the old `upload:` Makefile recipe, composed from this module's own
    typed functions plus argv-list subprocess steps (never a shell
    string). `dry_run=True` returns after computing the `PublishPlan`
    only -- no write, no `.env` load, no subprocess spawn of any kind."""
    plan_result = _compute_plan(root)
    if plan_result.is_err:
        return Err(plan_result.danger_err)
    plan = plan_result.danger_ok

    if dry_run:
        _log.info(
            "release publish --dry-run: would bump %s -> %s, commit %s, push, "
            "build, publish",
            plan.current_version,
            plan.new_version,
            ", ".join(plan.files_to_commit),
        )
        return Ok(PublishReport(plan=plan, dry_run=True))

    from dotenv import load_dotenv

    # T-2242 safety requirement: loaded via python-dotenv at runtime, never
    # read/echoed/logged by this module. A missing .env is not an error --
    # load_dotenv() is a no-op then, and the eventual `uv publish` step is
    # what actually needs a token to be present in the environment.
    load_dotenv(root / ".env")

    bumped = bump_patch_version(root)
    if bumped.is_err:
        return Err(bumped.danger_err)

    stamped = stamp(root, snapshot, bumped.danger_ok)
    if stamped.is_err:
        return Err(stamped.danger_err)

    synced = _sync_derived_artifacts(root, bumped.danger_ok)
    if synced.is_err:
        return Err(synced.danger_err)

    tail = _run_git_publish_steps(root, plan, bumped.danger_ok)
    if tail.is_err:
        return Err(tail.danger_err)

    executed = ("bump", "stamp", "sync", *tail.danger_ok)
    return Ok(PublishReport(plan=plan, dry_run=False, executed_steps=executed))


__all__ = ["PublishPlan", "PublishReport", "publish"]
