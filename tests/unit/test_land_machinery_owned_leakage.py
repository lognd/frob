"""T-2121: `_check_cross_ticket_leakage` must never treat a
machinery-owned path (written exclusively by land/sweep machinery, never
by a ticket's own hand) as "claimed" by any ticket's declared or
live-lease scope.

The real incident: `rapid-debt.jsonl` (T-1699's deferred-debt append) is
touched by essentially every rapid land via the detached post-land sweep.
An UNRELATED open ticket (T-2049 in the field) happened to declare it in
its own scope, and every OTHER rapid land in the fleet started refusing
with `CrossTicketLeakage` over a file its own author never touched by
hand -- the shared-file class T-1780 already names for
`docs/modules/tickets.md`, but worse here because the collision is
between a DECLARED scope and a file only MACHINERY writes, not two
tickets' own deliberate work.

v2-mode fixtures throughout (mirrors `tests/unit/test_land_duplicate_
ticket_id.py`/`tests/unit/test_land_sibling_regression.py`'s own
precedent): the sibling ticket is seeded DIRECTLY as a real, non-draft id
(`_seed_v2_ticket`) rather than through `new_ticket` on a non-default
branch, which mints a `T-draft-...` provisional id and would otherwise
drag this test into `land()`'s unrelated sibling-draft-finalize path.

Self-contained rather than appending to `tests/unit/test_land_cross_
ticket_leakage.py`, which was under a live scope lease (T-2120) at the
time this was written.
"""

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
    """Write a fresh QUEUED ticket directly into v2-mode storage, a REAL
    (never draft) id (mirrors `tests/unit/test_land_duplicate_ticket_id.
    py::_seed_v2_ticket`)."""
    ticket = _ticket_from_spec(ticket_id, _spec("Seed", scope=scope), ())
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept
    (mirrors the same helper duplicated across every land test module in
    this suite, per that duplication's own standing DUP001 waiver)."""
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
    """A main checkout in v2-mode storage, seeded with a `rapid-debt.jsonl`
    already tracked (mirrors `tests/unit/test_land_duplicate_ticket_id.
    py::v2_repo`)."""
    main_repo = tmp_path / "v2main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    (main_repo / "rapid-debt.jsonl").write_text(
        '{"commit": "deadbeef", "skipped": "x", "ticket": "T-0000"}\n'
    )
    _commit_all(main_repo, "init v2")
    return main_repo


# frob:ticket T-2121
class TestMachineryOwnedLeakageExemption:
    """`_machinery_owned_leakage_exempt_paths` (T-2121) -- a
    machinery-appended file's OWN write is never eligible to be "claimed"
    by any ticket's declared scope for `_check_cross_ticket_leakage`
    purposes, no matter what an unrelated sibling ticket happens to
    declare."""

    # frob:tests tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption.test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it  # noqa: E501
    def test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it(
        self, v2_repo: Path
    ) -> None:
        # T-2121 (MUST FAIL on the pre-fix code): T-2049's real shape --
        # an UNRELATED, genuinely IN_PROGRESS sibling declares
        # `rapid-debt.jsonl` in its own scope, in a DIFFERENT worktree
        # than the one landing. `rapid-debt.jsonl` must never be
        # eligible to be "claimed" for leakage purposes, regardless.
        sibling_id = "T-4200"
        _seed_v2_ticket(v2_repo, sibling_id, scope=("rapid-debt.jsonl",))
        _commit_all(v2_repo, f"seed {sibling_id}, declaring rapid-debt.jsonl")

        wt_sibling = v2_repo.parent / "wt-sibling"
        _run(
            ["git", "worktree", "add", "-b", "sibling-declares-debt", str(wt_sibling)],
            v2_repo,
        )
        assert transition(wt_sibling, sibling_id, TicketState.PLANNED).is_ok
        assert transition(wt_sibling, sibling_id, TicketState.IN_PROGRESS).is_ok
        _commit_all(wt_sibling, f"{sibling_id}: start")

        # Landing worktree, forked from ROOT (v2_repo) -- already knows
        # about the sibling's declared scope (seeded there directly,
        # step one above) but never sees its IN_PROGRESS transition
        # (that only happened in wt_sibling) -- `is_effectively_in_
        # progress`'s live-lease check (T-1999) is what still counts it
        # as genuinely open, exactly the real incident's shape.
        wt_land = v2_repo.parent / "wt-land"
        _run(["git", "worktree", "add", "-b", "independent-fix", str(wt_land)], v2_repo)
        landing = new_ticket(
            wt_land,
            _spec("Independent fix, unrelated to the debt log", scope=("src/fix.py",)),
        )
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt_land, landing_id)
        (wt_land / "src").mkdir(exist_ok=True)
        (wt_land / "src" / "fix.py").write_text("# independent fix\n")
        # The machinery-appended write itself: a rapid-land-shaped debt
        # line, exactly like `record_rapid_debt` would append.
        with (wt_land / "rapid-debt.jsonl").open("a") as fh:
            fh.write(
                '{"commit": "cafef00d", "skipped": "y", "ticket": "'
                + landing_id
                + '"}\n'
            )
        _commit_all(wt_land, f"{landing_id}: independent fix + rapid-debt append")

        result = land(v2_repo, landing_id, wt_land, dry_run=False)

        assert result.is_ok, (
            "land refused over a machinery-owned rapid-debt.jsonl append "
            f"merely declared by an unrelated sibling (T-2121): "
            f"{result.err if result.is_err else None}"
        )
        assert (v2_repo / "src" / "fix.py").exists()
