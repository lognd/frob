"""
frob dispatch -- branch-per-agent git worktree isolation.

Each dispatch creates a git worktree on a fresh branch. Agents work in
isolation (no lock contention, no read-the-whole-file needed for context).
When done, `collect` rebases the branch onto the current HEAD and merges
with --no-ff for a clean history.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob._frob_state import ensure_gitignore


class DispatchError(ErrorSet):
    NotAGitRepo = "Not inside a git repository"
    WorktreeExists = "Dispatch worktree already exists"
    NotFound = "Dispatch not found"
    MergeFailed = "Rebase/merge failed; manual resolution required"
    GitError = "Git command failed"


_STATE_DIR = ".frob/dispatch"


class DispatchInfo(BaseModel):
    model_config = {}

    dispatch_id: str
    branch: str
    worktree: str
    base_branch: str
    base_commit: str
    label: str
    created_at: float


def _git(args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def _repo_root(project_root: Path) -> Result[Path, DispatchError]:
    rc, out, _ = _git(["rev-parse", "--show-toplevel"], cwd=str(project_root))
    if rc != 0:
        return Err(DispatchError.NotAGitRepo)
    return Ok(Path(out))


def _current_branch(root: Path) -> str:
    _, out, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(root))
    return out or "HEAD"


def _current_commit(root: Path) -> str:
    _, out, _ = _git(["rev-parse", "HEAD"], cwd=str(root))
    return out


def _state_path(root: Path, dispatch_id: str) -> Path:
    return root / _STATE_DIR / f"{dispatch_id}.json"


def _load_state(root: Path, dispatch_id: str) -> Result[DispatchInfo, DispatchError]:
    p = _state_path(root, dispatch_id)
    if not p.exists():
        return Err(DispatchError.NotFound)
    data = json.loads(p.read_text())
    return Ok(DispatchInfo(**data))


def create_dispatch(
    label: str,
    *,
    project_root: Path,
    mission_id: str | None = None,
) -> Result[DispatchInfo, DispatchError]:
    """
    Create a git worktree on a new branch for isolated agent work.

    Returns DispatchInfo with the worktree path the agent should work in.
    """
    root_result = _repo_root(project_root)
    if root_result.is_err:
        return Err(root_result.danger_err)
    root = root_result.danger_ok

    base_branch = _current_branch(root)
    base_commit = _current_commit(root)

    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:32]
    ts = int(time.monotonic_ns() % 10**9)
    dispatch_id = f"{slug}-{ts:08x}"
    branch = f"frob/dispatch/{dispatch_id}"
    worktree_path = root / ".frob" / "worktrees" / dispatch_id

    # Create branch + worktree
    rc, _, err = _git(
        ["worktree", "add", "-b", branch, str(worktree_path)], cwd=str(root)
    )
    if rc != 0:
        return Err(DispatchError.GitError)

    info = DispatchInfo(
        dispatch_id=dispatch_id,
        branch=branch,
        worktree=str(worktree_path),
        base_branch=base_branch,
        base_commit=base_commit,
        label=label,
        created_at=time.time(),
    )

    # Persist state
    state_dir = root / _STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    _state_path(root, dispatch_id).write_text(info.model_dump_json(indent=2))

    # Ensure .frob/ is gitignored
    ensure_gitignore(root)

    return Ok(info)


def collect_dispatch(
    dispatch_id: str,
    *,
    project_root: Path,
    strategy: str = "rebase",
) -> Result[None, DispatchError]:
    """
    Rebase the dispatch branch onto the current HEAD then fast-forward merge.

    strategy: 'rebase' (default) or 'merge' (--no-ff squash).
    """
    root_result = _repo_root(project_root)
    if root_result.is_err:
        return Err(root_result.danger_err)
    root = root_result.danger_ok

    info_result = _load_state(root, dispatch_id)
    if info_result.is_err:
        return Err(info_result.danger_err)
    info = info_result.danger_ok

    current_branch = _current_branch(root)

    # Remove the worktree first -- git won't rebase a branch checked out elsewhere.
    wt = Path(info.worktree)
    if wt.exists():
        _git(["worktree", "remove", "--force", str(wt)], cwd=str(root))

    if strategy == "rebase":
        # Rebase commits on dispatch branch (since base_commit) onto current HEAD.
        # git rebase --onto <newbase> <upstream> <branch>
        rc, _, err = _git(
            ["rebase", "--onto", current_branch, info.base_commit, info.branch],
            cwd=str(root),
        )
        if rc != 0:
            _git(["rebase", "--abort"], cwd=str(root))
            return Err(DispatchError.MergeFailed)

        # Fast-forward the current branch to the rebased tip
        rc, _, err = _git(["merge", "--ff-only", info.branch], cwd=str(root))
    else:
        rc, _, err = _git(
            [
                "merge",
                "--no-ff",
                "-m",
                f"dispatch: collect {info.label} ({dispatch_id})",
                info.branch,
            ],
            cwd=str(root),
        )

    if rc != 0:
        return Err(DispatchError.MergeFailed)

    # Worktree already removed above; just delete the branch and state file
    _git(["branch", "-D", info.branch], cwd=str(root))
    sp = _state_path(root, info.dispatch_id)
    if sp.exists():
        sp.unlink()

    return Ok(None)


def abort_dispatch(
    dispatch_id: str,
    *,
    project_root: Path,
) -> Result[None, DispatchError]:
    root_result = _repo_root(project_root)
    if root_result.is_err:
        return Err(root_result.danger_err)
    root = root_result.danger_ok

    info_result = _load_state(root, dispatch_id)
    if info_result.is_err:
        return Err(info_result.danger_err)
    info = info_result.danger_ok

    _cleanup_dispatch(root, info)
    return Ok(None)


def list_dispatches(project_root: Path) -> list[DispatchInfo]:
    root_result = _repo_root(project_root)
    if root_result.is_err:
        return []
    root = root_result.danger_ok

    state_dir = root / _STATE_DIR
    if not state_dir.exists():
        return []

    results = []
    for p in sorted(state_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            results.append(DispatchInfo(**data))
        except Exception:
            continue
    return results


def _cleanup_dispatch(root: Path, info: DispatchInfo) -> None:
    wt = Path(info.worktree)
    if wt.exists():
        _git(["worktree", "remove", "--force", str(wt)], cwd=str(root))
    _git(["branch", "-D", info.branch], cwd=str(root))
    sp = _state_path(root, info.dispatch_id)
    if sp.exists():
        sp.unlink()
