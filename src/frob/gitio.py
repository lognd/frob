"""The ONE git subprocess seam (docs/modules/testing.md), shared by testing and gates.

Every git invocation in frob goes through this module: `repo_root` (worktree-
correct root discovery), `working_diff` (merge-base-to-worktree unified diff,
including uncommitted and untracked changes), and `current_branch`. Two diff
implementations would desync (docs/modules/gates.md's old `gates/diff.py` design is
superseded by this module). `_run_git` is the private spawn primitive;
`run_argv` is the small public wrapper `frob.testing` reuses for its own
runner spawns so there is exactly one subprocess-with-timeout helper in the
package, never a second copy living under `frob.testing`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

_log = get_logger(__name__)

_EXCERPT_LINES = 40
_DEFAULT_TIMEOUT_S = 30.0


# frob:doc docs/modules/testing.md#error-types
class GitError(ErrorSet):
    """Failure values every `frob.gitio` function can return."""

    NotARepo = "Path is not inside a git repository or worktree"
    GitFailed = "git subprocess failed"


# frob:doc docs/modules/testing.md#data-models
class Hunk(BaseModel):
    """One contiguous new-file line range touched in `file`."""

    model_config = ConfigDict(frozen=True)

    file: str
    span: tuple[int, int]


# frob:doc docs/modules/testing.md#data-models
class Diff(BaseModel):
    """The working-tree delta against `base`'s merge-base sha."""

    model_config = ConfigDict(frozen=True)

    base: str
    hunks: tuple[Hunk, ...]


# frob:doc docs/modules/testing.md#data-models
class ProcResult(BaseModel):
    """One completed spawn's captured result (any returncode)."""

    model_config = ConfigDict(frozen=True)

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def _excerpt(text: str, *, lines: int = _EXCERPT_LINES) -> str:
    """Bound a stdout/stderr blob to its last N lines -- the useful end."""
    parts = text.splitlines()
    if len(parts) <= lines:
        return text
    return "\n".join(["...(truncated)...", *parts[-lines:]])


