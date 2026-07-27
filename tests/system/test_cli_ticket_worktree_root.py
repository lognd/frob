"""Regression coverage for T-0131: `frob ticket` root resolution from inside a
linked git worktree, with no explicit `--path` (cwd-based, the scenario the
ticket's incident report described).

Investigation found `frob.app.ticket_runner.run` resolves root purely from
`cfg.ticket_path or Path(".")`, resolved against cwd -- it never walks
upward and never calls `frob.gitio.repo_root`, so there is no code path by
which it could "escape" a linked worktree into the main checkout. Every
variant tried here (fresh worktree with no `.frob/`, worktree with its own
`.frob/`, diverged `tickets.md` content) resolved correctly. These tests
lock that behavior in so a future change to root resolution cannot silently
regress it.

T-0162 note: a linked worktree checks out its own branch, which is (by
definition, since main can't be checked out twice) NOT the repo's default
branch -- so `frob ticket new` from `wt` here mints a `T-draft-<hex>`
provisional id, not a sequential `T-####` (the collision-proofing mechanism
these tests now exercise incidentally). `_new_ticket_id` below extracts
whatever id was actually minted instead of hardcoding `T-0001`, since the
root-resolution behavior under test is orthogonal to id allocation.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tests.system.conftest import run

_CREATED_ID_RE = re.compile(r"created (T-\S+):")


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """A main checkout at `tmp_path/main` plus a linked worktree at
    `tmp_path/wt` on its own branch, each with a distinct `tickets.md`."""
    main = tmp_path / "main"
    main.mkdir()
    _git("init", "-q", cwd=main)
    _git("config", "user.email", "test@example.com", cwd=main)
    _git("config", "user.name", "Test", cwd=main)
    (main / "tickets.md").write_text("# tickets (main)\n")
    _git("add", "-A", cwd=main)
    _git("commit", "-q", "-m", "init", cwd=main)

    wt = tmp_path / "wt"
    _git("worktree", "add", "-q", "-b", "feature", str(wt), cwd=main)
    return main, wt


def _new_ticket_id(cli_output: str) -> str:
    """The id `frob ticket new` reports having created (`created T-####: ...`
    or `created T-draft-<hex>: ...`) -- see module docstring's T-0162 note."""
    m = _CREATED_ID_RE.search(cli_output)
    assert m is not None, f"no 'created T-...' line in: {cli_output!r}"
    return m.group(1)


class TestTicketRootFromLinkedWorktree:
    def test_new_ticket_no_dot_frob_lands_in_worktree(self, tmp_path: Path) -> None:
        """First-ever invocation (no `.frob/` anywhere yet), cwd inside the
        worktree, no `--path`: `frob ticket new` must write to the
        worktree's tickets.md, never the main checkout's."""
        main, wt = _init_repo_with_worktree(tmp_path)
        assert not (wt / ".frob").exists()
        assert not (main / ".frob").exists()

        r = run("ticket", "new", "--title", "wt thing", "--kind", "bug", cwd=wt)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        new_id = _new_ticket_id(out)

        assert new_id in (wt / "tickets.md").read_text()
        assert new_id not in main.joinpath("tickets.md").read_text()

    def test_ticket_new_with_dot_frob_in_worktree_only(self, tmp_path: Path) -> None:
        """A pre-existing `.frob/` inside the worktree (but not main) must
        not change which tickets.md gets written."""
        main, wt = _init_repo_with_worktree(tmp_path)
        (wt / ".frob").mkdir()

        r = run("ticket", "new", "--title", "wt thing 2", "--kind", "bug", cwd=wt)
        assert r.returncode == 0, r.stdout + r.stderr
        new_id = _new_ticket_id(r.stdout + r.stderr)
        assert new_id in (wt / "tickets.md").read_text()
        assert new_id not in main.joinpath("tickets.md").read_text()

    def test_ticket_show_reads_worktrees_own_ledger(self, tmp_path: Path) -> None:
        """With diverged tickets.md content between main and the worktree,
        `frob ticket show` from the worktree must read the worktree's
        ledger, not main's."""
        main, wt = _init_repo_with_worktree(tmp_path)

        r = run("ticket", "new", "--title", "wt-only", "--kind", "bug", cwd=wt)
        assert r.returncode == 0, r.stdout + r.stderr
        new_id = _new_ticket_id(r.stdout + r.stderr)

        # T-0768 clamped the ticket CLI's default output to the runner's own
        # formatted line (deliberate noise reduction) -- the resolved root
        # path no longer rides along in `frob ticket show`'s output unless
        # `-v` restores the diagnostic firehose (gitio spawn lines, which do
        # carry the resolved path). Pass `-v` here so the path-based
        # assertions below keep verifying what they always verified, instead
        # of silently degrading to only the `"wt-only" in out` check.
        r = run("ticket", "-v", "show", new_id, cwd=wt)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "wt-only" in out
        assert str(wt.resolve()) in out
        assert str(main.resolve()) not in out

    def test_ticket_start_prework_written_under_worktree(self, tmp_path: Path) -> None:
        """`frob ticket start` (which runs the pre-work sweep) must record
        its sweep artifact under the worktree's `.frob/`, not main's."""
        main, wt = _init_repo_with_worktree(tmp_path)
        (wt / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        _git("add", "-A", cwd=wt)
        _git("commit", "-q", "-m", "add pkg", cwd=wt)

        r = run(
            "ticket",
            "new",
            "--title",
            "startable",
            "--kind",
            "bug",
            "--scope",
            "pkg.py",
            cwd=wt,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        new_id = _new_ticket_id(r.stdout + r.stderr)

        # T-0474: `start` backgrounds the sweep by default -- `--foreground`
        # keeps this test's synchronous, deterministic assertion valid.
        r = run("ticket", "start", new_id, "--foreground", cwd=wt)
        assert r.returncode == 0, r.stdout + r.stderr

        assert (wt / ".frob" / "prework" / f"{new_id}.json").exists()
        assert not (main / ".frob").exists()
