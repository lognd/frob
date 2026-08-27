"""Detects CLI-surface skew between the INVOKED `frob` binary and the repo
it is running inside, when a matching `--version` string cannot (T-3129).

The incident this closes: the globally `uv tool install`ed `frob` on PATH
and this repo's own `uv run frob` reported the IDENTICAL version string
(`frob 0.530.0`) while exposing DIFFERENT CLI surfaces (`refactor`,
`narrative`, `status`, `-v/--verbose`, `ticket unblock`, `refactor
move-module` all present in one, absent in the other) -- three tickets
were filed this session on the false premise that verbs the global binary
rejected did not exist at all. `frob.repo_meta.stale_install_warning`
already warns on a running-vs-declared VERSION mismatch, but a stale
build whose `pyproject.toml` version was never bumped past its last
release is invisible to that check by construction: the string matches,
the code does not. T-2884 already established the fix for this exact
shape one layer down (`frob.app._daemon_proxy._client_source_sha`,
daemon-vs-client skew) -- this module is the same content-sensitive
git-SHA fingerprint applied to the CLI entry point itself, not imported
from `_daemon_proxy` (that module is a sibling concern scoped to the
daemon proxy, per its own docstring's layering note) but duplicated in
the same shape deliberately, matching this repo's established precedent
for this exact kind of small, security-relevant duplication over a
speculative shared import.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import subprocess
from pathlib import Path

from frob.logging import get_logger
from frob.repo_meta import is_frob_own_repo

_log = get_logger(__name__)


# frob:ticket T-3129
def _git_head_sha(git_root: Path) -> str | None:
    """`git rev-parse HEAD` run inside `git_root`, or `None` on any failure
    (no git binary, not a git worktree, detached/corrupt HEAD, timeout) --
    callers MUST treat `None` as UNTRUSTED, never as a match against
    another `None` (T-2884's fail-safe-to-stale direction, reapplied
    here: an unresolvable sha is exactly the "cannot prove these are the
    same build" case this module exists to catch loudly, not wave
    through)."""
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "HEAD"],
            cwd=str(git_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.debug("_version_guard: git rev-parse failed for %s: %s", git_root, exc)
        return None
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha or None


# frob:ticket T-3129
def _running_frob_source_sha() -> tuple[Path | None, str | None]:
    """The git HEAD sha of whichever checkout the RUNNING `frob` package's
    own `__init__.py` resolves into, found by walking up from that file
    for a `.git` ancestor -- same walk as `_daemon_proxy._client_source_
    sha`, applied to the CLI process itself rather than a daemon. A
    globally `uv tool install`ed binary's site-packages copy has no
    `.git` ancestor at all (pip/uv build wheels do not ship one), so this
    resolves to `(None, None)` for exactly the stale-global-binary case
    T-3129 exists to catch -- an unresolvable running sha is later treated
    as a mismatch, never a trusted match, so that case is never silently
    waved through as equivalent to a genuine in-tree run."""
    spec = importlib.util.find_spec("frob")
    if spec is None or spec.origin is None:
        return None, None
    here = Path(spec.origin).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate, _git_head_sha(candidate)
    return None, None


# frob:ticket T-3129
def _fingerprint_mismatch_message(
    repo_root: Path,
    running_init: Path,
    running_root: Path | None,
    running_sha: str | None,
    repo_sha: str | None,
) -> str:
    """Renders `binary_fingerprint_warning`'s loud one-liner once a
    mismatch (or an unresolvable side) has already been decided -- split
    out purely to keep that function under ARCH001's line threshold, no
    behavior of its own beyond string assembly."""
    running_desc = (
        f"{running_sha} ({running_root})"
        if running_sha is not None
        else f"unresolvable ({running_init}, no .git ancestor found -- likely a "
        f"packaged wheel install, e.g. `uv tool install frob`)"
    )
    repo_desc = repo_sha if repo_sha is not None else "unresolvable"
    return (
        "frob: WARNING -- CLI-surface skew risk: the invoked frob binary's "
        f"source identity ({running_desc}) does not provably match "
        f"{repo_root}'s own git HEAD ({repo_desc}). `frob --version` alone "
        "cannot detect this (T-3129): version strings can match while the "
        "CLI surface and gate logic differ. Use 'uv run frob' (or 'make "
        "<target>') from inside this checkout, never the bare installed "
        "binary, for any command whose result matters."
    )


# frob:ticket T-3129
# frob:doc docs/modules/app.md#entry-point
# frob:tests tests/unit/test_version_guard.py::test_matching_sha_is_quiet
# frob:tests tests/unit/test_version_guard.py::test_mismatched_sha_warns_loudly
# frob:tests tests/unit/test_version_guard.py::test_unresolvable_running_sha_warns
# frob:tests tests/unit/test_version_guard.py::test_non_frob_repo_is_quiet
# frob:tests tests/unit/test_version_guard.py::test_editable_in_tree_run_is_quiet
def binary_fingerprint_warning(repo_root: Path) -> str | None:
    """A loud, one-line warning when the INVOKED `frob` binary's source
    content cannot be PROVEN identical to `repo_root`'s own checkout,
    even when `frob --version` reports the same string as `repo_root`'s
    declared version (T-3129) -- `frob.repo_meta.stale_install_warning`'s
    exact-version-string check is blind to this by construction: a stale
    global install built before the LAST version bump but after an
    UNRELATED source-only change (or a build from a stale tag that never
    got a fresh bump at all) reports a version string identical to a repo
    that has since moved on. This check never compares version strings at
    all -- only git content identity, T-2884's precedent for exactly this
    class of gap.

    `None` (no warning, the quiet case tests must cover) when: `repo_root`
    is not frob's own checkout (`is_frob_own_repo` is `False` -- this
    check only makes sense for frob's own repo, not an arbitrary consumer
    that happens to depend on the `frob` package), the running package's
    own `__init__.py` resolves to exactly `repo_root/src/frob/__init__.py`
    (an editable install / `uv run frob` from this same checkout -- the
    file identity check alone already proves it is not stale, no git
    spawn needed), or both sides' git HEAD sha resolve and are equal.

    Fires (a warning string, not `None`) when: either side's sha is
    unresolvable (fail-safe-to-stale, T-2884's direction: an
    indeterminate check warns rather than trusts), or both resolve and
    disagree. The message states the mechanism explicitly (git HEAD sha,
    not version) per T-3129's acceptance criteria, and names both the
    running binary's own path and the repo's expected sha so the operator
    can act without re-deriving anything."""
    if not is_frob_own_repo(repo_root):
        return None

    spec = importlib.util.find_spec("frob")
    if spec is None or spec.origin is None:
        return None
    running_init = Path(spec.origin).resolve()
    local_init = (repo_root / "src" / "frob" / "__init__.py").resolve()
    if running_init == local_init:
        return None

    running_root, running_sha = _running_frob_source_sha()
    repo_sha = _git_head_sha(repo_root)

    if running_sha is not None and repo_sha is not None and running_sha == repo_sha:
        return None

    return _fingerprint_mismatch_message(
        repo_root, running_init, running_root, running_sha, repo_sha
    )
