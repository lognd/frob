"""T-1618: `frob.tickets._land._check_already_landed` -- landing a ticket
whose own declared scope has no changes relative to main is a distinct,
self-explaining outcome (`LandError.AlreadyLandedOnMain`), not a confusing
fall-through into whatever the normal land path does with an empty
changeset. Opt-in via `land(..., check_already_landed=True)` / `frob
ticket land --check-already-landed` -- see `_land_precheck`'s own
docstring for why this stays off by default (measured against this
repo's own fixture population, an empty scope-diff is ALSO the ordinary
shape of a docs-only/ledger-only/Done-report-only ticket, so refusing by
default would trade one false-positive class for a worse one). Real git
fixture repos throughout, matching
`tests/unit/test_land_cross_ticket_leakage.py`'s own style."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import LandError
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init/commit boilerplate already \
# duplicated verbatim across several land/ticket test modules -- see \
# tests/unit/test_land_cross_ticket_leakage.py's own identical waiver for the same \
# rationale"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


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
    """A main checkout with an initialized ledger and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


# frob:ticket T-1618
class TestAlreadyLandedOnMain:
    """`_check_already_landed` -- an empty diff inside the ticket's own
    scope refuses with a distinct, self-explaining outcome instead of
    falling through to a confusing generic failure."""

    def test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"  # noqa: E501
        # Content matching the ticket's OWN declared scope already exists
        # on main from before this worktree was even cut -- the exact
        # "sibling's land already carried this one's content" shape.
        (repo / "src" / "already-there.py").write_text("# pre-existing content\n")
        _commit_all(repo, "seed: content already on main")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-empty", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Already landed", scope=("src/already-there.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Committed on the branch, but touching a DIFFERENT file than the
        # ticket's own declared scope -- e.g. only its own ledger record
        # moved; no actual change to src/already-there.py on this branch.
        (wt / "src" / "unrelated.py").write_text("# unrelated bookkeeping\n")
        _commit_all(wt, f"{tid}: ledger-only, no scope change")

        with caplog.at_level("WARNING"):
            result = land(repo, tid, wt, dry_run=False, check_already_landed=True)

        assert result.is_err
        assert result.danger_err == LandError.AlreadyLandedOnMain
        assert "frob ticket close" in caplog.text
        assert tid in caplog.text

    def test_no_op_when_the_ticket_has_real_changes_in_its_own_scope(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-real", str(wt)], repo)
        created = new_ticket(wt, _spec("Real work", scope=("src/fix.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "fix.py").write_text("# real change\n")
        _commit_all(wt, f"{tid}: real change")

        result = land(repo, tid, wt, dry_run=False, check_already_landed=True)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    def test_no_op_when_the_ticket_declares_no_scope_at_all(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-scopeless", str(wt)], repo)
        created = new_ticket(wt, _spec("No scope declared", scope=()))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "fix.py").write_text("# change under an empty scope\n")
        _commit_all(wt, f"{tid}: change, no declared scope")

        result = land(repo, tid, wt, dry_run=False, check_already_landed=True)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()
