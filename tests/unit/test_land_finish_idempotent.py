"""T-2108: `frob ticket land <id> --finish` on a ticket ALREADY terminal
(done/dropped) on `main` must skip the full land pipeline entirely --
never spawn `_land_core`'s merge+BUG002-repro re-verification, which
refuses on a designated repro test that now genuinely PASSES against
main's new parent (the fix is already there). `--finish` on an
already-landed ticket is pure cleanup: worktree removal (and branch
deletion for `--retire-on-proof`), nothing else.

Real git fixture repos throughout, matching `tests/unit/
test_land_already_landed.py`'s own style and `_seed_done_on_main`
pattern -- a genuinely closed ticket record, not a hand-typed fixture."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._land_cmd import (
    _finish_only_if_already_landed,
    _ticket_terminal_state_on_main,
)
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init/commit boilerplate already \
# duplicated verbatim across several land/ticket test modules -- see \
# tests/unit/test_land_already_landed.py's own identical waiver for the same rationale"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


def _make_closeable(root: Path, ticket_id: str) -> None:
    assert transition(root, ticket_id, TicketState.PLANNED).is_ok
    assert transition(root, ticket_id, TicketState.IN_PROGRESS).is_ok
    loaded = load_all(root)
    ticket = loaded.danger_ok[ticket_id]
    ticket = ticket.model_copy(
        update={
            "evidence": ("tests/test_x.py::test_ok",),
            "body": ticket.body + "\n## Done report\n\nevidence attached\n",
        }
    )
    assert write_ticket(root, ticket).is_ok


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    _commit_all(main_repo, "init")
    return main_repo


class TestTicketTerminalStateOnMain:
    """`_ticket_terminal_state_on_main` -- the one-ledger-read primitive
    `_finish_only_if_already_landed` gates on."""

    def test_done_ticket_returns_its_state(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain.test_done_ticket_returns_its_state  # noqa: E501
        created = new_ticket(repo, _spec("Already closed"))
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        assert transition(repo, tid, TicketState.DONE).is_ok

        assert _ticket_terminal_state_on_main(repo, tid) == "done"

    def test_in_progress_ticket_returns_none(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain.test_in_progress_ticket_returns_none  # noqa: E501
        created = new_ticket(repo, _spec("Still working"))
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        assert _ticket_terminal_state_on_main(repo, tid) is None

    def test_unknown_ticket_id_returns_none(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain.test_unknown_ticket_id_returns_none  # noqa: E501
        assert _ticket_terminal_state_on_main(repo, "T-9999") is None


class TestFinishOnlyIfAlreadyLanded:
    """`_finish_only_if_already_landed` -- the `_land` pre-check T-2108
    adds: skip `_land_core` entirely (never touch BUG002) when
    `cfg.ticket_id` is already terminal on `main`, running pure cleanup
    instead."""

    def test_terminal_on_main_skips_land_core_and_cleans_up(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded.test_terminal_on_main_skips_land_core_and_cleans_up  # noqa: E501
        created = new_ticket(repo, _spec("Landed already"))
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        assert transition(repo, tid, TicketState.DONE).is_ok

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-finish", str(wt)], repo)

        import frob.app.ticket_runner._land_cmd as land_cmd_mod

        finish_calls: list[Path] = []
        monkeypatch.setattr(
            land_cmd_mod,
            "_finish_worktree",
            lambda root, worktree, ticket_id, **kw: finish_calls.append(worktree),
        )
        land_core_calls: list[str] = []
        monkeypatch.setattr(
            land_cmd_mod,
            "_land_core",
            lambda root, cfg: land_core_calls.append(cfg.ticket_id),
        )

        cfg = AppConfig(ticket_id=tid, ticket_land_finish=True, ticket_dry_run=False)
        handled = _finish_only_if_already_landed(repo, wt, cfg)

        assert handled is True
        assert finish_calls == [wt]
        # The whole point: _land_core (which would spawn the full
        # merge+BUG002-repro re-verification) is never called.
        assert land_core_calls == []

    def test_non_terminal_on_main_runs_the_normal_land(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded.test_non_terminal_on_main_runs_the_normal_land  # noqa: E501
        created = new_ticket(repo, _spec("Still needs to land"))
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-normal", str(wt)], repo)

        import frob.app.ticket_runner._land_cmd as land_cmd_mod

        finish_calls: list[Path] = []
        monkeypatch.setattr(
            land_cmd_mod,
            "_finish_worktree",
            lambda root, worktree, ticket_id, **kw: finish_calls.append(worktree),
        )

        cfg = AppConfig(ticket_id=tid, ticket_land_finish=True, ticket_dry_run=False)
        handled = _finish_only_if_already_landed(repo, wt, cfg)

        assert handled is False
        # No cleanup side effect either -- the caller proceeds to the
        # normal `_land_core` path exactly as before this fix.
        assert finish_calls == []
