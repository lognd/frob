"""T-0162: ticket-id collision structurally impossible across checkouts.

Reproduces the three real incidents from the ticket body and proves the
REQUIRED INVARIANT end to end: two ledgers filed independently in any two
checkouts/branches/worktrees must never merge into the same final id, with
no human coordination.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates import Severity, tickets_gate
from frob.tickets import (
    Origin,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    finalize_draft,
    load_active,
    load_queue,
    new_ticket,
    renumber_one,
)
from frob.tickets._models import Ticket
from frob.tickets._provisional import is_draft_id, mint_draft_id, on_default_branch
from frob.tickets._store import atomic_write, ledger_path


def _run(argv: list[str], cwd: Path) -> None:
    subprocess.run(argv, cwd=str(cwd), check=True, capture_output=True, text=True)


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.BUG, origin=Origin.AGENT)


class TestPostArchiveReissueIncident:
    """Incident 1: allocator restarting from T-0001 after everything active
    got archived, colliding with an archived id (T-0140 fixed the max-scan;
    this proves it still holds under the T-0162 changes)."""

    def test_new_ticket_never_reissues_an_archived_id(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::new_ticket kind="unit"
        first = new_ticket(tmp_path, _spec("First"))
        assert first.is_ok
        assert first.danger_ok.id == "T-0001"

        from frob.tickets import archive, transition
        from frob.tickets._store import load_all, write_ticket

        done = transition(tmp_path, "T-0001", TicketState.PLANNED)
        assert done.is_ok
        done = transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        assert done.is_ok

        loaded = load_all(tmp_path)
        ticket = loaded.danger_ok["T-0001"]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(tmp_path, ticket).is_ok

        done = transition(tmp_path, "T-0001", TicketState.DONE)
        assert done.is_ok
        archived = archive(tmp_path)
        assert archived.is_ok and archived.danger_ok == 1

        active = load_active(tmp_path)
        assert active.is_ok
        assert active.danger_ok.tickets == {}

        second = new_ticket(tmp_path, _spec("Second"))
        assert second.is_ok
        assert second.danger_ok.id == "T-0002"


class TestTwoCheckoutConcurrentFilingIncident:
    """Incident 2: T-0144 reserved in one worktree while main allocated the
    same id -- avoided only by manual coordination. Proves off-default
    branches mint disjoint provisional ids so no coordination is needed."""

    def test_two_worktrees_file_concurrently_no_collision(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::finalize_draft kind="unit"
        # frob:tests src/frob/tickets/_provisional.py::on_default_branch kind="unit"
        # frob:tests src/frob/tickets/_provisional.py::is_draft_id kind="unit"
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        _commit_all(main_repo, "init")
        base_content = ledger_path(main_repo).read_text()

        wt_a = tmp_path / "wt-a"
        wt_b = tmp_path / "wt-b"
        _run(["git", "worktree", "add", "-b", "feature-a", str(wt_a)], main_repo)
        _run(["git", "worktree", "add", "-b", "feature-b", str(wt_b)], main_repo)

        assert on_default_branch(main_repo) is True
        assert on_default_branch(wt_a) is False
        assert on_default_branch(wt_b) is False

        result_a = new_ticket(wt_a, _spec("Filed from worktree A"))
        result_b = new_ticket(wt_b, _spec("Filed from worktree B"))
        assert result_a.is_ok
        assert result_b.is_ok

        id_a, id_b = result_a.danger_ok.id, result_b.danger_ok.id
        assert is_draft_id(id_a)
        assert is_draft_id(id_b)
        assert id_a != id_b  # THE INVARIANT: no coordination, no collision

        # Merge both branches into main, like a real land. Both sides append
        # a ledger section at the same end-of-file location, so git's own
        # textual merge conflicts here regardless of ids (a plain "both
        # added lines" conflict, orthogonal to T-0162) -- resolved the way a
        # land script resolves it, by keeping both appended sections. THE
        # INVARIANT under test is that once merged, the two ids are still
        # distinct: no human ever had to pick who "wins" an id, only that
        # trivial textual union.
        _commit_all(wt_a, "file draft ticket A")
        _commit_all(wt_b, "file draft ticket B")
        _run(["git", "merge", "-q", "feature-a"], main_repo)
        merge_b = subprocess.run(
            ["git", "merge", "feature-b"],
            cwd=str(main_repo),
            capture_output=True,
            text=True,
        )
        if merge_b.returncode != 0:
            # union resolution: both draft sections are independent, so
            # keep both -- abort git's failed 3-way attempt, take "ours"
            # (already merged feature-a) as the base, and append the
            # section "theirs" (feature-b) added relative to the pre-merge
            # base.
            _run(["git", "merge", "--abort"], main_repo)
            ours = ledger_path(main_repo).read_text()
            theirs = subprocess.run(
                ["git", "show", "feature-b:tickets.md"],
                cwd=str(main_repo),
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            added = (
                theirs[len(base_content) :]
                if theirs.startswith(base_content)
                else theirs
            )
            atomic_write(ledger_path(main_repo), ours + added)
            _run(["git", "add", "-A"], main_repo)
            _run(
                ["git", "commit", "-q", "-m", "merge feature-b (union resolve)"],
                main_repo,
            )

        merged = load_queue(main_repo)
        assert merged.is_ok
        assert {id_a, id_b} <= set(merged.danger_ok.tickets)

        final_a = finalize_draft(main_repo, id_a)
        assert final_a.is_ok
        final_b = finalize_draft(main_repo, id_b)
        assert final_b.is_ok

        assert final_a.danger_ok != final_b.danger_ok
        assert not is_draft_id(final_a.danger_ok)
        assert not is_draft_id(final_b.danger_ok)

        final_queue = load_queue(main_repo)
        assert final_queue.is_ok
        assert final_a.danger_ok in final_queue.danger_ok.tickets
        assert final_b.danger_ok in final_queue.danger_ok.tickets
        assert id_a not in final_queue.danger_ok.tickets
        assert id_b not in final_queue.danger_ok.tickets


class TestSweepWorktreeCollisionIncident:
    """Incident 3: a sweep worktree filed T-0157 while main independently
    assigned T-0157 to a different ticket, with ~100 code references to fix
    by hand. Proves `renumber_one` performs the atomic ledger+reference
    rewrite `frob ticket renumber <old> <new>` promises, at a scale
    representative of that incident."""

    def test_renumber_one_rewrites_ledger_and_many_code_references(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/__init__.py::renumber_one kind="unit"
        _git_init(tmp_path)
        collided = new_ticket(tmp_path, _spec("Collided ticket"))
        assert collided.is_ok
        old_id = collided.danger_ok.id

        # ~100 stray waiver references, like the real incident.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        for i in range(100):
            (src_dir / f"mod_{i}.py").write_text(
                f'"""module {i}."""\n\n# frob:waive TEST005 reason="debt {old_id}"\n'
                f"def f_{i}():\n    pass\n"
            )
        (src_dir / "unrelated.py").write_text(
            f'"""not a directive line: {old_id} mentioned in prose only."""\n'
        )
        _commit_all(tmp_path, "seed collision fixture")

        new_id = "T-9999"
        report = renumber_one(tmp_path, old_id, new_id)
        assert report.is_ok
        r = report.danger_ok
        assert r.ledger_changed is True
        assert (
            r.occurrences == 100
        )  # exactly the directive-line hits, not the prose one

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert new_id in queue.danger_ok.tickets
        assert old_id not in queue.danger_ok.tickets

        for i in range(100):
            text = (src_dir / f"mod_{i}.py").read_text()
            assert new_id in text
            assert old_id not in text
        # prose mention untouched -- only directive lines are code references
        assert old_id in (src_dir / "unrelated.py").read_text()

    def test_dry_run_reports_without_writing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::renumber_one kind="unit"
        collided = new_ticket(tmp_path, _spec("Collided ticket"))
        old_id = collided.danger_ok.id
        src = tmp_path / "mod.py"
        src.write_text(f"# frob:ticket {old_id}\ndef f():\n    pass\n")

        report = renumber_one(tmp_path, old_id, "T-9999", dry_run=True)
        assert report.is_ok
        assert report.danger_ok.dry_run is True
        assert report.danger_ok.occurrences == 1

        # nothing was actually written
        assert old_id in src.read_text()
        queue = load_queue(tmp_path)
        assert old_id in queue.danger_ok.tickets


class TestTick002GateUnwaivable:
    """A draft id that survives onto the default branch must fail `frob
    check` loudly and be unwaivable -- the finalize step exists precisely to
    prevent this, so silence here means the invariant quietly broke."""

    def test_draft_id_on_default_branch_is_a_violation(self, monkeypatch) -> None:
        # frob:tests src/frob/gates/__init__.py::tickets_gate kind="unit"
        monkeypatch.setattr("frob.gates.on_default_branch", lambda root: True)
        draft = Ticket(
            id=mint_draft_id(),
            title="stray draft",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=__import__("datetime").date(2026, 1, 1),
        )
        queue = TicketQueue(tickets={draft.id: draft})
        violations = tickets_gate(Path("."), queue)
        rules = {v.rule for v in violations}
        assert "TICK002" in rules
        tick002 = next(v for v in violations if v.rule == "TICK002")
        assert tick002.severity == Severity.ERROR

    def test_tick002_is_unwaivable(self) -> None:
        # frob:tests src/frob/gates/__init__.py::tickets_gate kind="unit"
        from frob.gates import _UNWAIVABLE_RULES

        assert "TICK002" in _UNWAIVABLE_RULES
        assert "TICK001" in _UNWAIVABLE_RULES

    def test_no_violation_off_default_branch(self, monkeypatch) -> None:
        # frob:tests src/frob/gates/__init__.py::tickets_gate kind="unit"
        # frob:tests src/frob/tickets/_provisional.py::mint_draft_id kind="unit"
        monkeypatch.setattr("frob.gates.on_default_branch", lambda root: False)
        draft = Ticket(
            id=mint_draft_id(),
            title="draft in flight",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=__import__("datetime").date(2026, 1, 1),
        )
        queue = TicketQueue(tickets={draft.id: draft})
        violations = tickets_gate(Path("."), queue)
        assert violations == ()
