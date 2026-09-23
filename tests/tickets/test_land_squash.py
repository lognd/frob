"""T-5126: `_exclude_dev_merged_ledger_files` -- the T-3324
self-conformance attribution fix. Positive control (b) from the ticket's
plan: a land whose merge brings in an unrelated ticket's ledger file must
not have that file counted as "this land's own touched files".

Builds real git plumbing (no `frob ticket` verbs) so the fixture matches
what a genuine `git merge dev --no-edit` inside a worktree produces: a
`main` line that gains a second ticket's `ticket.md` after the worktree
branched off, then the worktree branch merging `main` back in.
"""

# frob:ticket T-5126

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.tickets._land_squash import _exclude_dev_merged_ledger_files


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """`subprocess.run` with `check=True` against `cwd` -- same shape the
    sibling `tests/unit/test_land_squash_stage.py` fixture uses."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _init_repo(root: Path) -> None:
    """A fresh git repo on branch `main`, committer identity set."""
    root.mkdir(parents=True)
    _run(["git", "init", "-q"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    _run(["git", "checkout", "-q", "-b", "main"], root)


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _commit(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


# frob:tests src/frob/tickets/_land_squash.py::_exclude_dev_merged_ledger_files
def test_dev_merged_ledger_file_excluded(tmp_path: Path) -> None:
    """A ticket ledger file that arrives ONLY via merging `main` (dev) in
    -- never touched by the worktree's own commits -- is excluded from
    the returned touched-files set (must-exclude half of the control)."""
    root = tmp_path / "repo"
    _init_repo(root)
    _write(root, "README.md", "seed\n")
    _commit(root, "seed")

    _run(["git", "checkout", "-q", "-b", "feature"], root)
    _write(root, "src/feature.py", "def feature(): pass\n")
    _commit(root, "feature work")

    _run(["git", "checkout", "-q", "main"], root)
    _write(root, "tickets/T-9999/ticket.md", "id: T-9999\nunrelated ticket\n")
    _commit(root, "unrelated ticket lands on main")

    _run(["git", "checkout", "-q", "feature"], root)
    _run(["git", "merge", "-q", "main", "--no-edit"], root)

    touched = frozenset({"src/feature.py", "tickets/T-9999/ticket.md"})
    narrowed = _exclude_dev_merged_ledger_files(root, "main", touched)

    assert narrowed == frozenset({"src/feature.py"})


# frob:tests src/frob/tickets/_land_squash.py::_exclude_dev_merged_ledger_files
def test_own_ledger_edit_after_merge_still_counted(tmp_path: Path) -> None:
    """A ticket ledger file the worktree's OWN commits additionally edit
    AFTER merging main in must NOT be excluded -- it genuinely differs
    from main's tip, so it is this land's own change (must-not-exclude
    half of the control; the exact shape a blanket `tickets/**` exclusion
    would silently drop)."""
    root = tmp_path / "repo"
    _init_repo(root)
    _write(root, "README.md", "seed\n")
    _write(root, "tickets/T-8888/ticket.md", "id: T-8888\nqueued\n")
    _commit(root, "seed")

    _run(["git", "checkout", "-q", "-b", "feature"], root)
    _write(root, "tickets/T-8888/ticket.md", "id: T-8888\nin-progress\n")
    _commit(root, "advance own ticket")

    _run(["git", "checkout", "-q", "main"], root)
    _write(root, "tickets/T-9999/ticket.md", "id: T-9999\nunrelated ticket\n")
    _commit(root, "unrelated ticket lands on main")

    _run(["git", "checkout", "-q", "feature"], root)
    _run(["git", "merge", "-q", "main", "--no-edit"], root)

    touched = frozenset({"tickets/T-8888/ticket.md", "tickets/T-9999/ticket.md"})
    narrowed = _exclude_dev_merged_ledger_files(root, "main", touched)

    assert narrowed == frozenset({"tickets/T-8888/ticket.md"})
