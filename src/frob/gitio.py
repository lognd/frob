"""The ONE git subprocess seam (docs/modules/testing.md), shared by testing and gates.

Every git invocation in frob goes through this module: `repo_root` (worktree-
correct root discovery), `working_diff` (merge-base-to-worktree unified diff,
including uncommitted and untracked changes), `current_branch`, and
`git_common_dir` (the shared `.git` dir across every linked worktree of a
repo, T-0784 -- `frob.tickets._leases` and `frob.gates._exclude_hazard` both
delegate here rather than each spawning and parsing their own `rev-parse
--git-common-dir`). Two diff implementations would desync (docs/modules/
gates.md's old `gates/diff.py` design is superseded by this module). `_run_git`
is the private spawn primitive; `run_argv` is the small public wrapper
`frob.testing` reuses for its own runner spawns so there is exactly one
subprocess-with-timeout helper in the package, never a second copy living
under `frob.testing`.
"""
# frob:waive ARCH102 reason="13 of 15 exports form one connected cluster \
# around the single subprocess seam this module's docstring names (_run_git \
# feeding repo_root/working_diff/current_branch/git_common_dir/run_argv); \
# the 2 outliers (reset_common_dir_cache, SpawnRecorder) are test-support-only \
# helpers for that same cache/spawn seam with no production call edges into \
# the rest -- splitting the one real seam this module exists to centralize \
# just to detach its own test-support helpers would be artificial"  # noqa: E501

from __future__ import annotations

import contextvars
import subprocess
import threading
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

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


# frob:doc docs/modules/testing.md#spawn-recorder-t-0776
class SpawnRecorder:
    """Tallies every argv spawned through `run_argv` while active (T-0776);
    the exact-count complement to the static loop-invariant-effect
    detector -- a test-mode-only litmus for the "same argv spawned twice
    in one CLI invocation" class of regression (e.g. T-0773's rev-parse
    incident). Never instantiate directly outside a test; use
    `spawn_recorder()`."""

    def __init__(self) -> None:
        self._counts: Counter[tuple[str, ...]] = Counter()

    # frob:doc docs/modules/testing.md#spawn-recorder-t-0776
    def record(self, argv: tuple[str, ...]) -> None:
        """Tally one spawned `argv`; called by `run_argv` while this
        recorder is the active one for the current context."""
        self._counts[argv] += 1

    # frob:doc docs/modules/testing.md#spawn-recorder-t-0776
    def counts(self) -> Mapping[tuple[str, ...], int]:
        """A snapshot `{argv: spawn count}` for everything recorded so far."""
        return dict(self._counts)

    # frob:doc docs/modules/testing.md#spawn-recorder-t-0776
    def duplicates(
        self,
        budgets: Mapping[tuple[str, ...], int] | None = None,
        *,
        default_budget: int = 1,
    ) -> dict[tuple[str, ...], int]:
        """Argv tuples whose spawn count exceeds their declared budget --
        `budgets` overrides `default_budget` (1, i.e. "spawned at most
        once") per exact argv tuple. Empty dict means every spawn stayed
        within budget."""
        budget_map = budgets or {}
        return {
            argv: n
            for argv, n in self._counts.items()
            if n > budget_map.get(argv, default_budget)
        }


# frob:doc docs/modules/testing.md#spawn-recorder-t-0776
_active_recorder: contextvars.ContextVar[SpawnRecorder | None] = contextvars.ContextVar(
    "_frob_gitio_active_recorder", default=None
)


# frob:doc docs/modules/testing.md#spawn-recorder-t-0776
@contextmanager
def spawn_recorder() -> Iterator[SpawnRecorder]:
    """Test-only context manager: every `run_argv` spawn made while the
    block is active is tallied onto the yielded `SpawnRecorder` (T-0776).
    Zero-cost and behavior-neutral when not active -- `run_argv` only pays
    a single `ContextVar.get()` outside this block, and never alters what
    it spawns or returns either way."""
    recorder = SpawnRecorder()
    token = _active_recorder.set(recorder)
    try:
        yield recorder
    finally:
        _active_recorder.reset(token)


