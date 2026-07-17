"""End-to-end tests for `frob ticket` (docs/tickets.md)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import FROB, run


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    _git("init", "-q", cwd=tmp_path)
    _git("config", "user.email", "test@example.com", cwd=tmp_path)
    _git("config", "user.name", "Test", cwd=tmp_path)
    (tmp_path / "pkg.py").write_text(
        "def add(x: int, y: int) -> int:\n    return x + y\n"
    )
    _git("add", "-A", cwd=tmp_path)
    _git("commit", "-q", "-m", "init", cwd=tmp_path)
    return tmp_path


class TestTicketRoundTrip:
    def test_new_list_doable(self, tmp_path):
        _init_repo(tmp_path)
        r = run(
            "ticket",
            "new",
            "--title",
            "do a thing",
            "--kind",
            "feature",
            "--path",
            str(tmp_path),
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "T-0001" in out

        r = run("ticket", "list", "--path", str(tmp_path))
        assert "T-0001" in r.stdout + r.stderr

        r = run("ticket", "doable", "--path", str(tmp_path))
        assert "T-0001" in r.stdout + r.stderr

    def test_show(self, tmp_path):
        _init_repo(tmp_path)
        run(
            "ticket",
            "new",
            "--title",
            "showable",
            "--kind",
            "bug",
            "--path",
            str(tmp_path),
        )
        r = run("ticket", "show", "T-0001", "--path", str(tmp_path))
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "showable" in out

    def test_start_auto_plans_queued_ticket(self, tmp_path):
        # The state machine is queued -> planned -> in-progress; `start` on a
        # freshly-created (queued) ticket takes BOTH legal steps for you.
        _init_repo(tmp_path)
        run(
            "ticket",
            "new",
            "--title",
            "flow",
            "--kind",
            "feature",
            "--path",
            str(tmp_path),
        )
        r = run("ticket", "start", "T-0001", "--path", str(tmp_path))
        assert r.returncode == 0, r.stderr
        shown = run("ticket", "show", "T-0001", "--path", str(tmp_path))
        assert "in-progress" in shown.stdout

    def test_plan_then_sweep_flow(self, tmp_path):
        # Explicit staging: plan moves queued -> planned; sweep re-records
        # the pre-work sweep for an in-progress ticket and refuses otherwise.
        _init_repo(tmp_path)
        run(
            "ticket",
            "new",
            "--title",
            "flow2",
            "--kind",
            "feature",
            "--path",
            str(tmp_path),
        )
        r = run("ticket", "plan", "T-0001", "--path", str(tmp_path))
        assert r.returncode == 0, r.stderr
        r = run("ticket", "sweep", "T-0001", "--path", str(tmp_path))
        assert r.returncode != 0  # not in-progress yet
        r = run("ticket", "start", "T-0001", "--path", str(tmp_path))
        assert r.returncode == 0, r.stderr
        r = run("ticket", "sweep", "T-0001", "--path", str(tmp_path))
        assert r.returncode == 0, r.stderr

    def test_close_without_evidence_fails(self, tmp_path):
        _init_repo(tmp_path)
        run(
            "ticket",
            "new",
            "--title",
            "closeable",
            "--kind",
            "feature",
            "--path",
            str(tmp_path),
        )
        r = run("ticket", "close", "T-0001", "--path", str(tmp_path))
        assert r.returncode != 0

    def test_fail_records_failure_log(self, tmp_path):
        _init_repo(tmp_path)
        run(
            "ticket",
            "new",
            "--title",
            "flaky",
            "--kind",
            "bug",
            "--path",
            str(tmp_path),
        )
        r = run(
            "ticket",
            "fail",
            "T-0001",
            "--summary",
            "hit a WSL clipboard edge case",
            "--path",
            str(tmp_path),
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out

        ledger = tmp_path / "tickets.md"
        assert ledger.exists()
        body = ledger.read_text()
        assert "attempt 1" in body
        assert "hit a WSL clipboard edge case" in body


class TestTicketNewNonInteractive:
    def test_new_does_not_prompt_or_hang_without_a_tty(self, tmp_path):
        _init_repo(tmp_path)
        # subprocess.run with input=None and no pty attached means stdin is
        # not a TTY, so the clipboard-attach prompt in `frob ticket new`
        # must never fire; a 10s timeout catches a hang if it does.
        r = subprocess.run(
            FROB
            + [
                "ticket",
                "new",
                "--title",
                "no prompt please",
                "--kind",
                "feature",
                "--path",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "?" not in out
