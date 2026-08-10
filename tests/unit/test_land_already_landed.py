"""T-1618/T-1675: `frob.tickets._land._check_already_landed` -- landing a
ticket whose own declared scope has no changes relative to main, AND whose
own ledger record read directly off main already shows `state: done`, is a
distinct, self-explaining outcome (`LandError.AlreadyLandedOnMain`), not a
confusing fall-through into whatever the normal land path does with an
empty changeset. Always runs now (T-1675 removed the `check_already_landed`
opt-in flag) -- see `_check_already_landed`'s own docstring for why
requiring that second, POSITIVE on-main signal alongside the empty
scope-diff makes an unconditional default safe: the false-positive class
the old empty-diff-only check had (a docs-only/ledger-only/Done-report-only
ticket landing for the FIRST time) cannot also already be `done` on main,
so it no longer trips this refusal. Real git fixture repos throughout,
matching `tests/unit/test_land_cross_ticket_leakage.py`'s own style."""

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


# frob:waive WIRE001 reason="private test-seed helper used only by this module's own \
# TestAlreadyLandedOnMain.test_refuses_with_a_diagnostic_message_when_scope_diff_is_emp\
# ty -- module-local test-fixture builder, no production caller to wire it to by \
# design, same waived shape as tests/unit/perf/test_hotpath_smells.py's own precedent" \
# permanent="true"
def _seed_done_on_main(repo: Path, wt: Path, tid: str) -> None:
    """Simulate T-1618's passenger shape for real: transition `tid` to
    `DONE` in the worktree's OWN ledger (a valid state transition, so the
    resulting `Ticket` is a legitimate closed record), then write that
    SAME record directly into `repo` (main)'s ledger and commit it there
    -- as if a sibling ticket's earlier land had already carried `tid`'s
    content and closure onto main ahead of `tid`'s own land. This is the
    positive T-1675 signal `_check_already_landed` now requires: `tid`'s
    record read directly off `repo`'s tip must already show `state:
    done`, not merely an empty scope-diff."""
    assert transition(wt, tid, TicketState.DONE).is_ok
    done_ticket = load_all(wt).danger_ok[tid]
    assert write_ticket(repo, done_ticket).is_ok
    _commit_all(repo, f"seed: {tid} already closed on main (simulated passenger land)")


# frob:ticket T-1618
# frob:ticket T-1675
class TestAlreadyLandedOnMain:
    """`_check_already_landed` -- an empty diff inside the ticket's own
    scope, PLUS the ticket's own record already showing `done` on main
    (T-1675's positive signal), refuses with a distinct, self-explaining
    outcome instead of falling through to a confusing generic failure."""

    def test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"
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
        # T-1675's positive signal: tid's OWN record already shows `done`
        # on main, not just an empty scope-diff.
        _seed_done_on_main(repo, wt, tid)
        # Committed on the branch, but touching a DIFFERENT file than the
        # ticket's own declared scope -- e.g. only its own ledger record
        # moved; no actual change to src/already-there.py on this branch.
        (wt / "src" / "unrelated.py").write_text("# unrelated bookkeeping\n")
        _commit_all(wt, f"{tid}: ledger-only, no scope change")

        with caplog.at_level("WARNING"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.AlreadyLandedOnMain
        assert "frob ticket close" in caplog.text
        assert tid in caplog.text

    def test_no_op_when_the_ticket_has_real_changes_in_its_own_scope(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-real", str(wt)], repo)
        created = new_ticket(wt, _spec("Real work", scope=("src/fix.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "fix.py").write_text("# real change\n")
        _commit_all(wt, f"{tid}: real change")

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    def test_no_op_when_the_ticket_declares_no_scope_at_all(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-scopeless", str(wt)], repo)
        created = new_ticket(wt, _spec("No scope declared", scope=()))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "fix.py").write_text("# change under an empty scope\n")
        _commit_all(wt, f"{tid}: change, no declared scope")

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    # frob:ticket T-1950
    def test_refuses_when_a_sibling_carried_this_tickets_content_before_it_ever_landed(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"
        # T-1950: the case T-1675's DONE-state signal cannot see -- tid's
        # OWN code already rode onto main under a SIBLING's earlier
        # --allow-cross-ticket land (carrying tid's own frob:ticket
        # directive along with it, per this repo's own convention), but
        # tid itself was never closed anywhere, so its ledger record on
        # main does not exist at all (not merely non-done). Measured
        # 2026-08-10: this is exactly T-1720's real shape after T-1922's
        # land carried it.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-carried", str(wt)], repo)
        created = new_ticket(wt, _spec("Carried elsewhere", scope=("src/held.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Simulate a sibling's earlier land carrying tid's own marked code
        # onto main -- the sibling's own commit, not tid's.
        (repo / "src" / "sibling_carried.py").write_text(
            f"# frob:ticket {tid}\ndef carried() -> None:\n    pass\n"
        )
        _commit_all(repo, "seed: a sibling land already carried tid's own code")

        # tid's own branch: committed, but nothing under its declared
        # scope -- everything it would have contributed is already on
        # main via the sibling above.
        (wt / "src" / "unrelated.py").write_text("# unrelated bookkeeping\n")
        _commit_all(wt, f"{tid}: nothing left to contribute, already carried")

        with caplog.at_level("WARNING"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.AlreadyLandedOnMain
        assert "frob ticket close" in caplog.text
        assert tid in caplog.text

    # frob:ticket T-1950
    def test_no_op_when_no_frob_ticket_directive_for_this_id_exists_on_main(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"
        # T-1950's own false-positive guard: an empty scope-diff with
        # NEITHER positive signal (no done state, no frob:ticket directive
        # anywhere on main) must not be refused -- the ordinary first-time
        # land of a ticket that genuinely has nothing yet.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-no-directive", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Nothing carried anywhere", scope=("src/held.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated.py").write_text("# unrelated bookkeeping\n")
        _commit_all(wt, f"{tid}: ledger-only, nothing under its own scope yet")

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err

    def test_no_op_for_a_docs_only_ticket_whose_scope_diff_is_empty_but_not_yet_landed(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_already_landed kind="unit"
        """T-1675's actual regression target: a docs-only ticket whose
        declared scope legitimately has no hits on this branch (it only
        ever needed a Done-report note, never a byte inside `docs/**`)
        must NOT be refused as 'already landed' just because its
        scope-diff is empty -- unlike the sibling test above, `tid` was
        NEVER written to `repo`'s ledger at all, so it has no `done`
        record there; the empty-diff-alone inference this ticket exists
        to close would have refused this incorrectly."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo-docs-only", str(wt)], repo)
        created = new_ticket(wt, _spec("Docs-only ticket", scope=("docs/**",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Committed on the branch, but nothing under docs/** -- the
        # ordinary shape of a docs-only ticket whose real content is its
        # Done report, already folded into the ledger-only diff `_check_
        # already_landed` deliberately excludes from scope-hit counting.
        (wt / "src" / "unrelated.py").write_text("# unrelated bookkeeping\n")
        _commit_all(wt, f"{tid}: ledger-only, docs scope never touched")

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
