"""Integration test for `frob fleet status` (T-0573): drives the real CLI
over two on-disk git repos (each with its own tickets.md) and a real
fleet.toml manifest, binding `src/frob/fleet` as an interface with at
least one integration edge (TEST003)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]


def _git(args: list[str], cwd: Path) -> None:
    """Run a git command in `cwd`, raising on failure."""
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _init_repo(path: Path) -> None:
    """A minimal git repo `frob fleet status` can probe for branch/dirty state."""
    path.mkdir(parents=True)
    _git(["init", "-q"], path)
    # frob:secret-fake -- fixture-only git identity, not a real address
    _git(["config", "user.email", "a@b.c"], path)
    _git(["config", "user.name", "a"], path)
    (path / "README.md").write_text("hello\n")
    _git(["add", "-A"], path)
    _git(["commit", "-q", "-m", "init"], path)


class TestFleetIntegration:
    def test_fleet_status_table_over_real_repos(self, tmp_path: Path) -> None:
        """`frob fleet status --skip-gates` over a real two-repo manifest
        prints a reddest-first table with both repos' names and branches."""
        # frob:tests src/frob/fleet kind="integration"
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _init_repo(repo_a)
        _init_repo(repo_b)

        manifest = tmp_path / "fleet.toml"
        manifest.write_text(
            f'[[repo]]\nname = "repo-a"\npath = "{repo_a}"\n\n'
            f'[[repo]]\nname = "repo-b"\npath = "{repo_b}"\n'
        )

        result = subprocess.run(
            FROB
            + [
                "fleet",
                "status",
                "--manifest",
                str(manifest),
                "--skip-gates",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "repo-a" in result.stdout
        assert "repo-b" in result.stdout
