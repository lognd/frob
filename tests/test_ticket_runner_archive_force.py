"""CLI-level coverage for `frob ticket archive --force` (T-0810).

T-0764 added `archive(root, *, force: bool = False)` in
`frob.tickets.archive`, refusing when a live cross-worktree lease exists
unless `force=True`; that landing left the CLI entrypoint (`_archive` in
`frob.app.ticket_runner`) without a way to pass `force` through. This
module exercises the CLI end to end: refusal without `--force` when a
live lease exists, success with `--force`, and the warning log emitted
when `--force` overrides one."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.tickets import TicketState, load_active
from frob.tickets._leases import _LeaseRecord, leases_dir


def _repo(tmp_path: Path) -> Path:
    """A minimal git repo `frob.tickets.archive` can resolve leases/locks
    against."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(root), check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=str(root), check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(root), check=True)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(root), check=True)
    return root


# frob:ticket T-0601
def _write_live_lease(root: Path, ticket_id: str, worktree: Path) -> None:
    """Record a lease whose worktree exists on disk, so
    `read_all_leases` treats it as live rather than stale."""
    resolved = leases_dir(root)
    assert resolved.is_ok
    leases_root = resolved.danger_ok
    leases_root.mkdir(parents=True, exist_ok=True)
    record = _LeaseRecord(
        ticket_id=ticket_id,
        scope=(),
        worktree=str(worktree),
        branch="main",
        recorded_at="2026-07-22T00:00:00+00:00",
    )
    (leases_root / f"{ticket_id}.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


def _make_done_ticket(root: Path) -> None:
    """Create and close one ticket so archive has something to move."""
    ticket_run(
        AppConfig(
            ticket_command="new",
            ticket_path=root,
            ticket_title="archive me",
            ticket_kind="docs",
            ticket_body="## Done report\n\nDone.\n",
        )
    )
    ticket_run(AppConfig(ticket_command="start", ticket_path=root, ticket_id="T-0001"))
    ticket_run(
        AppConfig(
            ticket_command="close",
            ticket_path=root,
            ticket_id="T-0001",
            ticket_evidence_cmd="true",
        )
    )


class TestTicketArchiveForceCLI:
    """T-0810: `frob ticket archive [--force]` end to end through
    `AppConfig`/`ticket_run`, not just the library function."""

    def test_refuses_without_force_when_a_live_lease_exists(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI.test_refuses_without_force_when_a_live_lease_exists  # noqa: E501
        root = _repo(tmp_path)
        _make_done_ticket(root)
        # T-0001 itself -- the ticket archive would move -- still holds a
        # live lease (T-0843: the guard now only cares about leases on
        # tickets actually being archived).
        _write_live_lease(root, "T-0001", root)

        cfg = AppConfig(ticket_command="archive", ticket_path=root)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket archive failed" in caplog.text

        active = load_active(root).danger_ok
        assert "T-0001" in active.tickets
        assert active.tickets["T-0001"].state == TicketState.DONE

    def test_force_overrides_the_live_lease_refusal(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI.test_force_overrides_the_live_lease_refusal  # noqa: E501
        root = _repo(tmp_path)
        _make_done_ticket(root)
        _write_live_lease(root, "T-0001", root)

        cfg = AppConfig(ticket_command="archive", ticket_path=root, ticket_force=True)
        with caplog.at_level("INFO"):
            ticket_run(cfg)

        assert "archived 1 ticket(s)" in caplog.text
        assert "overriding 1 live cross-worktree lease(s)" in caplog.text

        active = load_active(root).danger_ok
        assert "T-0001" not in active.tickets

    def test_force_with_no_live_leases_stays_quiet(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI.test_force_with_no_live_leases_stays_quiet  # noqa: E501
        root = _repo(tmp_path)
        _make_done_ticket(root)

        cfg = AppConfig(ticket_command="archive", ticket_path=root, ticket_force=True)
        with caplog.at_level("INFO"):
            ticket_run(cfg)

        assert "archived 1 ticket(s)" in caplog.text
        assert "overriding" not in caplog.text
