"""T-0176: `frob ticket land` -- one-command landing.

Fixture-repo tests reproducing the real incident classes the ticket body
names: a stale-base worktree silently deleting a feature main already
landed, a `tickets.md` both-sides-append textual conflict, and provisional
(draft) id finalization at land time. Uses real git subprocesses (matching
tests/test_tickets_collision.py's style) -- not mocks -- because the whole
point of `land` is real merge/conflict/deletion behavior.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok

import frob.tickets._land as _land_mod
from frob.gitio import GitError, ProcResult, run_argv
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land, splice_ledger
from frob.tickets._models import LandError
from frob.tickets._store import (
    atomic_write,
    ledger_path,
    load_all,
    load_archive,
    write_ticket,
)


def _failing_run_argv(
    monkeypatch: pytest.MonkeyPatch,
    should_fail: Callable[[Sequence[str]], bool],
    *,
    hard_err: bool = False,
) -> None:
    """Patch `frob.tickets._land.run_argv` (the single import point every
    helper in the module calls through) so any invocation matching
    `should_fail` returns a git failure -- either a bad returncode
    (`hard_err=False`) or an `Err(GitError...)` result (`hard_err=True`) --
    while everything else delegates to the real `run_argv`. This is how a
    real, hard-to-reproduce git subprocess failure (permission denial, disk
    full, a corrupted ref) gets exercised deterministically."""

    def _fake(argv: Sequence[str], **kwargs: Any) -> Any:
        if should_fail(argv):
            if hard_err:
                return Err(GitError.GitFailed)
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=1,
                    stdout="",
                    stderr="simulated failure",
                )
            )
        return run_argv(argv, **kwargs)

    monkeypatch.setattr(_land_mod, "run_argv", _fake)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept:
    planned -> in-progress, evidence + Done report attached."""
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


