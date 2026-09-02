from datetime import date
from pathlib import Path
from typing import Any

import pytest

import frob.tickets._land_git_ops as _land_git_ops_mod
from frob.graph import build_graph
from frob.tickets import (
    Origin,
    TicketKind,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._land_git_ops import _splice_and_stage_archive
from frob.tickets._models import (
    LandError,
    Ticket,
)
from frob.tickets._store import (
    _serialize_ticket,
    archive_path,
    atomic_write,
    ledger_path,
    load_all,
    load_archive,
    v2_ticket_path,
    write_archive,
    write_ticket,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _git_init,
    _make_closeable,
    _run,
    _spec,
)

pytestmark = pytest.mark.heavy_subprocess


# frob:ticket T-1256
# frob:ticket T-2986
class TestArchiveV2:
    """Ledger v2 design section 4.3: `archive` on a v2-mode tree does a
    plain `git mv tickets/T-#### tickets/archive/T-####` per done/dropped
    ticket, zero content rewrite -- eliminating the T-0959 archive-clobber
    failure mode structurally (no destination FILE is ever rewritten,
    only a rename) rather than merely guarding it the way
    `TestArchiveSpliceDiscipline` above guards the v1 monofile path."""

    def _v2_ticket(
        self,
        root: Path,
        ticket_id: str,
        *,
        state: TicketState = TicketState.DONE,
        blocked_by: tuple[str, ...] = (),
    ) -> Path:
        # Writes ticket.md directly (mirrors TestRenumberOneV2's own
        # `_v2_ticket` helper in tests/test_tickets_collision.py) so an
        # empty tmp_path's first ticket lands under tickets/<id>/ instead
        # of tickets.md, which write_ticket's own _store_mode dispatch
        # would otherwise choose for a tree with no v2 dir yet.
        from frob.tickets._store import _serialize_ticket, v2_ticket_path

        ticket = Ticket(
            id=ticket_id,
            title=f"Ticket {ticket_id}",
            state=state,
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            created=date.today(),
            blocked_by=blocked_by,
            evidence=("tests/test_x.py::test_ok",),
            body="## Description\nx\n\n## Done report\n\ndone\n",
        )
        path = v2_ticket_path(root, ticket_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_serialize_ticket(ticket), encoding="utf-8")
        return path

    # frob:ticket T-1256
    def test_archive_moves_directory_via_git_mv_no_content_rewrite(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_archive.py::archive_v2 kind="unit"
        from frob.tickets import archive
        from frob.tickets._store import v2_archive_dir, v2_ticket_dir

        root = tmp_path / "repo"
        _git_init(root)
        path = self._v2_ticket(root, "T-0042")
        original_text = path.read_text(encoding="utf-8")
        _commit_all(root, "seed v2 ticket")

        result = archive(root)
        assert result.is_ok, result.err
        assert result.danger_ok == 1

        assert not v2_ticket_dir(root, "T-0042").exists()
        moved_path = v2_archive_dir(root, "T-0042") / "ticket.md"
        assert moved_path.exists()
        # Zero content rewrite: the moved file's bytes are byte-for-byte
        # identical to what git_mv_dir moved -- the AC's core claim.
        assert moved_path.read_text(encoding="utf-8") == original_text

        _run(["git", "add", "-A"], root)
        status = _run(["git", "status", "--porcelain"], root).stdout
        assert (
            "R  tickets/T-0042/ticket.md -> tickets/archive/T-0042/ticket.md" in status
        ), status

        # A second call is idempotent -- nothing left to archive.
        again = archive(root)
        assert again.is_ok and again.danger_ok == 0

    # frob:ticket T-2986
    # frob:doc docs/design/ledger-v2.md#43-archive-as-git-mv
    def test_archived_ticket_attachment_still_resolves_for_cov004(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2986 regression: archiving a v2 ticket that carries an
        `attachments[].path` in the self-contained `<id>/attachments/...`
        shape (`frob.tickets._reporting_attachments._record_attachment`'s
        convention) must rewrite that path to the post-move `archive/<id>/
        attachments/...` shape, so COV004 (`coverage_gate`, resolved via
        the fixed `Path("tickets") / attachment.path` `_cov004` uses) never
        fires on it afterward. Before the T-2986 fix, `archive_v2` moved
        the directory via `git_mv_dir` but left the recorded path pointing
        at the pre-move location, and COV004 read that as a missing/
        mismatched attachment on every archived ticket that ever had one
        (10 such findings measured live on main)."""
        # frob:tests src/frob/tickets/_archive.py::_rewrite_moved_attachment_paths kind="unit"  # noqa: E501
        import hashlib

        from frob.gates import CollectedTests, coverage_gate
        from frob.gitio import Diff
        from frob.tickets import Attachment, archive, load_queue
        from frob.tickets._store import v2_attachments_dir

        root = tmp_path / "repo"
        _git_init(root)
        ticket_path = self._v2_ticket(root, "T-0042")

        payload = b"evidence text\n"
        att_dir = v2_attachments_dir(root, "T-0042")
        att_dir.mkdir(parents=True)
        (att_dir / "01-x.txt").write_bytes(payload)
        sha256 = hashlib.sha256(payload).hexdigest()

        ticket = load_queue(root).danger_ok.tickets["T-0042"]
        attachment = Attachment(
            path="T-0042/attachments/01-x.txt", caption="x", sha256=sha256
        )
        updated = ticket.model_copy(update={"attachments": (attachment,)})
        v2_ticket_path(root, "T-0042").write_text(
            _serialize_ticket(updated), encoding="utf-8"
        )
        assert ticket_path.exists()
        _commit_all(root, "seed v2 ticket with attachment")

        result = archive(root)
        assert result.is_ok, result.err
        assert result.danger_ok == 1

        reloaded = load_queue(root)
        assert reloaded.is_ok, reloaded.err
        archived_ticket = reloaded.danger_ok.tickets["T-0042"]
        assert len(archived_ticket.attachments) == 1
        rewritten_path = archived_ticket.attachments[0].path
        assert rewritten_path == "archive/T-0042/attachments/01-x.txt", rewritten_path
        # The fixed COV004 resolution shape (`_cov004`'s own convention).
        assert (root / "tickets" / rewritten_path).exists()

        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        # _cov004 resolves `Path("tickets") / attachment.path` against the
        # process CWD, not `root` (matches `test_cov004_matching_sha_is_
        # clean`'s own precedent in tests/test_gates.py).
        monkeypatch.chdir(root)
        violations = coverage_gate(root, snapshot, reloaded.danger_ok, diff, tests)
        assert not any(v.rule == "COV004" for v in violations), violations

    # frob:ticket T-1258
    # frob:doc docs/design/ledger-v2.md#43-archive-as-git-mv
    def test_first_ever_archive_uses_real_git_mv_not_rename_fallback(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_store.py::git_mv_dir kind="unit"
        # Chain-review fix: the VERY FIRST archive of a v2 repo (before
        # `tickets/archive/` has ever existed) used to silently take
        # `git_mv_dir`'s os.rename fallback -- `git mv` on a directory
        # refuses when the destination's PARENT does not exist yet, which
        # is exactly true on a repo's first-ever archive. Pre-creating the
        # parent (this fix) makes `git mv` itself succeed, so the fallback
        # log line must never fire here.
        from frob.tickets import archive

        root = tmp_path / "repo"
        _git_init(root)
        assert not (root / "tickets" / "archive").exists()
        self._v2_ticket(root, "T-0043")
        _commit_all(root, "seed v2 ticket")

        with caplog.at_level("DEBUG", logger="frob.tickets._store"):
            result = archive(root)
        assert result.is_ok, result.err
        assert result.danger_ok == 1
        assert "falling back to os.rename" not in caplog.text

    # frob:ticket T-1256
    def test_archive_v2_regression_two_sided_divergence_no_clobber(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_archive.py::archive_v2 kind="unit"
        # Reproduces the T-0959 incident SHAPE (two branches each archive a
        # DIFFERENT ticket, then merge) against the v2 path: since each
        # archived ticket is its own disjoint git path, a real git merge
        # unions both sides with no custom splice code and no lost block --
        # unlike the v1 monofile path TestArchiveSpliceDiscipline guards.
        from frob.tickets import archive
        from frob.tickets._store import load_all, load_archive, write_ticket

        root = tmp_path / "repo"
        _git_init(root)
        self._v2_ticket(root, "T-0100")
        # T-0200 starts QUEUED (not archive-eligible yet) -- it only
        # becomes done+archived on the WORKTREE side, after main has
        # already branched and archived T-0100 -- the two-sided
        # divergence shape.
        self._v2_ticket(root, "T-0200", state=TicketState.QUEUED)
        _commit_all(root, "seed two v2 tickets")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "feature-archive", str(wt)], root)

        # Main archives T-0100 only, after the worktree branched.
        main_archived = archive(root)
        assert main_archived.is_ok and main_archived.danger_ok == 1
        _commit_all(root, "main archives T-0100")

        # The worktree, unaware of main's sweep, closes AND independently
        # archives T-0200 -- the exact two-sided-divergence shape.
        wt_loaded = load_all(wt)
        assert wt_loaded.is_ok
        wt_ticket = wt_loaded.danger_ok["T-0200"].model_copy(
            update={"state": TicketState.DONE}
        )
        assert write_ticket(wt, wt_ticket).is_ok
        # The worktree's own checkout still has T-0100 as active+done too
        # (its branch point predates main's archive commit) -- archiving
        # here independently re-archives T-0100 AND T-0200, the literal
        # T-0959 double-archive shape: both sides archive T-0100.
        wt_archived = archive(wt)
        assert wt_archived.is_ok and wt_archived.danger_ok == 2
        _commit_all(wt, "worktree closes and archives T-0200 (and re-archives T-0100)")

        merge_result = _run(["git", "merge", "--no-edit", "feature-archive"], root)
        assert merge_result.returncode == 0, merge_result.stderr

        active = load_all(root)
        assert active.is_ok
        assert "T-0100" not in active.danger_ok
        assert "T-0200" not in active.danger_ok

        archived = load_archive(root)
        assert archived.is_ok
        assert "T-0100" in archived.danger_ok, "main's own archive sweep was lost"
        assert "T-0200" in archived.danger_ok, (
            "the worktree's archive sweep was clobbered by main's -- the "
            "T-0959 shape this test guards against"
        )

    # frob:ticket T-1256
    def test_archived_v2_ticket_still_resolves_as_blocker(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_archive.py::load_queue kind="unit"
        from frob.tickets import archive, load_queue

        root = tmp_path / "repo"
        _git_init(root)
        self._v2_ticket(root, "T-0400")
        self._v2_ticket(
            root, "T-0500", state=TicketState.QUEUED, blocked_by=("T-0400",)
        )
        _commit_all(root, "seed blocker pair")

        archived_count = archive(root)
        assert archived_count.is_ok and archived_count.danger_ok == 1

        queue = load_queue(root)
        assert queue.is_ok, queue.err
        merged = queue.danger_ok.tickets
        assert "T-0400" in merged, "archived blocker no longer resolves"
        assert merged["T-0400"].state == TicketState.DONE
        assert "T-0500" in merged
        assert merged["T-0500"].blocked_by == ("T-0400",)

    # frob:ticket T-1491
    def test_v2_draft_survives_a_concurrent_worktree_restore(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_archive.py::TestArchiveV2.test_v2_draft_survives_a_concurrent_worktree_restore  # noqa: E501
        """Regression for the T-1115/T-1126/T-1127/T-1128 draft-death
        shape (T-1259 acceptance[5], carried forward by this ticket): a
        draft ticket filed into a worktree, followed by the section 10b
        ledger-restore recipe (`git checkout main -- <ledger>`) another
        ticket in the SAME worktree runs before finalizing, used to WIPE
        the draft outright on the v1 monofile path -- because the whole
        ledger lives in one file, restoring main's copy of that file
        discards anything the worktree alone had written to it,
        including a draft nobody else has seen yet.

        On the v2 per-ticket-file path this class is structurally
        impossible: a draft is its own disjoint `tickets/T-draft-<hex>/
        ticket.md` file, never a section inside a shared ledger file, so
        there is no single-file "restore to main's copy" operation that
        could ever touch it. This reproduces the exact incident shape --
        main advances (landing an unrelated ticket) while a worktree
        independently files a draft, then the worktree does the
        equivalent of the section 10b restore (checking out main's
        ledger-relevant state) before its own final commit -- and asserts
        the draft file is untouched by either the restore or a
        subsequent merge back into main."""
        from frob.tickets import load_all
        from frob.tickets._store import v2_ticket_dir

        root = tmp_path / "repo"
        _git_init(root)
        self._v2_ticket(root, "T-0900", state=TicketState.QUEUED)
        _commit_all(root, "seed v2 repo")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "feature-draft", str(wt)], root)

        # Main advances independently (an unrelated ticket lands) after
        # the worktree branched off -- the same "main keeps moving while
        # you work" backdrop section 10b describes.
        main_ticket_path = self._v2_ticket(root, "T-1000", state=TicketState.QUEUED)
        assert main_ticket_path.exists()
        _commit_all(root, "main files an unrelated ticket")

        # The worktree, unaware of main's advance, files a brand-new
        # DRAFT (never seen by main, never committed anywhere else) --
        # the exact "original draft" this incident class loses.
        draft_path = self._v2_ticket(wt, "T-draft-deadbeef", state=TicketState.QUEUED)
        assert draft_path.exists()

        # Section 10b's restore recipe, applied here: bring the
        # worktree's tracked ledger-relevant state in line with main's
        # BEFORE the worktree's own final commit. On v1 this is
        # `git checkout main -- tickets.md`, which overwrites the whole
        # shared file and any draft section it held. On v2 there is no
        # single shared ledger file to check out -- the closest
        # structural equivalent is `git checkout main -- tickets/` for
        # the tracked (committed) subtree, which cannot reach a file
        # that was never committed in the first place.
        checkout_result = _run(["git", "checkout", "main", "--", "tickets/T-1000"], wt)
        assert checkout_result.returncode == 0, checkout_result.stderr

        # The draft, never committed, is untouched by the restore --
        # still on disk, still readable.
        assert draft_path.exists()
        wt_loaded = load_all(wt)
        assert wt_loaded.is_ok, wt_loaded.err
        assert "T-draft-deadbeef" in wt_loaded.danger_ok

        _commit_all(wt, "worktree commits its draft alongside restored state")

        merge_result = _run(["git", "merge", "--no-edit", "feature-draft"], root)
        assert merge_result.returncode == 0, merge_result.stderr

        merged = load_all(root)
        assert merged.is_ok, merged.err
        assert "T-draft-deadbeef" in merged.danger_ok, (
            "the worktree's draft was lost across restore+merge -- the "
            "TICK002/TICK006 draft-death shape this test guards against"
        )
        assert "T-1000" in merged.danger_ok, "main's own ticket was lost"
        assert v2_ticket_dir(root, "T-draft-deadbeef").exists()


# frob:ticket T-0959
# frob:ticket T-1194
# frob:ticket T-1636
# frob:ticket T-1750
# frob:ticket T-2550
class TestArchiveSpliceDiscipline:
    """T-0959: `tickets-archive.md` used to ride along on whatever git's raw
    merge/checkout produced at land time, with no per-id splice discipline
    at all (unlike tickets.md's `_splice_and_stage`) -- a real incident
    (T-0703's land) staged a worktree's STALE tickets-archive.md wholesale,
    wiping 62 blocks a TICK003 sweep had added to main's archive after the
    worktree's own warmup merge. This regression-locks the acceptance
    criterion directly: a worktree whose archive predates a later archive
    sweep on main must never cause `land` to lose main's newly-archived
    blocks."""

    def test_splice_and_stage_archive_merges_by_id_never_overwrites(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_splice_and_stage_archive \
        # kind="unit"
        # `authoritative_text` carries one id, `other_text` carries a
        # DISJOINT second id -- a wholesale overwrite (the pre-T-0959 bug)
        # would keep only one side; the splice must keep both.
        checkout = tmp_path / "checkout"
        _git_init(checkout)
        atomic_write(ledger_path(checkout), "# Tickets\n\n")

        created = new_ticket(checkout, _spec("Authoritative side"))
        assert created.is_ok
        authoritative_text = ledger_path(checkout).read_text()
        authoritative_id = created.danger_ok.id

        other_ticket = created.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Other side"}
        )
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        atomic_write(ledger_path(other_dir), "# Tickets\n\n")
        assert write_ticket(other_dir, other_ticket).is_ok
        other_text = ledger_path(other_dir).read_text()

        result = _splice_and_stage_archive(checkout, authoritative_text, other_text)
        assert result.is_ok, result.err
        merged = archive_path(checkout).read_text()
        assert authoritative_id in merged
        assert "T-0002" in merged
        assert "Authoritative side" in merged
        assert "Other side" in merged

    def test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_splice_and_stage_archive \
        # kind="unit"
        # The T-0959 id-integrity backstop: if the merge somehow produced a
        # result missing an id `authoritative_text` carried, refuse loudly
        # rather than silently staging a lossy result. Forced by making
        # `_merge_ledger_tickets` itself drop the authoritative id, since a
        # real union merge structurally never does this on its own -- this
        # pins the GUARD, not a naturally-reachable input.
        checkout = tmp_path / "checkout"
        _git_init(checkout)
        atomic_write(ledger_path(checkout), "# Tickets\n\n")

        created = new_ticket(checkout, _spec("Must survive"))
        assert created.is_ok
        authoritative_text = ledger_path(checkout).read_text()
        other_text = "# Tickets\n\n"

        def _drop_everything(
            ours: dict[str, Any], theirs: dict[str, Any], **_kwargs: Any
        ) -> dict[str, Any]:
            return {}

        monkeypatch.setattr(
            _land_git_ops_mod, "_merge_ledger_tickets", _drop_everything
        )

        result = _splice_and_stage_archive(checkout, authoritative_text, other_text)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    # frob:ticket T-1750
    def test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_splice_and_stage_archive \
        # kind="unit"
        # Two tickets that will be archived on MAIN, AFTER the worktree
        # branches off -- the exact T-0703 incident shape: the worktree's
        # warmup merge happens before the archive sweep, so its own
        # tickets-archive.md never sees it.
        first = new_ticket(repo, _spec("First to archive"), no_commit=True)
        second = new_ticket(repo, _spec("Second to archive"), no_commit=True)
        assert first.is_ok and second.is_ok
        first_id, second_id = first.danger_ok.id, second.danger_ok.id
        _commit_all(repo, "file two tickets that will later be archived")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-archive-splice", str(wt)], repo)

        # The worktree ALSO independently archives its own sibling ticket
        # (a genuine two-sided divergence on tickets-archive.md, the shape
        # that actually exercises a real merge/splice decision rather than
        # a one-sided fast-forward git can resolve on its own).
        from frob.tickets import archive

        sibling = new_ticket(
            wt, _spec("Sibling archived in worktree", scope=("src/sib.py",))
        )
        assert sibling.is_ok
        sibling_id = sibling.danger_ok.id
        _make_closeable(wt, sibling_id)
        assert transition(wt, sibling_id, TicketState.DONE).is_ok
        # T-1750: `repo` is live from `wt`'s point of view -- force past
        # the new in-flight-worktree refusal (the scenario below is
        # exactly what that guard exists to flag in real operation; this
        # test forces past it deliberately to prove splice correctness).
        wt_archived_count = archive(wt, force=True)
        assert wt_archived_count.is_ok and wt_archived_count.danger_ok == 1
        _commit_all(wt, "worktree archives its own sibling ticket")

        # Main independently closes and archives BOTH tickets AFTER the
        # worktree branched.
        for ticket_id in (first_id, second_id):
            _make_closeable(repo, ticket_id)
            assert transition(repo, ticket_id, TicketState.DONE).is_ok
        archived_count = archive(repo, force=True)
        assert archived_count.is_ok and archived_count.danger_ok == 2
        _commit_all(repo, "archive two tickets (sweep happens after worktree branch)")

        # Confirm the worktree's own archive really is stale at this point
        # -- the precondition the incident needs.
        wt_archive_before = load_archive(wt)
        assert wt_archive_before.is_ok
        assert first_id not in wt_archive_before.danger_ok
        assert second_id not in wt_archive_before.danger_ok

        # Land unrelated worktree work.
        created = new_ticket(
            wt, _spec("Unrelated archive-splice land", scope=("src/unrelated3.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated3.py").write_text("# unrelated\n")
        _commit_all(wt, "unrelated worktree work")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        archived = load_archive(repo)
        assert archived.is_ok
        assert first_id in archived.danger_ok, (
            f"{first_id} wiped from tickets-archive.md by land (T-0959)"
        )
        assert second_id in archived.danger_ok, (
            f"{second_id} wiped from tickets-archive.md by land (T-0959)"
        )
        # The worktree's own genuinely new archive addition must not be
        # silently dropped either -- a raw git merge/checkout with no
        # per-id splice discarded this side entirely before the fix.
        assert sibling_id in archived.danger_ok, (
            f"worktree's own archived sibling {sibling_id} was dropped by land (T-0959)"
        )

    # frob:ticket T-1194
    # frob:ticket T-1636
    # frob:ticket T-2550
    def test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_ledger_merge.py::_merge_ledger_tickets \
        # kind="integration"
        # frob:tests src/frob/tickets/_land_ledger_merge.py::_resolve_divergence \
        # kind="integration"
        # T-1636/T-2550: both bindings above are exercised only through the
        # full `land(..., dry_run=True)` pipeline several call-hops deep,
        # not a direct call a static call-graph can see -- COV006's own
        # kind="integration" trust-at-face-value convention. `_merge_ledger_
        # tickets` was previously kind="unit" here despite the same shape as
        # its own sibling directive one line below -- a misclassification
        # (T-2550 trace 3), corrected to match.
        # T-1154 (3rd occurrence of the wrong-side-merge class, see this
        # ticket's own Done report): a ticket archived on BOTH main and the
        # worktree, same state (done) and same richness (both carry a Done
        # report, same evidence count) -- so pre-T-1154, `_newer`'s tier-3
        # fallback ties and arbitrarily picks `theirs` (the worktree side).
        # Main then makes a REAL content edit to its own archived copy (the
        # T-1143 shape: an evidence-path text migration inside the Done
        # report) while the worktree's copy sits untouched since branch --
        # unchanged-since-branch means the worktree made no deliberate edit
        # and has no claim, so main's edit must survive the land, not be
        # silently reverted.
        from frob.tickets import archive

        archived_ticket = new_ticket(
            repo, _spec("Migrated evidence path", scope=("src/parse.py",))
        )
        assert archived_ticket.is_ok
        aid = archived_ticket.danger_ok.id
        _make_closeable(repo, aid)
        assert transition(repo, aid, TicketState.DONE).is_ok
        assert archive(repo).is_ok
        _commit_all(repo, "archive the ticket that will later be content-edited")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-content-edit", str(wt)], repo)
        # The worktree's own copy of the archived block is byte-identical
        # to the merge-base at this point -- it never touches it.
        wt_archive_before = archive_path(wt).read_text()

        # Main makes a real, deliberate content edit to the SAME archived
        # block -- same state, same evidence count (richness tied), only
        # the Done-report text itself changes (the T-1143 shape: an
        # evidence-path migration).
        main_archived = load_archive(repo)
        assert main_archived.is_ok
        edited = main_archived.danger_ok[aid].model_copy(
            update={
                "body": main_archived.danger_ok[aid].body.replace(
                    "evidence attached", "evidence attached (src/parse/mod.py)"
                )
            }
        )
        assert write_archive(repo, {**main_archived.danger_ok, aid: edited}).is_ok
        _commit_all(repo, "main migrates the evidence path inside the archived block")
        assert "src/parse/mod.py" in archive_path(repo).read_text()

        # Land unrelated worktree work -- exercises the real land path's
        # archive splice, not a hand-called unit helper.
        created = new_ticket(
            wt, _spec("Unrelated content-edit land", scope=("src/unrelated4.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated4.py").write_text("# unrelated\n")
        _commit_all(wt, "unrelated worktree work")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        post_land_archive = archive_path(repo).read_text()
        assert "src/parse/mod.py" in post_land_archive, (
            f"{aid}: main's evidence-path migration reverted by land "
            "(T-1154 wrong-side-merge regression)"
        )
        assert wt_archive_before != post_land_archive


# frob:ticket T-1194
# frob:ticket T-1750
class TestArchiveResurrection:
    """Reviewer bug 2: `splice_ledger` only read active tickets.md, never
    tickets-archive.md -- an id archived on main after the branch point
    would survive the ours-union and land back into main's active ledger,
    resurrecting a duplicate-id class a human previously had to resolve by
    hand at merge time (T-0176's own 0bb02cf merge). `land` must never
    reintroduce an already-archived id."""

    # frob:ticket T-1194
    # frob:ticket T-1750
    def test_archived_id_never_resurrected(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
        # Seed a ticket that exists (stale, still active) in the worktree's
        # ledger view, then archive it on MAIN after the branch point --
        # simulating a branch whose base predates the archive.
        stale = new_ticket(repo, _spec("Will be archived"), no_commit=True)
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

        # T-1750: `wt` is live at this point (deliberately, the scenario
        # this test proves splice safety for) -- force past the new
        # in-flight-worktree refusal to keep exercising splice
        # correctness, the property this test actually checks.
        archived_count = archive(repo, force=True)
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
