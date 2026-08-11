"""T-2105 (half 2 of T-2092): a duplicate ticket id created by a MERGE, not
an in-process race. T-2092 closed the allocator-lock half (two writers in
the SAME process/root racing on id allocation); this covers the field
incident's actual mechanism -- two DIFFERENT worktrees/roots each write a
real, distinct `tickets/<id>/ticket.md` for the SAME id, neither write
itself ever errors, and the collision only surfaces at `git merge`, where
the land machinery's own internal merge-main-into-worktree step used to
treat the other record as out-of-scope and silently keep main's side,
discarding the worktree's content entirely -- caught only by grepping
ticket CONTENT on main post-land, since the id itself looked fine.

Self-contained (mirrors `tests/unit/test_land_sibling_regression.py`'s own
git-fixture helpers) rather than appending to `tests/test_ticket_land.py`,
per that file's own precedent for avoiding a scope-lease collision on the
shared test file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, TicketSpec, TicketState, new_ticket, transition
from frob.tickets._land import land
from frob.tickets._land_git_ops import detect_duplicate_ticket_id_collisions
from frob.tickets._models import LandError
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import (
    _serialize_ticket,
    atomic_write,
    load_all,
    v2_ticket_path,
    write_ticket,
)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(cwd), check=True, capture_output=True, text=True)


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
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope)


def _seed_v2_ticket(root: Path, ticket_id: str, *, scope: tuple[str, ...] = ()):
    """Write a fresh QUEUED ticket directly into v2-mode storage (mirrors
    `tests/unit/test_land_sibling_regression.py::_seed_v2_ticket`)."""
    ticket = _ticket_from_spec(ticket_id, _spec("Seed", scope=scope), ())
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept
    (mirrors `tests/unit/test_land_sibling_regression.py::_make_closeable`)."""
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
    """A main checkout in v2-mode storage, seeded with one ticket and one
    committed source file (mirrors
    `tests/unit/test_land_sibling_regression.py::v2_repo`)."""
    main_repo = tmp_path / "v2main"
    _git_init(main_repo)
    _seed_v2_ticket(main_repo, "T-3000", scope=("src/seed.py",))
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init v2")
    return main_repo