class TestSpliceLedger:
    """`splice_ledger` -- the id-level merge tickets.md conflicts always go
    through, never git's line-level textual algorithm."""

    def test_disjoint_ids_both_kept(self, tmp_path: Path) -> None:
        ours = new_ticket(tmp_path, _spec("Ours"))
        assert ours.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # A second, DISJOINT id on "their" side -- write it directly rather
        # than via new_ticket (two non-git tmp dirs would both allocate
        # T-0001, which is not the scenario under test: two SIDES of an
        # already-diverged ledger, one entry each).
        theirs_path = tmp_path / "theirs"
        theirs_path.mkdir()
        theirs_ticket = ours.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Theirs"}
        )
        atomic_write(ledger_path(theirs_path), "# Tickets\n\n")
        assert write_ticket(theirs_path, theirs_ticket).is_ok
        theirs_text = ledger_path(theirs_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "Ours" in spliced.danger_ok
        assert "Theirs" in spliced.danger_ok

    def test_same_id_newer_state_wins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::splice_ledger kind="unit"
        created = new_ticket(tmp_path, _spec("Shared"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "state: planned" in spliced.danger_ok
        assert "state: queued" not in spliced.danger_ok


class TestLand:
    """`frob.tickets.land` against real fixture repos."""

    def test_dry_run_lands_cleanly_and_leaves_no_trace(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-a", str(wt)], repo)
        created = new_ticket(wt, _spec("Add widget", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "add widget")

        # Main gains a commit AFTER the worktree branched, so merging main
        # into the worktree is a real merge, not a no-op.
        (repo / "src" / "unrelated.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        before_wt_sha = _run(["git", "rev-parse", "HEAD"], wt).stdout.strip()

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.dry_run is True
        assert report.merged_main_into_worktree is True

        # Dry run must leave both checkouts exactly as found.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "rev-parse", "HEAD"], wt).stdout.strip() == before_wt_sha
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""

    def test_real_land_lands(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-b", str(wt)], repo)
        created = new_ticket(wt, _spec("Add gadget", scope=("src/gadget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "gadget.py").write_text("# new gadget\n")
        _commit_all(wt, "add gadget")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.dry_run is False
        assert report.commit_sha is not None
        assert (repo / "src" / "gadget.py").exists()

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE

    def test_refuses_on_dirty_main(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-c", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        (repo / "dirty.txt").write_text("uncommitted\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain

    def test_refuses_without_evidence_or_done_report(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-d", str(wt)], repo)
        created = new_ticket(wt, _spec("Not ready"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(wt, "wip")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Nothing must have been touched -- close validation runs BEFORE any
        # git mutation, so main and the worktree are exactly as found.
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


class TestCloseFailAfterMerge:
    """`_transition_guard` can still refuse `DONE` even after `_validate_
    closeable`'s precheck passed on the worktree's OWN snapshot -- the
    splice can overwrite the worktree's in-memory ticket with a further-
    along same-id entry from main (e.g. DROPPED, a terminal state with no
    outgoing transitions) between the precheck and the close call. `land`
    must surface `LandError.CloseFailed` and name the manual remedy rather
    than silently landing a ticket main considers dropped."""

    def test_close_fails_after_merge_when_main_dropped_same_id(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-k", str(wt)], repo)

        created = new_ticket(wt, _spec("Race with main", scope=("src/raced.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "raced.py").write_text("# raced feature\n")
        _commit_all(wt, "add raced feature")

        # Main independently ends up with the SAME ticket id, further along
        # the state machine (DROPPED, terminal) -- simulating a race where
        # main dropped this exact ticket after the worktree branched.
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        dropped = created.danger_ok.model_copy(update={"state": TicketState.DROPPED})
        assert write_ticket(repo, dropped).is_ok
        _commit_all(repo, "main independently drops the same ticket id")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.CloseFailed

        # The merge into the worktree landed (that happens before close),
        # but main itself must be untouched -- the failure surfaces before
        # any squash-apply onto main.
        landed_main = load_all(repo)
        assert landed_main.is_ok
        assert landed_main.danger_ok[tid].state == TicketState.DROPPED


class TestStaleBaseDeletion:
    """Incident class 1: a worktree branched from an old main base ends up,
    relative to main's CURRENT tip, deleting a file main already landed --
    the deletion-filter check must abort loudly rather than let that
    deletion reach main."""

    def test_unowned_deletion_aborts_loudly(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-e", str(wt)], repo)

        # The worktree's own (out-of-scope) change deletes a file main has
        # -- simulating a stale-base agent that clobbered an unrelated file
        # it never should have touched.
        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions

        # Worktree must be left clean (merge --abort ran) -- no half-applied
        # merge state left behind by the aborted dry run.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""
        assert (repo / "src" / "feature.py").exists()

    def test_scoped_deletion_is_allowed(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-f", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Retire feature", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "retire feature.py, in scope")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err


class TestLedgerBothSidesAppend:
    """Incident class 2: main gets a new ticket appended AFTER the worktree
    branched, and the worktree independently appends its own new ticket --
    a textual same-region conflict in tickets.md that must resolve as
    "keep both", not as a real conflict requiring a human."""

    def test_both_sides_append_merges_cleanly(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-g", str(wt)], repo)

        created_wt = new_ticket(
            wt, _spec("Worktree ticket", scope=("src/wt_thing.py",))
        )
        assert created_wt.is_ok
        wt_tid = created_wt.danger_ok.id
        _make_closeable(wt, wt_tid)
        (wt / "src" / "wt_thing.py").write_text("# from worktree\n")
        _commit_all(wt, "worktree ticket + feature")

        # Main independently gains a new ticket AFTER the worktree branched.
        created_main = new_ticket(repo, _spec("Main-side ticket"))
        assert created_main.is_ok
        main_tid = created_main.danger_ok.id
        _commit_all(repo, "main-side ticket")

        result = land(repo, wt_tid, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id

        landed = load_all(repo)
        assert landed.is_ok
        assert final_id in landed.danger_ok
        assert main_tid in landed.danger_ok
        assert landed.danger_ok[final_id].state == TicketState.DONE


class TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean:
    """Reviewer bug 1: `finalize_draft` rewrites tickets.md AND every code
    file carrying a `frob:ticket <draft-id>` directive, uncommitted, in the
    worktree -- but the old `land` squashed from the branch's last commit,
    which predated those rewrites. A landed source file kept the dangling
    draft id, and the worktree was left dirty after a "successful" land.
    `land` must commit finalize/close's changes in the worktree BEFORE the
    squash so both the ledger AND the rewritten code reach main, and the
    worktree ends up clean."""

    def test_code_directive_rewritten_and_worktree_clean_after_land(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-i", str(wt)], repo)

        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing2.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        # A code file carrying a frob:ticket directive naming the DRAFT id --
        # renumber_one (finalize_draft's rename primitive) must rewrite this
        # reference, and that rewrite must actually reach main.
        (wt / "src" / "thing2.py").write_text(
            f"# frob:ticket {draft_id}\ndef f():\n    pass\n"
        )
        _commit_all(wt, "off-branch ticket with a code directive")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id
        assert final_id != draft_id

        # The landed file on MAIN must carry the FINAL id, never the draft.
        landed_src = (repo / "src" / "thing2.py").read_text()
        assert draft_id not in landed_src
        assert f"frob:ticket {final_id}" in landed_src

        # The worktree must be left completely clean -- finalize/close's
        # writes were committed before the squash, not left dangling.
        wt_status = _run(["git", "status", "--porcelain"], wt).stdout.strip()
        assert wt_status == "", f"worktree left dirty: {wt_status!r}"

        # And the worktree's own copy of the file must ALSO carry the final
        # id (the commit-before-squash fix touches the worktree itself).
        wt_src = (wt / "src" / "thing2.py").read_text()
        assert draft_id not in wt_src
        assert f"frob:ticket {final_id}" in wt_src


class TestArchiveResurrection:
    """Reviewer bug 2: `splice_ledger` only read active tickets.md, never
    tickets-archive.md -- an id archived on main after the branch point
    would survive the ours-union and land back into main's active ledger,
    resurrecting a duplicate-id class a human previously had to resolve by
    hand at merge time (T-0176's own 0bb02cf merge). `land` must never
    reintroduce an already-archived id."""

    def test_archived_id_never_resurrected(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::splice_ledger kind="unit"
        # Seed a ticket that exists (stale, still active) in the worktree's
        # ledger view, then archive it on MAIN after the branch point --
        # simulating a branch whose base predates the archive.
        stale = new_ticket(repo, _spec("Will be archived"))
        assert stale.is_ok
        stale_id = stale.danger_ok.id
        _commit_all(repo, "file the soon-to-be-archived ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-j", str(wt)], repo)

        # Main independently closes and archives it AFTER the worktree
        # branched -- the worktree's tickets.md still has it as active.
        assert transition(repo, stale_id, TicketState.PLANNED).is_ok
        assert transition(repo, stale_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(repo)
        stale_ticket = loaded.danger_ok[stale_id]
        stale_ticket = stale_ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": stale_ticket.body + "\n## Done report\n\ndone\n",
            }
        )
        assert write_ticket(repo, stale_ticket).is_ok
        assert transition(repo, stale_id, TicketState.DONE).is_ok
        from frob.tickets import archive

        archived_count = archive(repo)
        assert archived_count.is_ok and archived_count.danger_ok == 1
        _commit_all(repo, "archive the stale ticket")

        # Now land unrelated worktree work; the worktree's own tickets.md
        # STILL carries stale_id as active (it branched before the archive).
        created = new_ticket(wt, _spec("Unrelated land", scope=("src/unrelated2.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated2.py").write_text("# unrelated\n")
        _commit_all(wt, "unrelated worktree work")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        active = load_all(repo)
        assert active.is_ok
        assert stale_id not in active.danger_ok, (
            f"{stale_id} resurrected into the active ledger by land"
        )

        archived = load_archive(repo)
        assert archived.is_ok
        assert stale_id in archived.danger_ok
        # Exactly once -- not duplicated across active+archive.
        assert list(load_all(repo).danger_ok).count(stale_id) == 0


class TestWipCommit:
    """`_wip_commit` -- uncommitted worktree changes at land time must be
    snapshotted before the merge that follows, both in dry-run (staged then
    unwound) and real (actually committed) mode."""

    def test_dry_run_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-dry", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip dry", scope=("src/wip_dry.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip dry ticket bits")

        # An UNCOMMITTED change present when land() is called.
        (wt / "src" / "wip_dry.py").write_text("# uncommitted at land time\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        # Dry run unwinds everything -- the uncommitted change is still
        # sitting uncommitted in the worktree afterward.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() != ""

    def test_real_land_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-real", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip real", scope=("src/wip_real.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "wip_real.py").write_text("# committed baseline\n")
        _commit_all(wt, "wip real ticket bits")

        # An UNCOMMITTED change present when land() is called, real run.
        (wt / "src" / "wip_real.py").write_text("# uncommitted change to snapshot\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" in wt_log

        landed_content = (repo / "src" / "wip_real.py").read_text()
        assert landed_content == "# uncommitted change to snapshot\n"


class TestKindEvidenceMismatch:
    """`_validate_closeable`'s T-0215 kind-consistency guard: a non-docs-kind
    ticket carrying a `cmd:`-shaped evidence entry must never land, mirroring
    the write-time gate in `add_cmd_evidence`."""

    def test_non_docs_kind_with_cmd_evidence_refused(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-kind", str(wt)], repo)
        created = new_ticket(wt, _spec("Feature kind with cmd evidence"))
        assert created.is_ok
        tid = created.danger_ok.id

        loaded = load_all(wt)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        # FEATURE is not in CMD_EVIDENCE_ALLOWED_KINDS ({DOCS}), but the
        # evidence entry has the exact cmd: shape (as if hand-pasted or the
        # kind was changed after the entry was recorded).
        ticket = ticket.model_copy(
            update={
                "evidence": ("cmd:pytest -q exit=0 sha256=abcdef012345",),
                "body": ticket.body + "\n## Done report\n\ndone\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "feature ticket with cmd evidence")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable


class TestUnownedDeletionRealRun:
    """The `_unowned_deletions` abort must behave identically in a real
    (non-dry-run) landing -- main untouched, worktree merge state aborted."""

    def test_unowned_deletion_aborts_on_real_run(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-real-del", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(
            wt, _spec("Unrelated real ticket", scope=("src/other2.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py, real run")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions

        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert (repo / "src" / "feature.py").exists()
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


class TestMergeConflictOutsideLedger:
    """`_merge_main_into_worktree` must abort loudly (not silently splice)
    on a real textual conflict in a NON-tickets.md file -- only tickets.md
    is resolved via `splice_ledger`; anything else conflicting must surface
    to a human."""

    def test_real_conflict_outside_tickets_md_aborts(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-conflict", str(wt)], repo)

        # Worktree modifies the SAME line of src/feature.py.
        (wt / "src" / "feature.py").write_text("# worktree-side edit\n")
        created = new_ticket(wt, _spec("Conflicting edit", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits feature.py")

        # Main independently modifies the SAME line, AFTER the worktree
        # branched -- a genuine textual conflict on a non-ticket file.
        (repo / "src" / "feature.py").write_text("# main-side edit\n")
        _commit_all(repo, "main edits feature.py")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.MergeConflict

        # _abort_merge must have run -- worktree left exactly as found.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


class TestDraftIdFinalization:
    """Incident class 3: a ticket filed off the default branch got a
    provisional T-draft-<hex> id; landing must finalize it to a real
    sequential id (T-0162's promised mechanism) before closing."""

    def test_draft_id_finalized_on_land(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-h", str(wt)], repo)

        # A worktree is, by definition, off the default branch -- new_ticket
        # mints a draft id here unconditionally.
        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        (wt / "src" / "thing.py").write_text("# thing\n")
        _commit_all(wt, "off-branch ticket")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.final_id != draft_id
        assert not report.final_id.startswith("T-draft-")

        landed = load_all(repo)
        assert landed.is_ok
        assert draft_id not in landed.danger_ok
        assert report.final_id in landed.danger_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


class TestLandNotFound:
    """`land` on a ticket id the worktree's store has never heard of."""

    def test_unknown_ticket_id_returns_not_found(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nf", str(wt)], repo)

        result = land(repo, "T-9999", wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotFound


class TestGitSubprocessFailures:
    """`land`'s own git-failure early returns -- each wraps a `run_argv`
    call whose failure is otherwise only reachable via a real, hard-to-
    reproduce environment fault (permission denial, disk full, a corrupted
    ref). Deterministically forced here via `_failing_run_argv` patching
    the module's single `run_argv` import point."""

    def test_main_dirty_check_git_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l1", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(repo) in argv and "status" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_main_branch_lookup_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l2", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # `current_branch` (frob.gitio) has its own internal `run_argv`
        # reference, independent of the one `_land.py` imports -- patch the
        # symbol `_land.py` calls directly rather than the git subprocess
        # layer, to exercise `land`'s own `main_branch.is_err` branch.
        def _fail(root: Path) -> Any:
            return Err(GitError.GitFailed)

        monkeypatch.setattr(_land_mod, "current_branch", _fail)
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_wip_commit_status_check_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l3", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "status" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_merge_command_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l4", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")
        (repo / "src" / "extra.py").write_text("# extra main commit\n")
        _commit_all(repo, "main moves on")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "merge" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_unowned_deletions_diff_failure_after_merge(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l5", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l5.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l5.py").write_text("# l5\n")
        _commit_all(wt, "wip")
        (repo / "src" / "extra2.py").write_text("# extra main commit\n")
        _commit_all(repo, "main moves on")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(wt) in argv and "diff" in argv and "--diff-filter=D" in argv
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # The merge that already landed in the worktree must have been
        # aborted -- no half-applied merge state left behind.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""

    def test_squash_command_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l6", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l6.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l6.py").write_text("# l6\n")
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(repo) in argv and "--squash" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_final_commit_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l7", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l7.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l7.py").write_text("# l7\n")
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(repo) in argv and "commit" in argv and "--squash" not in argv
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.CommitFailed


class TestLandDeeperBranches:
    """Additional `land`-body branches unreachable via ordinary happy/error
    fixture paths: the post-merge commit and finalize/close git-failure
    branches, each forced deterministically via monkeypatch since a real
    reproduction (disk full, permission denial mid-land) is impractical to
    fixture."""

    def test_unowned_deletion_real_run_with_actual_merge(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l8", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Unrelated", scope=("src/other8.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py")

        # Main gains a commit AFTER the worktree branched, so merging main
        # into the worktree is a REAL merge (did_merge=True), not a no-op --
        # exercising the `if did_merge: _abort_merge(...)` branch under the
        # unowned-deletion abort, in a real (non-dry-run) land.
        (repo / "src" / "unrelated8.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""
        assert (repo / "src" / "feature.py").exists()

    def test_post_merge_commit_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l9", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l9.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l9.py").write_text("# l9\n")
        _commit_all(wt, "wip")

        (repo / "src" / "unrelated9.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(wt) in argv
                and "commit" in argv
                and any("merge" in a and "landing" in a for a in argv)
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_finalize_draft_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        import frob.tickets as tickets_mod

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l10", str(wt)], repo)
        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/l10.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        (wt / "src" / "l10.py").write_text("# l10\n")
        _commit_all(wt, "off-branch ticket")

        from frob.tickets._models import TicketError

        monkeypatch.setattr(
            tickets_mod, "finalize_draft", lambda *a, **k: Err(TicketError.NotFound)
        )
        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_worktree_branch_lookup_failure_after_close(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l11", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l11.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l11.py").write_text("# l11\n")
        _commit_all(wt, "wip")

        real_current_branch = _land_mod.current_branch

        def _fake(root: Path) -> Any:
            if str(root) == str(wt):
                return Err(GitError.GitFailed)
            return real_current_branch(root)

        monkeypatch.setattr(_land_mod, "current_branch", _fake)
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
