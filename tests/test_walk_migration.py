"""T-0471: arch/xref no longer descend into `.claude/worktrees/` or other
pruned directories (docs/modules/gates.md#walk-lint-unpruned-traversal-
t-0471) -- the concrete regression WALK001 exists to prevent.

Both `frob.arch._collect_files` and `frob.xref._collect_source_files` used
to `root.rglob("*")` the whole subtree (arch/__init__.py:59,
xref/__init__.py:140 pre-T-0471) before filtering, which meant a stale
nested git worktree parked under `.claude/worktrees/` was fully walked
even though its contents were always going to be discarded. A real
dispatched-agent worktree is its own separate git checkout, never part of
the parent repo's tracked-file index (and typically also `.gitignore`d) --
which is exactly what the shared `frob.excludes.iter_files`'s `git
ls-files` fast path (T-0471) now uses to prune it for free, with zero
traversal cost, instead of `_should_prune_dir`-filtering it post-walk.
These tests plant a nested-worktree-shaped, deliberately UNTRACKED
directory under `.claude/worktrees/` and assert neither collector's result
set contains anything from inside it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.arch import analyze_project
from frob.xref import xref


# frob:waive DUP001 reason="parallel per-domain test scaffolding across 9 sibling test modules \
# (9 sites) -- each file exercises a structurally similar check for \
# a distinct domain/module with the same arrange-act shape; \
# extracting would blur which domain owns which check"
def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str = "commit") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _plant_untracked_worktree(root: Path) -> Path:
    """A `.claude/worktrees/agent-x` checkout, deliberately left UNTRACKED
    (never `git add`ed) -- the real shape a dispatched-agent worktree takes
    relative to its parent repo's index."""
    nested = root / ".claude" / "worktrees" / "agent-x"
    nested.mkdir(parents=True)
    (nested / "poison.py").write_text(
        "class GodClass:\n"
        + "\n".join(f"    def m{i}(self):\n        pass" for i in range(200))
    )
    return nested


def test_arch_does_not_walk_nested_worktree(tmp_path: Path) -> None:
    # frob:tests tests/test_walk_migration.py::test_arch_does_not_walk_nested_worktree
    _init_repo(tmp_path)
    (tmp_path / "main.py").write_text("x = 1\n")
    _commit(tmp_path)
    _plant_untracked_worktree(tmp_path)

    result = analyze_project(tmp_path)

    files_seen = {s.file for s in result.suggestions}
    assert not any("poison.py" in f for f in files_seen)


def test_xref_does_not_walk_nested_worktree(tmp_path: Path) -> None:
    # frob:tests tests/test_walk_migration.py::test_xref_does_not_walk_nested_worktree
    _init_repo(tmp_path)
    (tmp_path / "defn.py").write_text("def helper(x):\n    return x\n")
    _commit(tmp_path)
    _plant_untracked_worktree(tmp_path)

    result = xref("helper", tmp_path)

    assert result.is_ok
    xr = result.danger_ok
    assert xr.definition is not None
    assert "poison" not in xr.definition.file
    assert all("poison" not in u.file for u in xr.usages)
