"""T-1914: `frob ticket land`'s internal "merge main into worktree" step
must not silently clobber a SIBLING ticket's already-recorded state.

Self-contained (not appended to `tests/test_ticket_land.py`) because that
file's `tests/test_ticket_land.py` path is under a standing scope lease
held by another in-progress ticket (T-1686) at the time this was written --
duplicating the small git-fixture helpers here rather than fighting that
lease.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, TicketSpec, TicketState, new_ticket, transition
from frob.tickets._land import (
    _assert_no_sibling_state_regression,
    _sibling_ticket_states,
    land,
)
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
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    """Init a fixture repo AND gitignore `.frob/` (mirrors
    `tests/test_ticket_land.py::_git_init` -- see its own docstring for why
    this matters for a blanket `git add -A` fixture)."""
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


def _seed_v2_ticket(
    root: Path, ticket_id: str, *, scope: tuple[str, ...] = ()
):
    """Write a fresh QUEUED ticket directly into v2-mode storage (mirrors
    `tests/test_ticket_land.py::_seed_v2_ticket`)."""
    ticket = _ticket_from_spec(ticket_id, _spec("Seed", scope=scope), ())
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept
    (mirrors `tests/test_ticket_land.py::_make_closeable`)."""
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
    committed source file (mirrors `tests/test_ticket_land.py::v2_repo`)."""
    main_repo = tmp_path / "v2main"
    _git_init(main_repo)
    _seed_v2_ticket(main_repo, "T-3000", scope=("src/seed.py",))
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init v2")
    return main_repo


# frob:ticket T-1914
class TestSiblingStateRegressionGuard:
    """`_sibling_ticket_states`/`_assert_no_sibling_state_regression`
    (T-1914) -- the general post-merge invariant `_land_merge_stage` now
    asserts right after its internal `_merge_main_into_worktree[_v2]`
    call, plus the real, end-to-end incident reproduction against
    `land()` itself."""

    # frob:tests tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_no_regression_when_sibling_state_only_improves_or_holds  # noqa: E501
    def test_no_regression_when_sibling_state_only_improves_or_holds(
        self, tmp_path: Path
    ) -> None:
        _git_init(tmp_path)
        _seed_v2_ticket(tmp_path, "T-1000")
        _commit_all(tmp_path, "seed")
        pre = _sibling_ticket_states(tmp_path, landing_id="T-9999")
        assert pre == {"T-1000": TicketState.QUEUED.value}

        # A hold (no change at all) is never a regression.
        assert _assert_no_sibling_state_regression(tmp_path, "T-9999", pre) == ()

        # An improvement (queued -> done) is never a regression either.
        loaded = load_all(tmp_path)
        ticket = loaded.danger_ok["T-1000"]
        assert write_ticket(
            tmp_path,
            ticket.model_copy(
                update={
                    "state": TicketState.DONE,
                    "evidence": ("tests/test_x.py::test_ok",),
                    "body": ticket.body + "\n## Done report\n\nevidence attached\n",
                }
            ),
        ).is_ok
        assert _assert_no_sibling_state_regression(tmp_path, "T-9999", pre) == ()

    # frob:tests tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_regressed_sibling_is_detected_by_rank_comparison  # noqa: E501
    def test_regressed_sibling_is_detected_by_rank_comparison(
        self, tmp_path: Path
    ) -> None:
        _git_init(tmp_path)
        _seed_v2_ticket(tmp_path, "T-1000")
        _make_closeable(tmp_path, "T-1000")
        assert transition(tmp_path, "T-1000", TicketState.DONE).is_ok
        _commit_all(tmp_path, "close T-1000")
        pre = _sibling_ticket_states(tmp_path, landing_id="T-9999")
        assert pre == {"T-1000": TicketState.DONE.value}

        # Simulate the incident: something (an auto-resolved conflict
        # taking main's side, or an equivalent overwrite) reverts the
        # sibling's on-disk state back to queued.
        loaded = load_all(tmp_path)
        ticket = loaded.danger_ok["T-1000"]
        assert write_ticket(
            tmp_path, ticket.model_copy(update={"state": TicketState.QUEUED})
        ).is_ok

        regressed = _assert_no_sibling_state_regression(tmp_path, "T-9999", pre)
        assert regressed == ("T-1000",)

    # frob:tests tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_pre_fix_shape_would_have_silently_reverted_sibling  # noqa: E501
    def test_pre_fix_shape_would_have_silently_reverted_sibling(
        self, v2_repo: Path
    ) -> None:
        # T-1914: the real incident's own shape, end to end through
        # `land()`. A worktree closes SIBLING ticket S (state -> done,
        # a Done report attached) while landing an unrelated ticket L in
        # the SAME worktree -- the standing dispatch policy of one series
        # worktree per agent. Meanwhile main independently retitles S (S's
        # title is the SAME line both sides touch, so S's
        # `tickets/S/ticket.md` genuinely conflicts when land's internal
        # `_merge_main_into_worktree_v2` merges main into the worktree).
        # Before the T-1914 fix, `_auto_resolve_out_of_scope_conflicts(
        # keep="theirs")` blindly took main's ENTIRE file for any conflict
        # outside the landing ticket's own scope -- including S's own
        # directory -- silently discarding the worktree's `done` edit
        # along with the title conflict it was actually trying to
        # resolve, with no error surfaced anywhere. `land()` must now
        # refuse instead of committing over the lost sibling state.
        sibling = _seed_v2_ticket(v2_repo, "T-3010", scope=("src/sibling.py",))
        assert sibling.id == "T-3010"
        _commit_all(v2_repo, "main gains sibling v2 ticket T-3010")

        wt = v2_repo.parent / "wt-v2-sibling"
        _run(["git", "worktree", "add", "-b", "feature-v2-sibling", str(wt)], v2_repo)

        # Worktree lands ticket L (unrelated scope) ...
        created = new_ticket(wt, _spec("Land L", scope=("src/widget.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "widget.py").write_text("# widget\n")

        # ... and, in the SAME worktree, closes sibling S, retitling it
        # too (the same field main will independently retitle below --
        # the real conflict trigger).
        wt_sibling = load_all(wt).danger_ok["T-3010"]
        wt_sibling = wt_sibling.model_copy(
            update={
                "state": TicketState.DONE,
                "title": "Sibling closed by worktree",
                "evidence": ("tests/test_x.py::test_ok",),
                "body": wt_sibling.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, wt_sibling).is_ok
        _commit_all(wt, "worktree closes sibling T-3010 and lands L")

        # Main independently retitles the SAME sibling ticket's SAME
        # field, after the branch point -- a genuine same-line textual
        # conflict on tickets/T-3010/ticket.md, still QUEUED on main.
        main_sibling = load_all(v2_repo).danger_ok["T-3010"]
        assert write_ticket(
            v2_repo,
            main_sibling.model_copy(update={"title": "Sibling retitled by main"}),
        ).is_ok
        _commit_all(v2_repo, "main retitles sibling T-3010")

        result = land(v2_repo, landing_id, wt, dry_run=False)
        assert result.is_err, (
            "land silently succeeded -- sibling T-3010's `done` close was "
            "clobbered back to main's stale `queued` copy (T-1914)"
        )
        assert result.danger_err == LandError.TerminalStateRegression

        # Refused before any commit -- neither L nor the sibling
        # regression made it onto main.
        landed = load_all(v2_repo)
        assert landed.is_ok
        assert landing_id not in landed.danger_ok
        assert landed.danger_ok["T-3010"].state == TicketState.QUEUED
