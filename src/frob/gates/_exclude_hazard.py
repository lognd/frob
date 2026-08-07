"""EXCL001: a `.git/info/exclude` entry that shadows tracked source
(docs/modules/gates.md#rule-catalog).

`.git/info/exclude` behaves like a personal, untracked `.gitignore`
(T-0465): unlike `.gitignore` (itself tracked, reviewable, and shared),
it lives under `.git/` -- the COMMON dir shared by every worktree of a
clone (`git rev-parse --git-common-dir`) -- so one entry silently
affects `git status`/`git add -A` in every worktree AND `main`, not just
the worktree that added it. A real incident: an agent added
`src/frob/render/` to `.git/info/exclude` to hide its own in-progress
untracked scratch files, but that pattern also matches every ALREADY-
TRACKED file under `src/frob/render/` for `git status`'s untracked-file
listing -- so brand-new files an agent adds under that same directory
later become invisible to `git add -A`/`git status`, and silently never
get committed. The hazard isn't that excluding a directory untracks
existing files (it does not); it's that a real, tracked source directory
now has a standing blind spot for anything NEW added under it.

Scope decision: this module reads `.git/info/exclude` directly (a
plain-text gitignore-format file) rather than going through
`frob.excludes` (that module's `[graph] exclude` is a DIFFERENT,
tracked, `frob.toml`-declared config -- the thing THIS gate exists to
say is the honest alternative to hiding work in `.git/info/exclude`).
"""

from __future__ import annotations

import re
from pathlib import Path

from frob import gitio
from frob.gates._models import Severity, Violation
from frob.gates._tracked_files import tracked_files as _shared_tracked_files
from frob.logging import get_logger

_log = get_logger(__name__)

# Comment lines and blank lines are not patterns; git's gitignore-format
# rules apply (trailing `/` means "directory", `#` starts a comment,
# leading `!` negates -- negation entries are never a hazard since they
# UN-hide something, so they are skipped here rather than flagged).
_COMMENT_RE = re.compile(r"^\s*#")


def _git_common_dir(root: Path) -> Path | None:
    """The shared `.git` common dir for `root` (same dir across every
    worktree of one clone), or `None` if `root` is not a git checkout at
    all -- degrade-don't-crash, mirroring `frob.gitio`'s posture.

    Thin wrapper (T-0784) over the single canonical `frob.gitio.
    git_common_dir` -- this gate used to spawn and parse its own
    `rev-parse --git-common-dir` copy; delegating here means it also picks
    up that seam's process-lifetime memoization for free."""
    resolved = gitio.git_common_dir(root)
    if resolved.is_err:
        _log.debug(
            "exclude_hazard: git-common-dir lookup failed: %s", resolved.danger_err
        )
        return None
    return resolved.danger_ok


def _exclude_entries(exclude_path: Path) -> tuple[str, ...]:
    """Non-comment, non-blank, non-negated patterns from a gitignore-format
    file; `()` if the file does not exist or cannot be read."""
    try:
        text = exclude_path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.debug("exclude_hazard: could not read %s: %s", exclude_path, exc)
        return ()
    entries: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or _COMMENT_RE.match(line) or line.startswith("!"):
            continue
        entries.append(line)
    return tuple(entries)


def _pattern_prefix(pattern: str) -> str:
    """The literal directory/file prefix a gitignore pattern names, for a
    tracked-path prefix match: strips a leading `/` (repo-root anchor) and
    a trailing `/` or `/**`/`/*` (directory-contents wildcard) -- this
    gate only needs to know WHICH directory/file a pattern targets, not
    full gitignore glob semantics."""
    prefix = pattern.lstrip("/")
    for suffix in ("/**", "/*"):
        if prefix.endswith(suffix):
            prefix = prefix[: -len(suffix)]
            break
    return prefix.rstrip("/")


def _shadows_tracked_path(prefix: str, tracked: tuple[str, ...]) -> bool:
    """True if `prefix` names an exact tracked file, or a directory prefix
    under which at least one tracked file lives -- either shape means the
    exclude entry has real, git-tracked source to shadow, not merely a
    generated/vendored/never-tracked directory."""
    if not prefix:
        return False
    if prefix in tracked:
        return True
    dir_prefix = prefix + "/"
    return any(t.startswith(dir_prefix) for t in tracked)


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_gates.py::TestExcludeHazardGate.test_entry_shadowing_tracked_dir_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestExcludeHazardGate.test_entry_matching_no_tracked_path_is_silent  # noqa: E501
# frob:enforces CHK-GATE-EXCL001
def exclude_hazard_gate(root: Path) -> tuple[Violation, ...]:
    """EXCL001: every `.git/info/exclude` entry that shadows a tracked file
    or a directory containing tracked files.

    Reads the SHARED common-dir `info/exclude` (T-0465: this file is not
    per-worktree, so a hazard here affects every worktree and `main`),
    not any worktree-local path. A repo doctor's remediation reads the
    same file; this gate is the static, `frob check`-time half.
    """
    common_dir = _git_common_dir(root)
    if common_dir is None:
        return ()
    exclude_path = common_dir / "info" / "exclude"
    entries = _exclude_entries(exclude_path)
    if not entries:
        return ()
    tracked = _shared_tracked_files(root, caller="exclude_hazard")
    if not tracked:
        return ()
    violations: list[Violation] = []
    for pattern in entries:
        prefix = _pattern_prefix(pattern)
        if not _shadows_tracked_path(prefix, tracked):
            continue
        violations.append(
            Violation(
                rule="EXCL001",
                severity=Severity.ERROR,
                file=str(exclude_path),
                line=0,
                message=(
                    f"EXCL001: .git/info/exclude entry {pattern!r} shadows "
                    f"tracked source under {prefix!r} -- this file is "
                    f"SHARED across every worktree of this clone (and "
                    f"main), so new files added under {prefix!r} later "
                    f"become invisible to `git status`/`git add -A` "
                    f"everywhere and silently never get committed; remove "
                    f"the entry (or narrow it to a genuinely untracked "
                    f"path) rather than using it to hide work-in-progress"
                ),
            )
        )
    return tuple(violations)


__all__ = ["exclude_hazard_gate"]