# frob:ticket T-1067
# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_gitio.py::TestWorkingDiff.test_bad_base_ref_is_git_failed
# frob:tests tests/test_gitio.py::TestWorkingDiff.test_diff_command_failure_propagates
# frob:tests tests/test_testing.py::TestRunners.test_exit_code_is_data
def excerpt(text: str, *, lines: int = _EXCERPT_LINES) -> str:
    """Bound a stdout/stderr blob to its last N lines -- the useful end.
    Public (T-1067, extracted from a byte-identical private duplicate that
    lived in `frob.testing._runners`) so any caller truncating captured
    process output shares this one rule instead of re-deriving it."""
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
    env: Mapping[str, str] | None = None,
) -> Result[ProcResult, GitError]:
    """Spawn an already-resolved argv (never shell=True); public seam `frob.testing`
    reuses so there is exactly one process-with-timeout helper in the package.
    Routed through `frob.process._guard.guarded_subprocess_run` (T-0778) so
    `FROB_DISABLE_EXEC=1` genuinely refuses every git spawn this module (and
    transitively the serve daemon and tickets lease reads, which have no
    other spawn seam) would otherwise make -- returns `Err(GitError.
    GitFailed)` without ever spawning a process while the kill switch is
    flipped.

    `env`, when given, replaces the spawned process's environment entirely
    (the same `subprocess.Popen`/`subprocess.run` semantics -- `None` means
    "inherit the caller's environment unchanged", not "empty"). T-2005:
    added because `guarded_subprocess_run` already forwards any kwarg
    (including `env`) straight to `subprocess.run`, but this wrapper had no
    parameter to accept one -- a caller building an `env` override (e.g.
    BUG002's `_run_designated_test`, PYTHONPATH-pointed at a parent-commit
    checkout) had no way to pass it through, and the override was silently
    dropped, so the spawned process ran with the CALLER's own environment
    instead."""
    full_argv = tuple(argv)
    recorder = _active_recorder.get()
    if recorder is not None:
        recorder.record(full_argv)
    _log.debug("gitio: spawning %s (cwd=%s, timeout=%gs)", full_argv, cwd, timeout_s)
    try:
        guarded = guarded_subprocess_run(
            list(full_argv),
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            timeout=timeout_s,
            text=True,
            check=False,
            env=dict(env) if env is not None else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("gitio: spawn failed for %s: %s", full_argv, exc)
        return Err(GitError.GitFailed)
    if guarded.is_err:
        # Kill switch flipped (FROB_DISABLE_EXEC=1) -- guard already logged
        # a warning and never spawned anything; surface as the same
        # GitError callers already handle.
        return Err(GitError.GitFailed)
    completed = guarded.danger_ok
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
            excerpt(result.stderr),
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


# frob:ticket T-0784
# Process-lifetime memoization for `git_common_dir`, carried forward from
# T-0773 (which landed this cache in `frob.tickets._leases` before this
# ticket promoted the function itself into the single `frob.gitio` seam).
# Keyed by the RESOLVED root path so different callers spelling the same
# worktree differently (relative vs. absolute, symlinked) still share one
# cache entry. Safe because the shared `.git` common dir cannot move
# mid-invocation, so caching it for the process's lifetime is never stale
# within one CLI invocation. `_common_dir_lock` (T-0773 precedent)
# serializes cache reads/writes across threads (`frob.serve`'s daemon
# thread and a gate pool's workers can call in concurrently); the `git`
# subprocess itself runs OUTSIDE the lock so one thread spawning it never
# blocks another thread's unrelated cache lookups.
_common_dir_lock = threading.Lock()
_common_dir_cache: dict[Path, Result[Path, GitError]] = {}


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_gitio.py::TestGitCommonDir.test_memoized_per_root kind="unit"
def git_common_dir(root: Path) -> Result[Path, GitError]:
    """The shared `.git` directory for `root`'s repository (`git rev-parse
    --git-common-dir`), resolved to an absolute path -- identical across
    every linked worktree of the same repo, unlike `root / ".git"` itself
    (a linked worktree's `.git` is a pointer file, not the shared
    directory). `Err(GitFailed)` if `root` is not inside a git work tree
    or the git call fails. The single canonical implementation (T-0784) --
    `frob.tickets._leases._git_common_dir` and
    `frob.gates._exclude_hazard._git_common_dir` both delegate here rather
    than each spawning and parsing their own `rev-parse --git-common-dir`.

    Memoized per resolved `root` for the process's lifetime (T-0773,
    carried forward by T-0784): a second call for the same `root` returns
    the cached `Result` instead of spawning `git` again -- this is the fix
    for the 2026-07-22 incident where a single `frob ticket list`/`doable`
    spawned this subprocess dozens of times (once per candidate/ticket
    row). A benign race where two threads both miss the cache and both
    spawn `git` for the same `root` is possible but harmless (idempotent
    result, last write wins)."""
    key = root.resolve()
    with _common_dir_lock:
        cached = _common_dir_cache.get(key)
    if cached is not None:
        return cached
    spawned = run_argv(("git", "-C", str(root), "rev-parse", "--git-common-dir"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("gitio: git-common-dir lookup failed under %s", root)
        result: Result[Path, GitError] = Err(GitError.GitFailed)
        with _common_dir_lock:
            _common_dir_cache[key] = result
        return result
    raw = spawned.danger_ok.stdout.strip()
    if not raw:
        result = Err(GitError.GitFailed)
        with _common_dir_lock:
            _common_dir_cache[key] = result
        return result
    common_dir = Path(raw)
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    result = Ok(common_dir)
    with _common_dir_lock:
        _common_dir_cache[key] = result
    return result


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_gitio.py::TestGitCommonDir.test_reset_clears_cache kind="unit"
def reset_common_dir_cache() -> None:
    """Drop the `git_common_dir` process-lifetime memo (T-0773/T-0784),
    under `_common_dir_lock` -- available to tests that need to simulate a
    fresh CLI invocation (or a fresh daemon poll cycle) within one
    interpreter; not required for correctness on the read path otherwise."""
    with _common_dir_lock:
        _common_dir_cache.clear()


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_gitio.py::TestCommonDirAndBranch.test_single_spawn_parses_both_lines kind="unit"  # noqa: E501
def common_dir_and_branch(root: Path) -> Result[tuple[Path, str], GitError]:
    """`(git_common_dir(root), current-branch-name)` in ONE `git` spawn
    (T-0784) via `git rev-parse --git-common-dir --abbrev-ref HEAD`, which
    prints one resolved value per line in the order requested -- the
    batched replacement for `frob.tickets._leases.record_lease`'s old
    back-to-back `rev-parse --git-common-dir` + `branch --show-current`
    calls. Bypasses the `git_common_dir` memo (it always spawns) since the
    caller also wants the branch, which is not itself cached -- callers
    that only need the common dir should call `git_common_dir` instead to
    get the memoized fast path."""
    spawned = run_argv(
        (
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--git-common-dir",
            "--abbrev-ref",
            "HEAD",
        )
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("gitio: common_dir_and_branch lookup failed under %s", root)
        return Err(GitError.GitFailed)
    lines = spawned.danger_ok.stdout.splitlines()
    if len(lines) < 2:
        _log.warning(
            "gitio: common_dir_and_branch: expected 2 lines, got %d under %s",
            len(lines),
            root,
        )
        return Err(GitError.GitFailed)
    raw_common, branch = lines[0].strip(), lines[1].strip()
    if not raw_common:
        return Err(GitError.GitFailed)
    common_dir = Path(raw_common)
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    return Ok((common_dir, branch))


def _merge_base(root: Path, base: str) -> Result[str, GitError]:
    """`git merge-base HEAD <base>`, trimmed to a bare sha."""
    return _run_git(("merge-base", "HEAD", base), cwd=root).map(str.strip)


_HUNK_HEADER_PREFIX = "@@ "


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to str.startswith/ \
# str.strip/dict.setdefault, plain str/dict methods the resolver cannot statically \
# bound; the one real raise path (the hunk-header token parse) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
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
            if "," in plus_part:
                start_s, count_s = plus_part.split(",", 1)
                start, count = int(start_s), int(count_s)
            else:
                start, count = int(plus_part), 1
        except (IndexError, KeyError, TypeError, ValueError):
            # A malformed hunk header (unexpected git diff output shape)
            # is skipped, never a crash -- this is a best-effort line-range
            # index, not a correctness-critical parse.
            continue
        if count == 0:
            # Pure deletion hunk -- no new lines to select against; skip.
            continue
        end = start + count - 1
        per_file.setdefault(current_file, []).append((start, end))
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
    hunks: list[Hunk] = _tracked_hunks(per_file)
    hunks.extend(_untracked_hunks(root, untracked_result.danger_ok))

    _log.info(
        "gitio: working_diff(base=%r): merge-base=%s, %d hunk(s)",
        base,
        mb,
        len(hunks),
    )
    return Ok(Diff(base=mb, hunks=tuple(hunks)))


# frob:doc docs/modules/testing.md#public-api
# frob:ticket T-2018
def commit_diff(root: Path, commit_sha: str) -> Result[Diff, GitError]:
    """The delta a single COMMIT introduced (`commit_sha^..commit_sha`),
    tracked hunks only -- `working_diff`'s COMMIT-relative sibling, for a
    caller that needs one already-landed commit's own touched-line spans
    rather than the working tree's delta against a merge-base. T-2018:
    this is the building block `frob.verify._attribution`'s ad-hoc
    candidate-commit batch construction needs -- attributing a finding
    against an arbitrary past commit range, not only the persisted
    verify-queue's own recorded intents, requires computing the SAME
    hunk-span shape `_touched_symrefs_for_intent` (`frob.tickets._land`)
    already consumes for a land-time intent, but for a commit that may be
    long past `HEAD`'s own merge-base. No untracked-file handling here
    (unlike `working_diff`): an already-landed commit has no working-tree
    concept of "untracked" -- everything in its tree is, by definition,
    tracked at that commit."""
    diff_result = _run_git(
        ("diff", f"{commit_sha}^", commit_sha, "--unified=0"), cwd=root
    )
    if diff_result.is_err:
        return Err(diff_result.danger_err)
    per_file = _parse_unified_diff(diff_result.danger_ok)
    hunks = _tracked_hunks(per_file)
    _log.info(
        "gitio: commit_diff(%s): %d hunk(s)",
        commit_sha[:12],
        len(hunks),
    )
    return Ok(Diff(base=f"{commit_sha}^", hunks=tuple(hunks)))


# frob:doc docs/modules/testing.md#public-api
# frob:ticket T-2018
def recent_commits(
    root: Path, *, since: str | None = None, limit: int | None = None
) -> Result[tuple[str, ...], GitError]:
    """Commit shas reachable from `HEAD`, oldest-candidate-range-shaped:
    `since` given -> every commit in `since..HEAD` (a watermark sha, most
    commonly); `since=None` -> the `limit`-bounded most recent commits on
    `HEAD` (a cold-start range with no watermark to anchor on yet).
    Newest-first (`git log`'s own default order). T-2018: the candidate-
    commit enumeration `frob.verify._attribution`'s ad-hoc batch
    construction needs when no persisted verify-queue entry covers the
    commit that could have caused a finding."""
    argv: list[str] = ["log", "--format=%H"]
    if since is not None:
        argv.append(f"{since}..HEAD")
    if limit is not None:
        argv.extend(("-n", str(limit)))
    result = _run_git(tuple(argv), cwd=root)
    if result.is_err:
        return Err(result.danger_err)
    shas = tuple(line.strip() for line in result.danger_ok.splitlines() if line.strip())
    return Ok(shas)


def _tracked_hunks(per_file: dict[str, list[tuple[int, int]]]) -> list[Hunk]:
    """Flatten the per-file span map from `_parse_unified_diff` into `Hunk`s."""
    hunks: list[Hunk] = []
    for file, spans in per_file.items():
        for start, end in spans:
            hunks.append(Hunk(file=file, span=(start, end)))
    return hunks


def _untracked_hunks(root: Path, listing: str) -> list[Hunk]:
    """One whole-file `Hunk` per untracked path in `git ls-files --others` output."""
    hunks: list[Hunk] = []
    for rel in listing.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        abs_path = root / rel
        if abs_path.is_dir():
            # Untracked gitlink or nested worktree dir (e.g. a submodule-like
            # checkout under .claude/worktrees/): `ls-files --others` lists
            # its path like a file, but it is not one -- skip cleanly rather
            # than attempt a read that raises Errno 21.
            _log.debug("gitio: skipping untracked directory/gitlink %s", rel)
            continue
        line_count = _count_lines(abs_path)
        hunks.append(Hunk(file=rel, span=(1, max(line_count, 1))))
    return hunks


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
    "SpawnRecorder",
    "commit_diff",
    "common_dir_and_branch",
    "current_branch",
    "excerpt",
    "git_common_dir",
    "repo_root",
    "recent_commits",
    "reset_common_dir_cache",
    "run_argv",
    "spawn_recorder",
    "working_diff",
]