# frob:doc docs/modules/testing.md#public-api
def run_argv(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> Result[ProcResult, GitError]:
    """Spawn an already-resolved argv (never shell=True); public seam `frob.testing`
    reuses so there is exactly one process-with-timeout helper in the package."""
    full_argv = tuple(argv)
    _log.debug("gitio: spawning %s (cwd=%s, timeout=%gs)", full_argv, cwd, timeout_s)
    try:
        completed = subprocess.run(
            list(full_argv),
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            timeout=timeout_s,
            text=True,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("gitio: spawn failed for %s: %s", full_argv, exc)
        return Err(GitError.GitFailed)
    _log.debug("gitio: %s -> returncode=%d", full_argv, completed.returncode)
    return Ok(
        ProcResult(
            argv=full_argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    )


def _run_git(
    args: Sequence[str], *, cwd: Path, timeout_s: float = _DEFAULT_TIMEOUT_S
) -> Result[str, GitError]:
    """Run `git <args>` in `cwd`; `Ok(stdout)` on exit 0, else `Err(GitFailed)`."""
    argv = ("git", "-C", str(cwd), *args)
    spawned = run_argv(argv, timeout_s=timeout_s)
    if spawned.is_err:
        return Err(spawned.danger_err)
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning(
            "gitio: git %s failed (rc=%d): %s",
            " ".join(args),
            result.returncode,
            _excerpt(result.stderr),
        )
        return Err(GitError.GitFailed)
    return Ok(result.stdout)


# frob:doc docs/modules/testing.md#public-api
def repo_root(start: Path) -> Result[Path, GitError]:
    """The repo root for `start`; worktree-correct via `rev-parse --show-toplevel`."""
    if not start.exists():
        _log.warning("gitio: repo_root: %s does not exist", start)
        return Err(GitError.NotARepo)
    argv = ("git", "-C", str(start), "rev-parse", "--show-toplevel")
    spawned = run_argv(argv)
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("gitio: %s is not inside a git repository", start)
        return Err(GitError.NotARepo)
    root = Path(spawned.danger_ok.stdout.strip())
    _log.debug("gitio: repo_root(%s) = %s", start, root)
    return Ok(root)


# frob:doc docs/modules/testing.md#public-api
def current_branch(root: Path) -> Result[str, GitError]:
    """The current branch name (`git rev-parse --abbrev-ref HEAD`)."""
    return _run_git(("rev-parse", "--abbrev-ref", "HEAD"), cwd=root).map(str.strip)


def _merge_base(root: Path, base: str) -> Result[str, GitError]:
    """`git merge-base HEAD <base>`, trimmed to a bare sha."""
    return _run_git(("merge-base", "HEAD", base), cwd=root).map(str.strip)


_HUNK_HEADER_PREFIX = "@@ "


def _parse_unified_diff(text: str) -> dict[str, list[tuple[int, int]]]:
    """Parse `git diff --unified=0` output into `{file: [(start, end), ...]}`."""
    per_file: dict[str, list[tuple[int, int]]] = {}
    current_file: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path == "/dev/null":
                current_file = None
                continue
            current_file = path[2:] if path.startswith("b/") else path
            per_file.setdefault(current_file, [])
            continue
        if not line.startswith(_HUNK_HEADER_PREFIX) or current_file is None:
            continue
        # "@@ -a,b +c,d @@ ..." -- we want the new-file (+) range.
        try:
            plus_part = line.split("+", 1)[1].split(" ", 1)[0]
        except IndexError:
            continue
        if "," in plus_part:
            start_s, count_s = plus_part.split(",", 1)
            start, count = int(start_s), int(count_s)
        else:
            start, count = int(plus_part), 1
        if count == 0:
            # Pure deletion hunk -- no new lines to select against; skip.
            continue
        end = start + count - 1
        per_file[current_file].append((start, end))
    return per_file


# frob:doc docs/modules/testing.md#public-api
def working_diff(root: Path, base: str) -> Result[Diff, GitError]:
    """The delta from `merge-base(HEAD, base)` to the working tree (committed
    since merge-base, plus staged, unstaged, and untracked whole-file hunks)."""
    mb_result = _merge_base(root, base)
    if mb_result.is_err:
        _log.warning("gitio: working_diff: no merge-base for base=%r", base)
        return Err(mb_result.danger_err)
    mb = mb_result.danger_ok

    diff_result = _run_git(("diff", mb, "--unified=0"), cwd=root)
    if diff_result.is_err:
        return Err(diff_result.danger_err)
    per_file = _parse_unified_diff(diff_result.danger_ok)

    untracked_result = _run_git(
        ("ls-files", "--others", "--exclude-standard"), cwd=root
    )
    if untracked_result.is_err:
        return Err(untracked_result.danger_err)
    hunks: list[Hunk] = []
    for file, spans in per_file.items():
        for start, end in spans:
            hunks.append(Hunk(file=file, span=(start, end)))
    for rel in untracked_result.danger_ok.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        line_count = _count_lines(root / rel)
        hunks.append(Hunk(file=rel, span=(1, max(line_count, 1))))

    _log.info(
        "gitio: working_diff(base=%r): merge-base=%s, %d hunk(s)",
        base,
        mb,
        len(hunks),
    )
    return Ok(Diff(base=mb, hunks=tuple(hunks)))


def _count_lines(path: Path) -> int:
    """Line count of an untracked file, `0` if unreadable (binary, race, etc)."""
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError as exc:
        _log.warning("gitio: could not read untracked file %s: %s", path, exc)
        return 0


__all__ = [
    "Diff",
    "GitError",
    "Hunk",
    "ProcResult",
    "current_branch",
    "repo_root",
    "run_argv",
    "working_diff",
]
