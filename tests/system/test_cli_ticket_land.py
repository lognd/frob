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
            "src/new_thing.py",
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

        # Hand-edit in evidence + a Done report (no pytest suite in this
        # fixture repo for `frob ticket evidence` to collect against).
        ledger = wt / "tickets.md"
        text = ledger.read_text()
        text = text.replace("evidence: []", "evidence:\n- tests/x.py::test_ok")
        text += "\n## Done report\n\nsmoke\n"
        ledger.write_text(text)
        (wt / "src" / "new_thing.py").write_text("# new\n")
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
