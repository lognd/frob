"""T-4498: `frob ticket land`'s internal "merge target into worktree" step
must never silently drop a capability declaration by taking the target
branch's side of a genuine textual conflict on `design/frob.strata` or
`docs/design/registry/capability-via-ratchet.lock.json`.

Measured incident (T-4492's land, worktree commit 0294ab436 vs merge
commit afcd60105): both files are NOT ticket-ledger files (only
`tickets.md`/`tickets-archive.md` go through the ledger splice driver), so
a conflict on the SAME via-list line landed in
`_auto_resolve_out_of_scope_conflicts`'s ordinary out-of-scope path and was
blindly resolved by `git checkout --theirs`, discarding the worktree's
freshly declared via-list entries and lock-file bump with no error
surfaced anywhere.

Self-contained (not appended to `tests/ticket_land_suite/test_land_core.py`)
following the `tests/unit/test_land_sibling_regression.py` precedent: a
fresh, minimal git-fixture harness here keeps this ticket's scope to
`_land_git_ops.py`/`_land.py` plus this one test file, matching that
file's own reasoning for staying self-contained rather than touching a
shared, leased suite module.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
from frob.tickets._land import land
from frob.tickets._models import LandError
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import _serialize_ticket, atomic_write, v2_ticket_path


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    """Init a fixture repo AND gitignore `.frob/` (mirrors
    `tests/unit/test_land_sibling_regression.py::_git_init`)."""
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
        title=title, kind=TicketKind.BUG, origin=Origin.AGENT, scope=scope
    )


def _seed_v2_ticket(root: Path, ticket_id: str, *, scope: tuple[str, ...] = ()):
    """Write a fresh QUEUED ticket directly into v2-mode storage (mirrors
    `tests/unit/test_land_sibling_regression.py::_seed_v2_ticket`)."""
    ticket = _ticket_from_spec(ticket_id, _spec("Seed", scope=scope), ())
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `land` will accept closing (mirrors
    `tests/unit/test_land_sibling_regression.py::_make_closeable`)."""
    from frob.tickets import TicketState, transition
    from frob.tickets._store import load_all, write_ticket

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
def v2_repo(tmp_path: Path) -> Path:
    """A main checkout in v2-mode storage, seeded with one ticket and a
    `design/frob.strata` file whose via-list line both sides will later
    edit (mirrors `tests/unit/test_land_sibling_regression.py::v2_repo`)."""
    main_repo = tmp_path / "v2main"
    _git_init(main_repo)
    _seed_v2_ticket(main_repo, "T-3000", scope=("src/seed.py",))
    (main_repo / "design").mkdir()
    (main_repo / "design" / "frob.strata").write_text(
        "testsuite:\n  exec: [tests/unit/test_a.py]\n"
    )
    (main_repo / "docs" / "design" / "registry").mkdir(parents=True)
    (
        main_repo / "docs" / "design" / "registry" / "capability-via-ratchet.lock.json"
    ).write_text('{"accepted_count": 100}\n')
    _commit_all(main_repo, "init v2")
    return main_repo


# frob:ticket T-4552
# frob:waive WIRE001 follow_up="T-4950" reason="test-only fixture helper (T-4552 DUP001 extraction), called by both TestCapabilityRatchetConflictRefused methods in this same file -- same shape as tests/unit/test_leases_staleness_perf.py's own _write_lease_for, no production caller expected"  # noqa: E501
def _seed_widget_worktree(
    v2_repo: Path, wt_name: str, branch: str, title: str, scope: tuple[str, ...]
) -> tuple[Path, str]:
    """DUP001 (T-4552): the setup shared by both
    `TestCapabilityRatchetConflictRefused` cases -- add a worktree, give
    it a throwaway `src/widget.py` so its ticket has an ordinary in-scope
    file, and register a closeable ticket for it. Returns `(wt, ticket_id)`
    so the caller can still write the file-under-conflict's content and
    commit it itself -- that part is the one thing that genuinely differs
    between the two cases."""
    wt = v2_repo.parent / wt_name
    _run(["git", "worktree", "add", "-b", branch, str(wt)], v2_repo)

    # Worktree ticket is scoped to src/widget.py -- it never legitimately
    # declares the capability-ratchet file "in scope" for THIS ticket,
    # mirroring the real T-4492 incident's shape.
    (wt / "src").mkdir(exist_ok=True)
    (wt / "src" / "widget.py").write_text("# widget\n")
    created = new_ticket(wt, _spec(title, scope=scope))
    assert created.is_ok
    tid = created.danger_ok.id
    _make_closeable(wt, tid)
    return wt, tid


# frob:ticket T-4552
class TestCapabilityRatchetConflictRefused:
    """A conflict on `design/frob.strata` or the capability-via-ratchet
    lock file must refuse the land (naming the file and both sides'
    tickets) rather than silently keeping the target branch's side."""

    # frob:tests tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused.test_conflicting_strata_via_list_refuses_instead_of_dropping  # noqa: E501
    def test_conflicting_strata_via_list_refuses_instead_of_dropping(
        self, v2_repo: Path
    ) -> None:
        wt, tid = _seed_widget_worktree(
            v2_repo, "wt-strata", "feature-strata", "Add widget", ("src/widget.py",)
        )
        (wt / "design" / "frob.strata").write_text(
            "testsuite:\n  exec: [tests/unit/test_a.py, tests/unit/test_worktree_new.py]\n"
        )
        _commit_all(wt, "worktree adds a via-list entry to design/frob.strata")

        # Main independently edits the SAME via-list line after the
        # worktree branched -- a genuine textual conflict.
        (v2_repo / "design" / "frob.strata").write_text(
            "testsuite:\n  exec: [tests/unit/test_a.py, tests/unit/test_main_new.py]\n"
        )
        _commit_all(v2_repo, "main adds a different via-list entry")

        result = land(v2_repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.MergeConflict

        # Refused, not silently landed: main's file is untouched and the
        # worktree's declaration was never dropped without a trace.
        status = _run(["git", "status", "--short"], v2_repo).stdout
        assert status == "" or "UU" not in status
        assert "test_main_new.py" in (v2_repo / "design" / "frob.strata").read_text()
        assert (
            "test_worktree_new.py"
            not in (v2_repo / "design" / "frob.strata").read_text()
        )

    # frob:tests tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused.test_conflicting_ratchet_lock_refuses_instead_of_dropping  # noqa: E501
    def test_conflicting_ratchet_lock_refuses_instead_of_dropping(
        self, v2_repo: Path
    ) -> None:
        wt, tid = _seed_widget_worktree(
            v2_repo, "wt-lock", "feature-lock", "Add widget 2", ("src/widget.py",)
        )
        lock_path = "docs/design/registry/capability-via-ratchet.lock.json"
        (wt / lock_path).write_text('{"accepted_count": 108}\n')
        _commit_all(wt, "worktree bumps the ratchet lock")

        (v2_repo / lock_path).write_text('{"accepted_count": 109}\n')
        _commit_all(v2_repo, "main bumps the ratchet lock differently")

        result = land(v2_repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.MergeConflict
        assert (v2_repo / lock_path).read_text() == '{"accepted_count": 109}\n'
