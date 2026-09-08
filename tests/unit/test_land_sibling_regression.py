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

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import (
    _assert_no_sibling_state_regression,
    _reopen_log_entries,
    _sibling_reopen_log_signatures,
    _sibling_ticket_states,
    land,
)
from frob.tickets._models import LandError
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._reporting import reopen_ticket
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
    `tests/ticket_land_suite/conftest.py::_git_init` -- see its own docstring for why
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


def _seed_v2_ticket(root: Path, ticket_id: str, *, scope: tuple[str, ...] = ()):
    """Write a fresh QUEUED ticket directly into v2-mode storage (mirrors
    `tests/ticket_land_suite/conftest.py::_seed_v2_ticket`)."""
    ticket = _ticket_from_spec(ticket_id, _spec("Seed", scope=scope), ())
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept
    (mirrors `tests/ticket_land_suite/conftest.py::_make_closeable`)."""
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
    committed source file (mirrors `tests/ticket_land_suite/conftest.py::v2_repo`)."""
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

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_\
    # no_regression_when_sibling_state_only_improves_or_holds
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

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_\
    # regressed_sibling_is_detected_by_rank_comparison
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

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_\
    # pre_fix_shape_would_have_silently_reverted_sibling
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


# frob:ticket T-2289
class TestSelfConflictAutoResolve:
    """T-2289: a land whose ONLY divergent ledger row is the LANDING
    ticket's own -- never a sibling's -- must resolve automatically by
    keeping the newer state (playbook section 10), not refuse. Before the
    fix, `_merge_main_into_worktree_v2` treats a conflict on the landing
    ticket's own `tickets/<id>/ticket.md` as an ordinary in-scope conflict
    (AC3 of the v2 merge story) and leaves it for manual resolution
    (`LandError.MergeConflict`) even when the conflict is exactly the
    mechanical "worktree progressed further than main's stale copy" shape
    this ticket exists to auto-resolve."""

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve.test_self\
    # _conflict_lands_by_keeping_newer_state
    def test_self_conflict_lands_by_keeping_newer_state(self, v2_repo: Path) -> None:
        created = new_ticket(v2_repo, _spec("Land L", scope=("src/widget.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id

        wt = v2_repo.parent / "wt-self-conflict"
        _run(
            ["git", "worktree", "add", "-b", "feature-self-conflict", str(wt)], v2_repo
        )

        # Worktree makes real progress on the LANDING ticket itself:
        # queued -> planned -> in_progress, plus evidence + a Done report.
        _make_closeable(wt, landing_id)
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "widget.py").write_text("# widget\n")
        _commit_all(wt, "worktree advances landing ticket L")

        # Main independently, and more shallowly, advances the SAME
        # ticket's SAME `state:` line to `planned` (e.g. an auto-plan
        # sweep) via a raw git-level edit -- bypassing the ownership guard
        # the way frob's own internal bookkeeping commits (rapid-sweep
        # debt rows, land-commit recording) write directly rather than
        # through the leased-store API -- reproducing the exact same-line
        # conflict a genuinely concurrent write to the landing ticket's
        # own row would leave behind.
        tpath = v2_ticket_path(v2_repo, landing_id)
        text = tpath.read_text().replace("state: queued", "state: planned", 1)
        assert "state: planned" in text
        tpath.write_text(text)
        _commit_all(v2_repo, "main auto-plans the landing ticket (raw)")

        result = land(v2_repo, landing_id, wt, dry_run=False)
        assert result.is_ok, (
            f"land refused a pure self-conflict on {landing_id}'s own row "
            f"-- {result.danger_err if result.is_err else None} "
            "(T-2289: this must auto-resolve by keeping the newer state, "
            "never require manual resolution or misfire the T-1914 "
            "sibling-state-regression guard against the landing ticket "
            "itself)"
        )

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestSelfConflictAutoResolve.test_genu\
    # ine_sibling_conflict_still_refuses
    def test_genuine_sibling_conflict_still_refuses(self, v2_repo: Path) -> None:
        """The exact `test_pre_fix_shape_would_have_silently_reverted_
        sibling` shape, restated here to pin down that T-2289's self-
        conflict auto-resolve is scoped to the LANDING ticket's own id
        only -- a GENUINE sibling regression must still refuse exactly as
        before (must-still-fail half of T-2289's acceptance criteria)."""
        sibling = _seed_v2_ticket(v2_repo, "T-3020", scope=("src/sibling2.py",))
        assert sibling.id == "T-3020"
        _commit_all(v2_repo, "main gains sibling v2 ticket T-3020")

        wt = v2_repo.parent / "wt-genuine-sibling"
        _run(
            ["git", "worktree", "add", "-b", "feature-genuine-sibling", str(wt)],
            v2_repo,
        )

        created = new_ticket(wt, _spec("Land M", scope=("src/gadget.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "gadget.py").write_text("# gadget\n")

        wt_sibling = load_all(wt).danger_ok["T-3020"]
        wt_sibling = wt_sibling.model_copy(
            update={
                "state": TicketState.DONE,
                "title": "Sibling closed by worktree (M)",
                "evidence": ("tests/test_x.py::test_ok",),
                "body": wt_sibling.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, wt_sibling).is_ok
        _commit_all(wt, "worktree closes sibling T-3020 and lands M")

        main_sibling = load_all(v2_repo).danger_ok["T-3020"]
        assert write_ticket(
            v2_repo,
            main_sibling.model_copy(
                update={"title": "Sibling T-3020 retitled by main"}
            ),
        ).is_ok
        _commit_all(v2_repo, "main retitles sibling T-3020")

        result = land(v2_repo, landing_id, wt, dry_run=False)
        assert result.is_err, (
            "T-2289's self-conflict fix over-widened and let a GENUINE "
            "sibling regression through -- the T-1914 guard must still "
            "refuse this"
        )
        assert result.danger_err == LandError.TerminalStateRegression

        landed = load_all(v2_repo)
        assert landed.is_ok
        assert landing_id not in landed.danger_ok
        assert landed.danger_ok["T-3020"].state == TicketState.QUEUED


# frob:ticket T-4287
class TestAuditedReopenEscape:
    """T-4287: `_assert_no_sibling_state_regression` must not refuse a
    land whose only "regression" is a sibling ticket a `frob ticket
    reopen --reason TEXT` deliberately moved back to QUEUED on `main`
    after this worktree forked -- while still refusing an accidental
    hand-resolved-merge resurrection with no reopen record at all."""

    # frob:ticket T-4287
    def test_no_reopen_log_returns_empty(self) -> None:
        assert _reopen_log_entries("## Done report\n\nsomething\n") == ()

    # frob:ticket T-4287
    def test_new_reopen_log_entry_is_the_signature(self) -> None:
        body = (
            "## Reopen log\n"
            "- 2026-09-08: falsely closed, no code reached main\n"
            "## Done report\n"
            "evidence attached\n"
        )
        assert _reopen_log_entries(body) == (
            "- 2026-09-08: falsely closed, no code reached main",
        )

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestAuditedReopenEscape.test_audited_\
    # reopen_is_not_flagged_as_regression
    # frob:ticket T-4287
    def test_audited_reopen_is_not_flagged_as_regression(self, v2_repo: Path) -> None:
        sibling = _seed_v2_ticket(v2_repo, "T-3030", scope=("src/sibling2.py",))
        assert sibling.id == "T-3030"
        _make_closeable(v2_repo, "T-3030")
        assert transition(v2_repo, "T-3030", TicketState.DONE).is_ok
        _commit_all(v2_repo, "close sibling T-3030")

        wt = v2_repo.parent / "wt-audited-reopen"
        _run(
            ["git", "worktree", "add", "-b", "feature-audited-reopen", str(wt)], v2_repo
        )

        # Worktree lands unrelated ticket L, forked while T-3030 was DONE
        # and carries no reopen-log entry of its own.
        created = new_ticket(wt, _spec("Land N", scope=("src/dial.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "dial.py").write_text("# dial\n")
        _commit_all(wt, "worktree lands N")

        # Main reopens the sibling through the AUDITED verb after the
        # worktree forked.
        reopened = reopen_ticket(v2_repo, "T-3030", "T-4287: false close, redo")
        assert reopened.is_ok
        _commit_all(v2_repo, "reopen sibling T-3030 (T-4287)")

        result = land(v2_repo, landing_id, wt, dry_run=False)
        assert result.is_ok, (
            "an audited `frob ticket reopen` on a sibling ticket must not "
            f"strand this land (T-4287); got {result}"
        )
        landed = load_all(v2_repo)
        assert landed.is_ok
        assert landed.danger_ok["T-3030"].state == TicketState.QUEUED

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestAuditedReopenEscape.test_hand_res\
    # urrection_without_reopen_log_is_still_refused
    # frob:ticket T-4287
    def test_hand_resurrection_without_reopen_log_is_still_refused(
        self, v2_repo: Path
    ) -> None:
        sibling = _seed_v2_ticket(v2_repo, "T-3031", scope=("src/sibling3.py",))
        assert sibling.id == "T-3031"
        _make_closeable(v2_repo, "T-3031")
        assert transition(v2_repo, "T-3031", TicketState.DONE).is_ok
        _commit_all(v2_repo, "close sibling T-3031")

        wt = v2_repo.parent / "wt-hand-resurrection"
        _run(
            ["git", "worktree", "add", "-b", "feature-hand-resurrection", str(wt)],
            v2_repo,
        )
        created = new_ticket(wt, _spec("Land O", scope=("src/knob.py",)))
        assert created.is_ok
        landing_id = created.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "knob.py").write_text("# knob\n")
        _commit_all(wt, "worktree lands O")

        # Main resurrects the sibling by a raw state edit -- NOT through
        # `reopen_ticket` -- reproducing the T-1914 incident shape
        # exactly: no reopen-log entry is ever written.
        main_sibling = load_all(v2_repo).danger_ok["T-3031"]
        assert write_ticket(
            v2_repo, main_sibling.model_copy(update={"state": TicketState.QUEUED})
        ).is_ok
        _commit_all(v2_repo, "hand-resurrect sibling T-3031")

        result = land(v2_repo, landing_id, wt, dry_run=False)
        assert result.is_err, (
            "a state resurrection with NO reopen-log entry must still be "
            "refused (T-4287 is an escape hatch for the audited verb "
            "only, not a general loosening of the T-1914 guard)"
        )
        assert result.danger_err == LandError.TerminalStateRegression

    # frob:ticket T-4287
    def test_pre_reopen_signatures_none_preserves_old_behavior(
        self, tmp_path: Path
    ) -> None:
        _git_init(tmp_path)
        _seed_v2_ticket(tmp_path, "T-1000")
        _make_closeable(tmp_path, "T-1000")
        assert transition(tmp_path, "T-1000", TicketState.DONE).is_ok
        _commit_all(tmp_path, "close T-1000")
        pre = _sibling_ticket_states(tmp_path, landing_id="T-9999")

        loaded = load_all(tmp_path)
        ticket = loaded.danger_ok["T-1000"]
        assert write_ticket(
            tmp_path, ticket.model_copy(update={"state": TicketState.QUEUED})
        ).is_ok

        # No `pre_reopen_signatures` given -- identical to the pre-T-4287
        # call shape, must still refuse.
        assert _assert_no_sibling_state_regression(tmp_path, "T-9999", pre) == (
            "T-1000",
        )
        assert _sibling_reopen_log_signatures(tmp_path, "T-9999") == {"T-1000": ()}


# frob:ticket T-4287
class TestNamesStrandedWorktreesBeforeReopen:
    """T-4287 AC3: `reopen_ticket` must name every live worktree whose own
    copy of the ticket is still terminal, BEFORE performing the
    DONE -> QUEUED transition."""

    # frob:tests \
    # tests/unit/test_land_sibling_regression.py::TestNamesStrandedWorktreesBeforeReope\
    # n.test_worktrees_carrying_terminal_copy_are_named
    # frob:ticket T-4287
    def test_worktrees_carrying_terminal_copy_are_named(self, v2_repo: Path) -> None:
        from frob.tickets._reporting import _worktrees_carrying_terminal_copy

        sibling = _seed_v2_ticket(v2_repo, "T-3040", scope=("src/sibling4.py",))
        assert sibling.id == "T-3040"
        _make_closeable(v2_repo, "T-3040")
        assert transition(v2_repo, "T-3040", TicketState.DONE).is_ok
        _commit_all(v2_repo, "close sibling T-3040")

        # A worktree forked AFTER T-3040 closed, doing UNRELATED work --
        # its own in-progress ticket is what holds the live lease
        # (`_make_closeable`'s own `transition(..., IN_PROGRESS)` records
        # it), not the terminal sibling itself. This is the real T-4287
        # shape: the worktree's OWN copy of T-3040 is what has gone stale,
        # discovered by checking its ticket store, not by a lease naming
        # T-3040 directly.
        wt = v2_repo.parent / "wt-stranded"
        _run(["git", "worktree", "add", "-b", "feature-stranded", str(wt)], v2_repo)
        created = new_ticket(wt, _spec("Unrelated work", scope=("src/lever.py",)))
        assert created.is_ok
        _make_closeable(wt, created.danger_ok.id)

        named = _worktrees_carrying_terminal_copy(v2_repo, "T-3040")
        assert named == (str(wt),)

        result = reopen_ticket(v2_repo, "T-3040", "T-4287: named before reopening")
        assert result.is_ok

        # No live-worktree lease at all -- no names, no error.
        no_stranding = _worktrees_carrying_terminal_copy(v2_repo, "T-3000")
        assert no_stranding == ()
