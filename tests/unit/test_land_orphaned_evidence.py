"""T-1946: `frob.tickets._land._check_orphaned_evidence_deletion` --
refuse a land whose branch deletes or renames a pytest test node bound
as evidence on a DIFFERENT ticket.

MEASURED INCIDENT (T-1946's own brief): two independent actors, one
hour, each deleted/replaced a test with no signal the deleting diff was
touching anything outside its own scope -- one deletion orphaned THREE
unrelated tickets' evidence at once (100% of the then-current unscoped
error floor, 4 COV003 findings). Real git fixture repo (matching
`tests/unit/test_land_cross_ticket_leakage.py`'s own style) -- pure git
plumbing, no checkout beyond the fixture's own branches. `collect_python_
tests` is monkeypatched (matching `tests/test_ticket_reverify.py`'s own
`_patch_collect` precedent) so these stay hermetic, no real pytest
subprocess spawn."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest
from typani import Ok

from frob.testing._models import CollectedTests
from frob.tickets import (
    Origin,
    Ticket,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import _check_orphaned_evidence_deletion
from frob.tickets._models import LandError
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:ticket T-2017
# frob:waive WIRE001 permanent="true" reason="private test-tree fixture helper, only \
# ever called from this file's own two archived-ticket regression tests -- the same \
# permanent test-support-helper class WIRE002 exempts from the follow_up requirement"
def _ticket_done(ticket_id: str, evidence_id: str) -> Ticket:
    """A minimal, already-DONE `Ticket` bound to `evidence_id` (T-2017) --
    built directly rather than via `transition` (which this test module's
    other fixtures use for an ACTIVE ticket) so the archived-ticket
    regression tests can seed a ticket straight into the DONE state
    `archive()` requires, with no intermediate PLANNED/IN_PROGRESS lease
    machinery to satisfy."""
    return Ticket(
        id=ticket_id,
        title=f"archived ticket {ticket_id}",
        state=TicketState.DONE,
        kind=TicketKind.FEATURE,
        origin=Origin.AGENT,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(evidence_id,),
        attachments=(),
        acceptance=(),
        threat=None,
        body="## Done report\n\nseeded directly for T-2017's archived-ticket test\n",
    )


# frob:waive DUP001 reason="fixture-repo git-init/commit boilerplate already \
# duplicated verbatim across tests/unit/test_land_cross_ticket_leakage.py and several \
# other land test modules -- each land test module owns its own tiny copy rather than \
# importing across test files, the existing convention this repo's suite follows"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


# frob:waive DUP001 reason="same established git-commit fixture idiom as _git_init's \
# own waiver above -- see that comment"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Make `frob.testing.collect_python_tests` return `node_ids` without
    spawning pytest, matching `tests/test_ticket_reverify.py::_patch_
    collect`'s own established pattern for this exact hermetic-collection
    substitution."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


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


class TestOrphanedEvidenceDeletion:
    """`_check_orphaned_evidence_deletion` refuses when this branch's own
    commits delete/rename a test node bound as evidence on a different
    ticket -- unless the same diff re-points that evidence."""

    # frob:ticket T-1946
    def test_refuses_when_branch_deletes_evidence_bound_test(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests \
        # tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion.test_\
        # refuses_when_branch_deletes_evidence_bound_test
        # This is the FAIL-THEN-PASS proof for T-1946 acceptance 1: before
        # _check_orphaned_evidence_deletion existed, nothing refused this
        # shape -- the branch would land, and the orphan would only
        # surface later as an unrelated COV003 finding.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)

        other = new_ticket(wt, _spec("Unrelated work", scope=("tests/test_orphan.py",)))
        assert other.is_ok
        other_id = other.danger_ok.id
        assert transition(wt, other_id, TicketState.PLANNED).is_ok
        assert transition(wt, other_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        other_ticket = loaded.danger_ok[other_id]
        other_ticket = other_ticket.model_copy(
            update={"evidence": ("tests/test_orphan.py::test_it",)}
        )
        assert write_ticket(wt, other_ticket).is_ok
        (wt / "tests").mkdir(exist_ok=True)
        (wt / "tests" / "test_orphan.py").write_text("def test_it():\n    pass\n")
        _commit_all(wt, f"{other_id}: add the test this ticket's evidence cites")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        (wt / "tests" / "test_orphan.py").write_text("# test_it deleted\n")
        _commit_all(wt, f"{landing_id}: unrelated cleanup that deletes test_it")

        # collect_python_tests now reports test_it gone -- the deletion
        # already landed on this branch's own history.
        _patch_collect(monkeypatch, frozenset())

        landing_ticket = load_all(wt).danger_ok[landing_id]
        with caplog.at_level("ERROR"):
            result = _check_orphaned_evidence_deletion(wt, landing_ticket, "main")

        assert result.is_err
        assert result.danger_err == LandError.OrphanedEvidenceDeletion
        assert other_id in caplog.text
        assert "tests/test_orphan.py::test_it" in caplog.text

    # frob:ticket T-1946
    def test_deletion_of_unbound_test_lands_cleanly(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion.test_\
        # deletion_of_unbound_test_lands_cleanly
        # T-1946 acceptance 2: no false refusal when nothing else cites
        # the deleted node.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-b", str(wt)], repo)

        landing = new_ticket(wt, _spec("Cleanup", scope=("tests/test_scratch.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        (wt / "tests").mkdir(exist_ok=True)
        (wt / "tests" / "test_scratch.py").write_text("def test_it():\n    pass\n")
        _commit_all(wt, f"{landing_id}: add scratch test")
        (wt / "tests" / "test_scratch.py").write_text("# deleted, cited by nobody\n")
        _commit_all(wt, f"{landing_id}: delete scratch test, unbound to anything")

        _patch_collect(monkeypatch, frozenset())

        landing_ticket = load_all(wt).danger_ok[landing_id]
        result = _check_orphaned_evidence_deletion(wt, landing_ticket, "main")

        assert result.is_ok

    # frob:ticket T-1946
    def test_rename_that_repoints_evidence_in_same_diff_is_accepted(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion.test_\
        # rename_that_repoints_evidence_in_same_diff_is_accepted
        # T-1946 acceptance 3: a rename that ALSO re-points the affected
        # ticket's evidence, in the same diff, must not be refused.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-c", str(wt)], repo)

        other = new_ticket(wt, _spec("Unrelated work", scope=("tests/test_old.py",)))
        assert other.is_ok
        other_id = other.danger_ok.id
        assert transition(wt, other_id, TicketState.PLANNED).is_ok
        assert transition(wt, other_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        other_ticket = loaded.danger_ok[other_id]
        other_ticket = other_ticket.model_copy(
            update={"evidence": ("tests/test_old.py::test_it",)}
        )
        assert write_ticket(wt, other_ticket).is_ok
        (wt / "tests").mkdir(exist_ok=True)
        (wt / "tests" / "test_old.py").write_text("def test_it():\n    pass\n")
        _commit_all(wt, f"{other_id}: add the test this ticket's evidence cites")

        landing = new_ticket(wt, _spec("Rename with repoint", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        (wt / "tests" / "test_old.py").unlink()
        (wt / "tests" / "test_new.py").write_text("def test_it():\n    pass\n")
        repointed = load_all(wt).danger_ok[other_id].model_copy(
            update={"evidence": ("tests/test_new.py::test_it",)}
        )
        assert write_ticket(wt, repointed).is_ok
        _commit_all(
            wt, f"{landing_id}: rename test_old.py -> test_new.py, repoint {other_id}"
        )

        _patch_collect(monkeypatch, frozenset({"tests/test_new.py::test_it"}))

        landing_ticket = load_all(wt).danger_ok[landing_id]
        result = _check_orphaned_evidence_deletion(wt, landing_ticket, "main")

        assert result.is_ok


# frob:ticket T-2017
class TestOrphanedEvidenceDeletionOnArchivedTicket:
    """T-2017: the MEASURED root cause of the T-1963 incident -- neither
    of the two hypotheses that ticket started from (a stale collection
    cache, or a rename mis-parsed as add+delete). `_check_orphaned_
    evidence_deletion` used `load_all(worktree)`, which for a repo's
    ACTIVE ledger never includes an already-ARCHIVED (done) ticket -- so
    an archived ticket's evidence was never even a CANDIDATE this check
    could flag, regardless of collection freshness or diff shape. T-0907
    (the real orphaned ticket) was archived long before T-1963's land
    ever ran."""

    # frob:ticket T-2017
    def test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests \
        # tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArch\
        # ivedTicket.test_refuses_when_branch_deletes_evidence_bound_test_on_an_archive\
        # d_ticket
        # T-2017 (MUST FAIL on the pre-fix code, matching T-1963's real
        # incident exactly): other_id is DONE and ARCHIVED -- moved out
        # of the active ledger into tickets-archive.md -- before the
        # landing branch's own diff deletes the test its evidence cites.
        from frob.tickets._archive import archive
        from frob.tickets._store import write_all

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-archived", str(wt)], repo)

        (wt / "tests").mkdir(exist_ok=True)
        (wt / "tests" / "test_archived.py").write_text("def test_it():\n    pass\n")
        other_id = "T-9001"
        other_ticket = _ticket_done(other_id, "tests/test_archived.py::test_it")
        assert write_all(wt, {other_id: other_ticket}).is_ok
        _commit_all(wt, f"seed {other_id}: done, evidence bound to test_archived.py")

        archived_count = archive(wt, force=True)
        assert archived_count.is_ok, archived_count.err
        assert archived_count.danger_ok == 1
        _commit_all(wt, f"archive {other_id}")

        landing = new_ticket(wt, _spec("Independent cleanup", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        (wt / "tests" / "test_archived.py").write_text("# test_it deleted\n")
        _commit_all(
            wt, f"{landing_id}: unrelated cleanup that deletes test_it (archived owner)"
        )

        _patch_collect(monkeypatch, frozenset())

        landing_ticket = load_all(wt).danger_ok[landing_id]
        with caplog.at_level("ERROR"):
            result = _check_orphaned_evidence_deletion(wt, landing_ticket, "main")

        assert result.is_err
        assert result.danger_err == LandError.OrphanedEvidenceDeletion
        assert other_id in caplog.text
        assert "tests/test_archived.py::test_it" in caplog.text

    # frob:ticket T-2017
    def test_deletion_unbound_to_any_archived_ticket_still_lands_cleanly(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArch\
        # ivedTicket.test_deletion_unbound_to_any_archived_ticket_still_lands_cleanly
        # Sanity companion (acceptance criterion 4): a real archived
        # ticket exists, but its evidence is untouched by this diff --
        # must not over-refuse.
        from frob.tickets._archive import archive
        from frob.tickets._store import write_all

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-archived-unbound", str(wt)], repo)

        (wt / "tests").mkdir(exist_ok=True)
        (wt / "tests" / "test_kept.py").write_text("def test_it():\n    pass\n")
        other_id = "T-9002"
        other_ticket = _ticket_done(other_id, "tests/test_kept.py::test_it")
        assert write_all(wt, {other_id: other_ticket}).is_ok
        _commit_all(wt, f"seed {other_id}: done, evidence bound to test_kept.py")
        assert archive(wt, force=True).is_ok
        _commit_all(wt, f"archive {other_id}")

        landing = new_ticket(wt, _spec("Unrelated fix", scope=("tests/test_scratch2.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        (wt / "tests" / "test_scratch2.py").write_text("def test_it():\n    pass\n")
        _commit_all(wt, f"{landing_id}: add scratch test, unrelated to {other_id}")
        (wt / "tests" / "test_scratch2.py").write_text("# deleted, cited by nobody\n")
        _commit_all(wt, f"{landing_id}: delete scratch test, unbound to anything")

        _patch_collect(monkeypatch, frozenset({"tests/test_kept.py::test_it"}))

        landing_ticket = load_all(wt).danger_ok[landing_id]
        result = _check_orphaned_evidence_deletion(wt, landing_ticket, "main")

        assert result.is_ok, result.err
