"""End-to-end CLI test for `frob ticket land` (T-0176, docs/modules/tickets.md
#frob-ticket-land) -- exercises the real subprocess entrypoint
(`frob.app.ticket_runner._land`), not just the library function."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "tickets.md").write_text("# Tickets\n\n")
    (root / "src").mkdir()
    (root / "src" / "existing.py").write_text("# existing\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


class TestLandCLI:
    """`frob ticket land <id> --worktree <path> --dry-run` end to end."""

    def test_dry_run_reports_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner.py::_land kind="unit"
        repo = tmp_path / "main"
        _init_repo(repo)

        wt = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature-cli", str(wt), cwd=repo)

        created = run(
            "ticket",
            "new",
            "--title",
            "CLI land smoke",
            "--kind",
            "feature",
            "--scope",
            "src/new_thing.py,tests/test_new_thing.py",
            "--path",
            str(wt),
        )
        assert created.returncode == 0, created.stdout + created.stderr
        # The worktree is off-default-branch -- new_ticket mints a draft id.
        out = created.stdout + created.stderr
        start = out.index("T-draft-")
        ticket_id = out[start : start + len("T-draft-XXXXXXXX")]

        plan = run("ticket", "plan", ticket_id, "--path", str(wt))
        assert plan.returncode == 0, plan.stdout + plan.stderr
        start_r = run("ticket", "start", ticket_id, "--path", str(wt))
        assert start_r.returncode == 0, start_r.stdout + start_r.stderr

        # T-0398 (D-01/D-05): land's post-merge re-verification now
        # actually re-collects and re-runs evidence against the merged
        # worktree tree -- a hand-edited, never-collected id (the old
        # fixture's "no pytest suite ... to collect against" shortcut)
        # would correctly FAIL land now. Give the worktree a REAL,
        # actually-passing test and record it through the real
        # `frob ticket evidence` command, so this test still proves what
        # it always meant to prove (a clean dry run for genuinely-covered,
        # passing, well-reported work), not the pre-D-05 shortcut.
        (wt / "src" / "new_thing.py").write_text(
            "def new_thing() -> int:\n    return 1\n"
        )
        (wt / "tests").mkdir(exist_ok=True)
        (wt / "tests" / "test_new_thing.py").write_text(
            "def test_new_thing() -> None:\n    assert True\n"
        )
        evidenced = run(
            "ticket",
            "evidence",
            ticket_id,
            "tests/test_new_thing.py::test_new_thing",
            "--path",
            str(wt),
        )
        assert evidenced.returncode == 0, evidenced.stdout + evidenced.stderr

        ledger = wt / "tickets.md"
        text = ledger.read_text()
        text += "\n## Done report\n\nsmoke\n"
        ledger.write_text(text)
        _git("add", "-A", cwd=wt)
        _git("commit", "-q", "-m", "cli land work", cwd=wt)

        result = run(
            "ticket",
            "land",
            ticket_id,
            "--worktree",
            str(wt),
            "--dry-run",
            "--path",
            str(repo),
        )
        out = result.stdout + result.stderr
        assert result.returncode == 0, out
        assert "DRY RUN clean" in out

        # A dry run must never touch main.
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert status.stdout.strip() == ""