# frob:ticket T-2105
class TestDetectDuplicateTicketIdCollisions:
    """`detect_duplicate_ticket_id_collisions` (T-2105) -- direct, content-
    aware comparison of two roots' `tickets/<id>/ticket.md` blobs, ahead of
    any `git merge`. This is the "ledger/history is inspected" detection
    half of the ticket: pointed at two roots that each hold a genuinely
    distinct record for the same id, it reports the collision by id
    rather than leaving it invisible until a merge resolves it one way or
    the other."""

    # frob:tests tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.test_flags_id_with_genuinely_different_content_on_both_sides  # noqa: E501
    def test_flags_id_with_genuinely_different_content_on_both_sides(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "root"
        worktree = tmp_path / "worktree"
        _git_init(root)
        (root / "README.md").write_text("seed\n")
        _commit_all(root, "seed (no T-4000 on either side yet)")

        _run(["git", "clone", "-q", str(root), str(worktree)], tmp_path)
        _run(["git", "-C", str(worktree), "checkout", "-q", "-b", "feature"], tmp_path)

        # AFTER the two sides diverge, root independently allocates T-4000
        # for one ticket ...
        seeded = _seed_v2_ticket(root, "T-4000", scope=("src/a.py",))
        seeded = seeded.model_copy(update={"title": "Filed directly on main"})
        assert write_ticket(root, seeded).is_ok
        _commit_all(root, "root independently writes T-4000")

        # ... while the worktree independently allocates the SAME id for
        # an entirely UNRELATED record (simulating a second, concurrent
        # writer that happened to land on the same id).
        colliding = _seed_v2_ticket(
            worktree, "T-4000", scope=("src/completely/different/path.py",)
        )
        colliding = colliding.model_copy(update={"title": "A totally different ticket"})
        assert write_ticket(worktree, colliding).is_ok
        _commit_all(worktree, "worktree independently writes a different T-4000")

        found = detect_duplicate_ticket_id_collisions(worktree, root, "T-9999", "main")
        assert found == frozenset({"T-4000"})

    # frob:tests tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.test_ignores_the_landing_tickets_own_id  # noqa: E501
    def test_ignores_the_landing_tickets_own_id(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        worktree = tmp_path / "worktree"
        _git_init(root)
        _seed_v2_ticket(root, "T-4001", scope=("src/a.py",))
        _commit_all(root, "root writes T-4001")

        _run(["git", "clone", "-q", str(root), str(worktree)], tmp_path)
        _run(["git", "-C", str(worktree), "checkout", "-q", "-b", "feature"], tmp_path)

        # The worktree's OWN change to the ticket actually being landed --
        # this is the whole point of landing it, never a collision.
        mine = load_all(worktree).danger_ok["T-4001"]
        mine = mine.model_copy(update={"title": "Retitled by its own landing worktree"})
        assert write_ticket(worktree, mine).is_ok
        _commit_all(worktree, "worktree retitles the ticket it is landing")

        found = detect_duplicate_ticket_id_collisions(worktree, root, "T-4001", "main")
        assert found == frozenset()

    # frob:tests tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.test_ignores_identical_content_on_both_sides  # noqa: E501
    def test_ignores_identical_content_on_both_sides(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        worktree = tmp_path / "worktree"
        _git_init(root)
        _seed_v2_ticket(root, "T-4002", scope=("src/a.py",))
        _commit_all(root, "root writes T-4002")
        _run(["git", "clone", "-q", str(root), str(worktree)], tmp_path)

        found = detect_duplicate_ticket_id_collisions(worktree, root, "T-9999", "main")
        assert found == frozenset()

    # frob:tests tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.test_ignores_an_id_that_already_existed_at_the_merge_base  # noqa: E501
    def test_ignores_an_id_that_already_existed_at_the_merge_base(
        self, tmp_path: Path
    ) -> None:
        """T-1914's own shape (a sibling ticket that existed BEFORE the
        two sides diverged, then edited differently by each) must NOT be
        misread as a T-2105 duplicate-id collision -- that is an ordinary
        edit conflict on a pre-existing record, not two independent id
        allocations landing on the same value."""
        root = tmp_path / "root"
        worktree = tmp_path / "worktree"
        _git_init(root)
        _seed_v2_ticket(root, "T-4003", scope=("src/a.py",))
        _commit_all(root, "root writes T-4003 (the shared base)")

        _run(["git", "clone", "-q", str(root), str(worktree)], tmp_path)
        _run(["git", "-C", str(worktree), "checkout", "-q", "-b", "feature"], tmp_path)

        # Worktree retitles T-4003 after the branch point.
        wt_sibling = load_all(worktree).danger_ok["T-4003"]
        wt_sibling = wt_sibling.model_copy(update={"title": "Retitled by worktree"})
        assert write_ticket(worktree, wt_sibling).is_ok
        _commit_all(worktree, "worktree retitles T-4003")

        # Main independently retitles the SAME pre-existing ticket,
        # differently.
        main_sibling = load_all(root).danger_ok["T-4003"]
        main_sibling = main_sibling.model_copy(update={"title": "Retitled by main"})
        assert write_ticket(root, main_sibling).is_ok
        _commit_all(root, "main retitles T-4003 differently")

        found = detect_duplicate_ticket_id_collisions(worktree, root, "T-9999", "main")
        assert found == frozenset()


# frob:ticket T-2105
class TestLandRefusesOnDuplicateTicketIdCollision:
    """The real incident, end to end through `land()`: a landing worktree
    and main each independently hold a genuinely different record at the
    same ticket id (simulating the T-2083/T-2090 field shape -- a
    finalized draft on one side, a direct `frob ticket new` on the other).
    Before T-2105, `land()`'s internal merge-main-into-worktree step
    treated the colliding id's `ticket.md` as out of the landing ticket's
    scope and silently kept whichever side `_auto_resolve_out_of_scope_
    conflicts` was told to keep, discarding the other's content with no
    error. It must now refuse instead."""

    # frob:tests tests/unit/test_land_duplicate_ticket_id.py::TestLandRefusesOnDuplicateTicketIdCollision.test_land_refuses_instead_of_silently_discarding_a_colliding_record  # noqa: E501
    def test_land_refuses_instead_of_silently_discarding_a_colliding_record(
        self, v2_repo: Path
    ) -> None:
        wt = v2_repo.parent / "wt-dup-id"
        _run(["git", "worktree", "add", "-b", "feature-dup-id", str(wt)], v2_repo)

        # Worktree lands ticket L (unrelated scope) ...
        created = new_ticket(wt, _spec("Land L", scope=("src/widget.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "widget.py").write_text("# widget\n")

        # ... and, in the SAME worktree, ALSO independently allocates a
        # brand-new ticket id T-4100 (e.g. a finalized draft during this
        # same land).
        colliding_a = _seed_v2_ticket(wt, "T-4100", scope=("src/from-worktree.py",))
        colliding_a = colliding_a.model_copy(update={"title": "Filed from the worktree"})
        assert write_ticket(wt, colliding_a).is_ok
        _commit_all(wt, "worktree lands L and files T-4100")

        # Main independently allocates the SAME id T-4100, for a totally
        # different, unrelated ticket (a direct `frob ticket new` on main
        # racing the worktree's own draft-finalize -- the real incident's
        # mechanism).
        colliding_b = _seed_v2_ticket(
            v2_repo, "T-4100", scope=("src/from-main-instead.py",)
        )
        colliding_b = colliding_b.model_copy(update={"title": "Filed directly on main"})
        assert write_ticket(v2_repo, colliding_b).is_ok
        _commit_all(v2_repo, "main independently files a different T-4100")

        result = land(v2_repo, landing_id, wt, dry_run=False)
        assert result.is_err, (
            "land silently succeeded -- one of the two T-4100 records was "
            "discarded without a trace (T-2105)"
        )
        assert result.danger_err == LandError.MergeConflict

        # Refused before any commit -- L never landed, and main's own
        # T-4100 record is untouched (still "Filed directly on main", not
        # silently overwritten by the worktree's).
        landed = load_all(v2_repo)
        assert landed.is_ok
        assert landing_id not in landed.danger_ok
        assert landed.danger_ok["T-4100"].title == "Filed directly on main"
