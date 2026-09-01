import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok, Result

import frob.tickets._land as _land_mod
import frob.tickets._land_squash as _land_squash_mod
from frob.gates import PreworkSweep, load_prework, record_prework, scope_digest
from frob.gitio import GitError
from frob.graph import build_graph
from frob.tickets import (
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import (
    LandError,
)
from frob.tickets._store import (
    atomic_write,
    ledger_path,
    load_all,
    v2_ticket_path,
    write_ticket,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _failing_run_argv,
    _git_init,
    _make_closeable,
    _run,
    _seed_v2_ticket,
    _spec,
    _status_ignoring_frob,
)

pytestmark = pytest.mark.heavy_subprocess



# frob:ticket T-1721
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
        assert _status_ignoring_frob(repo) == ""
        assert _status_ignoring_frob(wt) == ""

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

    # frob:ticket T-1805
    def test_non_version_pyproject_edit_survives_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLand.test_non_version_pyproject_edit_survives_land  # noqa: E501
        """T-1805 regression, end to end through the real `land()` entry
        point: a ticket whose ONLY change is a non-version
        `pyproject.toml` field (an optional-dependencies pin -- the exact
        shape T-1508's real, four-times-dropped z3-solver pin took) must
        still be on main after landing. Before the fix,
        `_reset_release_artifacts_to_pre_land`'s whole-file `git checkout`
        discarded this edit unconditionally, and `land()` still reported
        `Ok`/`verified=True` -- silent data loss with a green result."""
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n\n'
            "[project.optional-dependencies]\n"
            'smt = ["z3-solver>=4.13"]\n',
            encoding="utf-8",
        )
        _commit_all(repo, "seed pyproject.toml")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-pin", str(wt)], repo)
        created = new_ticket(wt, _spec("Pin z3-solver", scope=("pyproject.toml",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n\n'
            "[project.optional-dependencies]\n"
            'smt = ["z3-solver>=4.13,<4.15.5"]\n',
            encoding="utf-8",
        )
        _commit_all(wt, "pin z3-solver upper bound")

        # `bump_version` supplied (Ok(None): no new version needed) so the
        # reset path actually runs, same as a real `frob ticket land`
        # invocation always supplying its REL001 callback.
        def _no_bump_needed(
            _root: Path, _ticket: Any, _final_id: str
        ) -> Result[str | None, LandError]:
            return Ok(None)

        result = land(repo, tid, wt, dry_run=False, bump_version=_no_bump_needed)
        assert result.is_ok, result.err

        landed_pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
        assert "z3-solver>=4.13,<4.15.5" in landed_pyproject
        # the version field itself is untouched -- this is a field-scoped
        # reset, not a bypass of T-1760's own reset entirely.
        assert 'version = "0.1.0"' in landed_pyproject

    # frob:ticket T-1721
    def test_sibling_evidence_rebind_carried_forward_end_to_end(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLand.test_sibling_evidence_rebind_carried_forward_end_to_end  # noqa: E501
        """The real T-1637 field incident, reproduced end to end through
        the actual `land()` entry point (not just the splice primitive):
        a sibling ticket B is already DONE on main; in the SAME worktree
        that is landing ticket A, an agent rebinds B's evidence (a
        legitimate correction, e.g. after a rename -- no state change).
        Before T-1721, `land(repo, A, wt)` silently dropped B's rebind
        because `_splice_only_ticket`'s T-0479 sibling-scoping had no way
        to tell "B is merely stale" from "B was genuinely, deliberately
        edited". After T-1721, main's copy of B must carry the rebind."""
        created_b = new_ticket(repo, _spec("Sibling B, already done"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        _make_closeable(repo, tid_b)
        assert transition(repo, tid_b, TicketState.DONE, covers_scope=True).is_ok
        _commit_all(repo, f"close {tid_b}")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sibling-rebind", str(wt)], repo)

        created_a = new_ticket(wt, _spec("Landing A", scope=("src/a.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        _make_closeable(wt, tid_a)
        (wt / "src" / "a.py").write_text("# a\n")

        # The T-1637 shape: in the SAME worktree, rebind B's evidence to a
        # renamed test -- main never touches B again after this point.
        loaded_b = load_all(wt).danger_ok[tid_b]
        rebound_b = loaded_b.model_copy(
            update={"evidence": ("tests/test_x.py::TestFoo::test_renamed",)}
        )
        assert write_ticket(wt, rebound_b).is_ok
        _commit_all(wt, f"rebind {tid_b} evidence")

        result = land(repo, tid_a, wt, dry_run=False)
        assert result.is_ok, result.err

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[tid_b].evidence == (
            "tests/test_x.py::TestFoo::test_renamed",
        )

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
        created = new_ticket(wt, _spec("Not ready"), no_commit=True)
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(wt, "wip")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Nothing must have been touched -- close validation runs BEFORE any
        # git mutation, so main and the worktree are exactly as found.
        assert _status_ignoring_frob(repo) == ""
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""



# frob:ticket T-2220
class TestRecordLandCommit:
    """T-2220: a landed ticket's landing commit is resolvable after the
    fact -- via its own `land_commit` field for a `--plan` land (`git log
    --grep` structurally cannot reach that case, no ticket id in the
    subject at all) and, since T-3543, via `derive_land_commit_by_grep`
    for a per-ticket squash-apply land (the field is no longer written at
    all there -- see `_finish_real_land_report`'s own T-3543 docstring)."""

    # frob:ticket T-2220
    # frob:tests tests/test_ticket_land.py::TestRecordLandCommit.test_land_commit_is_derivable_with_no_follow_up_commit  # noqa: E501
    def test_land_commit_is_derivable_with_no_follow_up_commit(
        self, repo: Path
    ) -> None:
        """T-3543 (was MUST-FAIL-FIRST acceptance criterion 1 for T-2220's
        follow-up-commit design; superseded): landing a ticket no longer
        writes `land_commit` at all via a trailing bookkeeping commit --
        `root`'s HEAD after `land()` returns IS `report.commit_sha`
        itself, exactly one commit, and `derive_land_commit_by_grep`
        recovers that same sha from the commit's own subject on demand."""
        from frob.tickets._land_squash import derive_land_commit_by_grep

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-record", str(wt)], repo)
        created = new_ticket(wt, _spec("Add thingamajig", scope=("src/t.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "t.py").write_text("# thingamajig\n")
        _commit_all(wt, "add thingamajig")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.commit_sha is not None

        # exactly ONE commit for this land -- HEAD IS the landing commit,
        # not one commit ahead of it (the old follow-up-commit shape).
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == report.commit_sha
        )

        landed = load_all(repo)
        assert landed.is_ok
        ticket = landed.danger_ok[report.final_id]
        assert ticket.land_commit is None

        derived = derive_land_commit_by_grep(repo, report.final_id)
        assert derived == report.commit_sha

    # frob:ticket T-2274
    # frob:tests tests/test_ticket_land.py::TestRecordLandCommit.test_record_land_commit_never_absorbs_a_bystanders_dirty_file  # noqa: E501
    def test_record_land_commit_never_absorbs_a_bystanders_dirty_file(
        self, v2_repo: Path
    ) -> None:
        """MUST-FAIL-FIRST (T-2274): the T-2256 incident -- a concurrent
        land's own uncommitted, unrelated edit to `_land.py` was sitting
        in the shared root when `_record_land_commit`'s bookkeeping step
        ran, and a blanket `git add -A` scooped it into that commit,
        publishing a stranger's mid-edit diff to main with zero ticket/
        evidence trail attached to the ticket the bookkeeping commit
        named. Seed the identical shape here -- an unrelated TRACKED
        file dirtied in `v2_repo` right before `_record_land_commit`
        runs -- and assert the resulting commit's diff never contains it,
        while the bystander edit survives, still uncommitted, afterward
        (never silently discarded either)."""
        tid = "T-3000"
        _seed_v2_ticket(v2_repo, tid, scope=("src/feature.py",))
        _commit_all(v2_repo, "seed T-3000")
        fake_land_sha = _run(["git", "rev-parse", "HEAD"], v2_repo).stdout.strip()

        bystander = v2_repo / "src" / "feature.py"
        original = bystander.read_text()
        bystander.write_text(original + "# a concurrent land's own dirty edit\n")

        new_sha = _land_squash_mod._record_land_commit(v2_repo, tid, fake_land_sha)

        assert new_sha is not None, "record_land_commit must still make its own commit"
        head_files = _run(
            ["git", "show", "--stat", "--format=", new_sha], v2_repo
        ).stdout
        assert "feature.py" not in head_files
        assert str(v2_ticket_path(v2_repo, tid).relative_to(v2_repo)) in head_files

        # The bystander's edit was never absorbed -- it is still sitting
        # there, uncommitted, exactly as a genuinely concurrent process's
        # own in-progress work would be.
        status = _run(["git", "status", "--porcelain", "--", "src/feature.py"], v2_repo)
        assert "feature.py" in status.stdout

        reloaded = load_all(v2_repo)
        assert reloaded.is_ok
        assert reloaded.danger_ok[tid].land_commit == fake_land_sha

    # frob:ticket T-2220
    # frob:tests tests/test_ticket_land.py::TestRecordLandCommit.test_plan_land_finalized_ticket_is_resolvable_by_ticket_id  # noqa: E501
    def test_plan_land_finalized_ticket_is_resolvable_by_ticket_id(
        self, repo: Path, tmp_path: Path
    ) -> None:
        """Acceptance criterion 4: a `--plan` land's own commit subject
        (`chore(tickets): land --plan finalize ...`) carries no ticket id
        at all -- a `git log --grep "land T-####"` cannot match it. The
        finalized ticket's own `land_commit` field must still resolve it,
        to `report.merge_commit` (the ONLY sha this land makes before the
        finalize commit -- no self-reference problem here, unlike the
        per-ticket `land()` path above, since `merge_commit` already
        exists as a real commit by the time finalize writes it)."""
        from frob.tickets._land import land_plan

        worktree = repo.parent / "design-wt"
        _run(["git", "worktree", "add", str(worktree), "-b", "design", "main"], repo)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        draft = new_ticket(worktree, _spec("A design-phase draft ticket")).danger_ok
        assert draft.id.startswith("T-draft-")
        _commit_all(worktree, "docs: add new.md + file draft")

        result = land_plan(repo, worktree)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.merge_commit is not None
        _old_id, new_id = report.finalized[0]

        loaded = load_all(repo)
        assert loaded.is_ok
        landed_ticket = loaded.danger_ok[new_id]
        assert landed_ticket.land_commit == report.merge_commit

        # The defect this closes: the OLD grep pattern
        # (`_find_landing_commit`'s pre-T-2220 `git log --grep "land
        # {ticket_id}([^0-9]|$)"`) requires the literal substring
        # "land T-####" -- this commit's subject names `new_id` only via
        # "-> T-####" (the finalize mapping), never as "land T-####", so
        # the old grep genuinely could not have found it even though the
        # id IS textually present somewhere in the subject.
        import re as _re

        finalize_sha = report.commit_sha
        assert finalize_sha is not None
        subject = _run(
            ["git", "log", "-1", "--format=%s", finalize_sha], repo
        ).stdout.strip()
        assert "--plan" in subject
        assert _re.search(rf"land {new_id}([^0-9]|$)", subject) is None


class TestPlannedStateAutoAdvanceOnLand:
    """T-0821: a ticket left in PLANNED (never run through `frob ticket
    start`, or reverted there by a section-10b ledger restore) but
    otherwise closeable (evidence + Done report) must land straight to
    DONE, not die `InvalidTransition` after main already merged."""

    # frob:ticket T-0821
    # frob:tests tests/test_ticket_land.py::TestPlannedStateAutoAdvanceOnLand.test_planned_ticket_with_full_evidence_lands_to_done  # noqa: E501
    def test_planned_ticket_with_full_evidence_lands_to_done(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-planned", str(wt)], repo)
        created = new_ticket(wt, _spec("Add sprocket", scope=("src/sprocket.py",)))
        assert created.is_ok
        tid = created.danger_ok.id

        # Left in PLANNED (`frob ticket start`'s first transition), never
        # advanced to IN_PROGRESS -- but evidence and a Done report are
        # both present, exactly the T-0799/T-0752/T-0815 incident shape.
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok
        assert load_all(wt).danger_ok[tid].state == TicketState.PLANNED

        (wt / "src" / "sprocket.py").write_text("# new sprocket\n")
        _commit_all(wt, "add sprocket")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE



class TestWarnIfNativeStale:
    """T-0248: `land` warns loudly (without blocking) when the just-landed
    tree's native source outpaces its own built extension -- the T-0166
    review incident class."""

    def test_real_land_logs_stale_native_warning(
        self,
        repo: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests src/frob/tickets/_land_release.py::_warn_if_native_stale \
        # kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native", str(wt)], repo)
        created = new_ticket(wt, _spec("Grammar change", scope=("src/grammar.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "grammar.py").write_text("# grammar change\n")
        _commit_all(wt, "grammar change")

        monkeypatch.setattr(
            "frob.strata._native_staleness.stale_native_warning",
            lambda root: "STALE NATIVE: fake grammar-ahead-of-native fixture",
        )

        with caplog.at_level("WARNING", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert any("STALE NATIVE" in record.message for record in caplog.records)

    def test_real_land_no_warning_when_native_fresh(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_land_release.py::_warn_if_native_stale \
        # kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-fresh", str(wt)], repo)
        created = new_ticket(wt, _spec("Non-native change", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "other.py").write_text("# unrelated change\n")
        _commit_all(wt, "unrelated change")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert not any("STALE NATIVE" in r.message for r in caplog.records)


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
        # aborted -- no half-applied merge state left behind. Mutation
        # evidence's own derived_state_lock legitimately leaves
        # `.frob/derived.lock` behind (same scratch-artifact class as
        # `.frob/land.lock`, T-0577) -- filter `.frob/` like every other
        # such assertion in this file.
        assert _status_ignoring_frob(wt) == ""

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

        # T-3121 (T-3144 fallout): the squash-merge now runs against a
        # DISPOSABLE stage worktree (compose_squash_in_disposable_
        # worktree), a path under a fresh tempdir, never `str(repo)` --
        # matching on `"merge"`/`"--squash"` alone is now the only way to
        # target this call; `str(repo) in argv` never matches it post
        # T-3121 and silently made this predicate never fire.
        _failing_run_argv(
            monkeypatch,
            lambda argv: "merge" in argv and "--squash" in argv,
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

        # T-3121 (T-3144 fallout): the "final landing commit" is no
        # longer an in-tree `git commit` -- `_publish_squash_apply`
        # (T-3121's fold + CAS replacement) folds the disposable stage
        # into a commit object via `git commit-tree` against `repo`
        # (`fold_worktree_into_commit`, `frob.tickets._land_compose`),
        # never a bare `"commit"` argv token, so the old predicate never
        # matched post T-3121.
        _failing_run_argv(
            monkeypatch,
            lambda argv: str(repo) in argv and "commit-tree" in argv,
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

        # T-1179: land's own finalize step routes through
        # `finalize_draft_for_land` (main-fresh id ceiling), not plain
        # `finalize_draft` -- patch the symbol land actually calls.
        monkeypatch.setattr(
            tickets_mod,
            "finalize_draft_for_land",
            lambda *a, **k: Err(TicketError.NotFound),
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

        # T-1186: the worktree's own branch lookup this test targets lives
        # in `_land_finalize._land_squash_apply` now, not `_land.py`'s
        # `current_branch(root)` (that call is the MAIN repo's branch,
        # always `repo` here -- never `wt`).
        real_current_branch = _land_squash_mod.current_branch

        def _fake(root: Path) -> Any:
            if str(root) == str(wt):
                return Err(GitError.GitFailed)
            return real_current_branch(root)

        monkeypatch.setattr(_land_squash_mod, "current_branch", _fake)
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed




class TestPreworkSweepRefresh:
    """T-0236: an unrelated main landing that touches a ticket's scope globs
    moves its recorded pre-work sweep's scope digest out from under it --
    three consecutive reviews (T-0181, T-0203, T-0202) REJECTed solely or
    partly on this stale-PRE001 churn. `land` must refresh the sweep
    post-merge, pre-close so a ticket left in-progress after a landing
    failure (or a reviewer's `frob check --ticket` run in the interim)
    never sees a sweep stale for a reason outside the ticket's own control."""

    def test_land_refreshes_stale_sweep_after_unrelated_main_change(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_refresh_prework_sweep kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sweep", str(wt)], repo)

        created = new_ticket(wt, _spec("Sweep refresh", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Record a deliberately stale sweep -- this mirrors what `frob
        # ticket start` recorded before main moved.
        stale = PreworkSweep(
            date=date.today(), dup_findings=0, xref_hits=(), digest="stale-digest"
        )
        assert record_prework(wt, tid, stale).is_ok

        # main lands an UNRELATED commit that happens to touch the ticket's
        # scoped file -- the drift class this ticket is about.
        (repo / "src" / "feature.py").write_text("# landed feature, updated\n")
        _commit_all(repo, "unrelated main-side edit to a scope-owned file")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        # The sweep recorded in the worktree during land's post-merge,
        # pre-close refresh must reflect the POST-merge tree, not the stale
        # one recorded before `land` ran.
        refreshed = load_prework(wt, tid)
        assert refreshed is not None
        assert refreshed.digest != "stale-digest"

        graph = build_graph(wt, wt / ".frob" / "cache.db")
        assert graph.is_ok
        assert refreshed.digest == scope_digest(("src/feature.py",), graph.danger_ok)

    def test_sweep_refresh_failure_does_not_block_landing(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_refresh_prework_sweep kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sweep-fail", str(wt)], repo)

        created = new_ticket(wt, _spec("Sweep refresh failure", scope=("src/x.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "x.py").write_text("# x\n")
        _commit_all(wt, "add x")

        import frob.gates as gates_mod
        from frob.gates._models import GateError

        monkeypatch.setattr(
            gates_mod, "sweep_ticket", lambda *a, **k: Err(GateError.WriteFailed)
        )

        # `land` must still succeed -- the sweep refresh is best-effort and
        # is not what gates landing (close's own evidence/Done-report checks
        # are).
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err



# frob:ticket T-2550
class TestLandCompleteness:
    """T-0463: `land` must bring the worktree's COMPLETE changeset (tracked
    edits + untracked new files + deletions), not just what a `git diff
    HEAD` patch would see, and must assert this BEFORE committing -- the
    root cause of the T-0448 `docs/modules/render.md` loss was a surgical
    git-diff/patch land that silently dropped an untracked file with no
    error."""

    # frob:ticket T-2550
    def test_land_brings_tracked_edit_untracked_new_file_and_deletion(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_squash.py::_assert_land_complete kind="unit"
        # frob:tests src/frob/tickets/_land_squash.py::_worktree_full_changeset \
        # kind="integration"
        # T-2550: this binding is exercised only through the full `land()`
        # pipeline here (TestLandSquashHelpersMutationCoverage below calls
        # `_worktree_full_changeset` directly and keeps kind="unit" for its
        # own binding) -- same COV006 kind="integration" trust-at-face-value
        # convention as this file's other land-pipeline findings.
        # `doomed.py` must exist BEFORE the worktree branches, so its
        # deletion has a real net effect relative to main (a file created
        # and deleted within the same branch history nets to "no change"
        # against main and would not exercise the deletion path at all).
        (repo / "src" / "doomed.py").write_text("# present before branch\n")
        _commit_all(repo, "add doomed.py (present before branch)")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-complete", str(wt)], repo)
        created = new_ticket(
            wt,
            _spec(
                "Complete changeset",
                scope=("src/feature.py", "src/brand_new.py", "src/doomed.py"),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # (a) a tracked EDIT to a file main already has. (b) an uncommitted
        # DELETION of a file main already has -- exercises the wip-commit's
        # `git add -A` staging a deletion.
        (wt / "src" / "feature.py").write_text("# tracked edit\n")
        (wt / "src" / "doomed.py").unlink()

        # (c) an UNTRACKED new file, left uncommitted at land time -- the
        # exact T-0448 incident class.
        (wt / "src" / "brand_new.py").write_text("# brand new, never committed\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        assert (repo / "src" / "feature.py").read_text() == "# tracked edit\n"
        assert (repo / "src" / "brand_new.py").exists()
        assert not (repo / "src" / "doomed.py").exists()

        # The completeness assertion actually ran and saw all three paths,
        # and every one of them landed in the final commit.
        assert "src/feature.py" in report.worktree_changeset
        assert "src/brand_new.py" in report.worktree_changeset
        assert "src/doomed.py" in report.worktree_changeset
        for path in report.worktree_changeset:
            assert path in report.files_changed

    def test_incomplete_land_fails_loudly_and_commits_nothing(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/tickets/_land_squash.py::_assert_land_complete kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-incomplete", str(wt)], repo)
        created = new_ticket(wt, _spec("Incomplete", scope=("src/gadget2.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "gadget2.py").write_text("# gadget2\n")
        _commit_all(wt, "add gadget2")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # Simulate a dropped file: the worktree "changed" a path the
        # squash-apply never actually staged (the T-0448 incident, forced
        # deterministically instead of relying on a real patch-based land
        # to reproduce it).
        real_changeset = _land_squash_mod._worktree_full_changeset

        def _fake_changeset(worktree: Path, main_branch_name: str) -> Any:
            result = real_changeset(worktree, main_branch_name)
            if result.is_err:
                return result
            return Ok(result.danger_ok | {"src/phantom_dropped.py"})

        monkeypatch.setattr(
            _land_squash_mod, "_worktree_full_changeset", _fake_changeset
        )

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        assert "src/phantom_dropped.py" in caplog.text

        # The commit must never have happened, and the squash must have
        # been fully unwound -- root is exactly as found, not partially
        # staged or partially committed.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    # frob:ticket T-2550
    def test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_squash.py::_worktree_full_changeset \
        # kind="integration"
        # frob:tests src/frob/tickets/_land_git_ops.py::_true_merge_base kind="unit"
        # T-2550: `_worktree_full_changeset` binding above is exercised only
        # through the full `land()` pipeline here -- same COV006
        # kind="integration" trust-at-face-value convention as this file's
        # other land-pipeline findings.
        """T-0761 regression: the real T-0640 incident. `land()` was invoked
        with `--worktree` pointing at the SAME checkout/branch `root` had
        checked out -- no distinct feature branch was ever created. A NEW
        source file was added and committed directly on that shared branch
        (mirroring the incident's `src/frob/strata/_reliability.py`), then
        `land(repo, tid, repo)` ran.

        Before the T-0761 fix, this landed "successfully": the merge/squash
        steps against `worktree`'s own branch were git no-ops (a branch
        merged/squashed into itself), so the T-0463 completeness assertion's
        `expected` changeset came back EMPTY and passed vacuously -- only the
        version-bump/ledger-splice writes ended up in the final commit, and
        `new_feature.py` was silently dropped even though `frob ticket land`
        reported success. After the fix, `land` must refuse with
        `IncompleteLand` (a completeness error) rather than commit a
        changeset that drops the new file -- the ticket's acceptance
        criterion's second branch."""
        (repo / "src" / "new_feature.py").write_text("# brand new feature code\n")
        _commit_all(repo, "add new_feature.py directly on the shared branch")

        created = new_ticket(
            repo, _spec("Same-branch land", scope=("src/new_feature.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on the shared branch")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand

        # Refused, not silently landed: no "land T-XXXX" squash-apply commit
        # (the false-green signature -- version bump + ledger only) was ever
        # made, the squash-stage was unwound cleanly, and `new_feature.py`'s
        # content is exactly what was committed above -- nothing was dropped
        # by an incomplete commit.
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "land " not in log
        assert _status_ignoring_frob(repo) == ""
        assert (repo / "src" / "new_feature.py").read_text() == (
            "# brand new feature code\n"
        )


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
        assert _status_ignoring_frob(wt) == ""


class TestOutOfScopeConflictAutoResolved:
    """T-0479(b): a conflict in a file OUTSIDE the landing ticket's scope
    must auto-resolve to main's side instead of aborting the land."""

    def test_conflict_outside_scope_takes_mains_side_and_lands(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-oos", str(wt)], repo)

        # Worktree ticket is scoped ONLY to src/other.py; it never legitimately
        # touches feature.py.
        (wt / "src" / "other.py").write_text("worktree change\n")
        (wt / "src" / "feature.py").write_text("# worktree-side unrelated edit\n")
        created = new_ticket(
            wt, _spec("Out of scope conflict", scope=("src/other.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits other.py and (out of scope) feature.py")

        # Main independently changes the SAME line of feature.py.
        (repo / "src" / "feature.py").write_text("# main-side edit\n")
        _commit_all(repo, "main edits feature.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        # Main's side of the out-of-scope conflict won.
        assert (repo / "src" / "feature.py").read_text() == "# main-side edit\n"
        assert (repo / "src" / "other.py").read_text() == "worktree change\n"


# frob:ticket T-1434
# frob:ticket T-2550
class TestCoverageLockConflictMerges:
    """T-1434: `frob-coverage.lock.json` is a coverage-ratchet artifact,
    not an ordinary source file -- a genuine conflict on it (both the
    worktree and main independently stamped coverage since diverging)
    must never blindly discard one side's freshly measured data. Confirms
    the root cause (T-1270's "reverted to an older committed value"
    incident) and its fix: the out-of-scope conflict auto-resolver now
    keeps the elementwise MAX of both sides' `module_line` percentages
    instead of picking one side wholesale."""

    # frob:tests tests/test_ticket_land.py::TestCoverageLockConflictMerges.test_conflicting_lock_merges_to_the_higher_of_both_sides  # noqa: E501
    # frob:ticket T-2550
    def test_conflicting_lock_merges_to_the_higher_of_both_sides(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_merge_coverage_lock_conflict \
        # kind="integration"
        # T-2550: exercised only through the full `land(..., dry_run=False)`
        # pipeline several call-hops deep -- same COV006 kind="integration"
        # trust-at-face-value convention as this file's other land-pipeline
        # findings; see TestWipAddIgnoredPathFallback above for the fuller
        # precedent citation.
        wt = repo.parent / "wt-covlock"
        base_lock = {
            "source_sha": "base",
            "module_line": {"src/a.py": 50.0, "src/b.py": 50.0},
        }
        (repo / "frob-coverage.lock.json").write_text(
            json.dumps(base_lock, indent=2, sort_keys=True) + "\n"
        )
        _commit_all(repo, "seed base frob-coverage.lock.json")
        _run(["git", "worktree", "add", "-b", "feature-covlock", str(wt)], repo)

        # Worktree ticket is scoped ONLY to src/other.py -- it never
        # legitimately touches frob-coverage.lock.json, but a local
        # `--stamp-coverage` run (e.g. while investigating a fix) leaves
        # it dirty anyway, with a REAL, freshly measured, higher number
        # for src/a.py that main's own stamp does not have yet.
        (wt / "src" / "other.py").write_text("worktree change\n")
        wt_lock = {
            "source_sha": "worktree-fresh",
            "module_line": {"src/a.py": 95.0, "src/b.py": 50.0},
        }
        (wt / "frob-coverage.lock.json").write_text(
            json.dumps(wt_lock, indent=2, sort_keys=True) + "\n"
        )
        created = new_ticket(
            wt, _spec("Coverage lock conflict", scope=("src/other.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits other.py and stamps coverage locally")

        # Main independently stamps coverage too, with a higher number
        # for src/b.py the worktree's own stamp does not have.
        main_lock = {
            "source_sha": "main-fresh",
            "module_line": {"src/a.py": 50.0, "src/b.py": 90.0},
        }
        (repo / "frob-coverage.lock.json").write_text(
            json.dumps(main_lock, indent=2, sort_keys=True) + "\n"
        )
        _commit_all(repo, "main stamps coverage independently")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        merged = json.loads((repo / "frob-coverage.lock.json").read_text())
        # Neither side's freshly measured number was silently discarded --
        # the higher of the two survives for every module.
        assert merged["module_line"]["src/a.py"] == 95.0
        assert merged["module_line"]["src/b.py"] == 90.0
        assert (repo / "src" / "other.py").read_text() == "worktree change\n"


# frob:ticket T-0795
# frob:ticket T-2220
class TestLandRetryAfterFinalizeThenFail:
    """T-0795: three real lands this drive (T-0676, T-0774, T-0767) merged
    and finalized in the worktree (the ticket transitioned to `done` and
    that transition was committed there) but then failed at a LATER step
    -- the squash-apply onto `root` -- before the main commit landed.
    Retrying the identical `land()` call always errored `InvalidTransition`
    (`transition(..., DONE)` re-run against an already-`done` ticket), even
    though the land itself is perfectly resumable; each incident required a
    manual splice-apply onto main instead. This locks the fix: a retry
    recognizes the already-done ticket and resumes straight at
    squash-apply."""

    def test_retry_after_finalize_then_squash_failure_lands_the_diff(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_after_finalize_then_squash_failure_lands_the_diff  # noqa: E501
        # frob:tests src/frob/tickets/_land_finalize.py::_close_finalized_ticket \
        # kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-retry", str(wt)], repo)
        created = new_ticket(wt, _spec("Retry me", scope=("src/retried.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "retried.py").write_text("# retried feature\n")
        _commit_all(wt, "add retried.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # First attempt: `bump_version` fails (simulating whichever
        # post-finalize step actually failed in the real incidents --
        # squash conflict, REL001 bump, or the T-0463 completeness
        # assertion; all of them unwind `root` cleanly via `reset --hard`
        # the same way this callback's failure path does) AFTER the
        # worktree has already merged, finalized, and closed the ticket
        # (that whole sequence commits in the WORKTREE unconditionally
        # before `_land_squash_apply` -- see `_land_locked` -- so it
        # survives this failure).
        first = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Err(LandError.ReleaseBumpFailed),
        )
        assert first.is_err
        assert first.danger_err == LandError.ReleaseBumpFailed

        # root: untouched by the failed attempt (the bump failure unwound
        # the staged squash).
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _status_ignoring_frob(repo) == ""

        # worktree: the ticket really did reach `done` and that transition
        # really did commit -- this is the exact precondition that used to
        # make the retry below error `InvalidTransition`. The first attempt
        # already finalized `tid`'s draft id to a real sequential id (that
        # finalize-and-commit step runs BEFORE the bump that then failed),
        # so the retry -- exactly like a real coordinator's retry -- must
        # address the ticket by its now-finalized id.
        wt_tickets = load_all(wt).danger_ok
        final_id = next(i for i, t in wt_tickets.items() if t.state == TicketState.DONE)
        assert final_id != tid
        assert _status_ignoring_frob(wt) == ""

        # Retry, identical arguments (final id, same worktree) except a
        # bump_version that now succeeds -- must NOT error InvalidTransition
        # on the already-done ticket; must resume at squash-apply and
        # actually land.
        second = land(
            repo,
            final_id,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Ok(None),
        )
        assert second.is_ok, second.err
        assert second.danger_ok.final_id == final_id

        # The diff really landed onto main: the new file exists on root's
        # branch, in a real "land <id>" commit distinct from before_main_sha.
        assert (repo / "src" / "retried.py").read_text() == "# retried feature\n"
        after_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_main_sha != before_main_sha
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert f"land {final_id}" in log
        assert _status_ignoring_frob(repo) == ""

    # frob:ticket T-2220
    def test_retry_after_full_success_reports_absorption_not_commit_failed(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_after_full_success_reports_absorption_not_commit_failed  # noqa: E501
        """T-1001 (churn item 2): retrying a land whose FIRST attempt
        already fully succeeded (committed onto `root`, ticket `done` on
        both sides) stages nothing new -- the squash finds no file diff
        and the ledger splice of an already-matching block is a no-op.
        This must report a clean `absorbed by prior land` success
        (`ledger_spliced=False`, `commit_sha` naming the SAME commit the
        first land's own tip ended at, no new files), never `CommitFailed`
        from an empty `git commit`.

        T-2220: `first.danger_ok.commit_sha` names the squash-apply commit
        specifically (unchanged) -- but `root`'s actual tip after a REAL
        land is now one commit further, `_record_land_commit`'s own
        follow-up commit (structurally required: a commit cannot embed its
        own hash). The retry's absorption path reports root's CURRENT
        HEAD (unchanged existing behavior, `_report_stacked_sibling_
        absorption`), so the "same commit" this test's own docstring
        promises is root's tip as of right after the first land
        (`first_tip` below), not `first.danger_ok.commit_sha` itself."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-absorbed", str(wt)], repo)
        created = new_ticket(wt, _spec("Absorbed by its own prior land"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket absorbed by its own prior land")

        first = land(repo, tid, wt, dry_run=False)
        assert first.is_ok, first.err
        final_id = first.danger_ok.final_id
        first_sha = first.danger_ok.commit_sha
        assert first_sha is not None
        first_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        retry = land(repo, final_id, wt, dry_run=False)

        assert retry.is_ok, retry.err
        assert retry.danger_ok.ledger_spliced is False
        assert retry.danger_ok.commit_sha == first_tip
        assert retry.danger_ok.files_changed == ()
        # No new commit was made -- root's tip is unchanged by the retry.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == first_tip

    def test_retry_when_still_queued_re_runs_the_ordinary_transition(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_when_still_queued_re_runs_the_ordinary_transition  # noqa: E501
        # frob:tests src/frob/tickets/_land_finalize.py::_close_finalized_ticket \
        # kind="unit"
        """Sanity companion: the ordinary (non-retry) first-time land, where
        the ticket is NOT already done, still runs the real transition --
        the T-0795 fix only short-circuits when the ticket is ALREADY
        `done`, it does not skip closing altogether."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-firsttime", str(wt)], repo)
        created = new_ticket(wt, _spec("First time", scope=("src/firsttime.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "firsttime.py").write_text("# first time\n")
        _commit_all(wt, "add firsttime.py")

        assert load_all(wt).danger_ok[tid].state == TicketState.IN_PROGRESS

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.final_id != ""


# frob:ticket T-1701
# frob:ticket T-1721
class TestLandDroppedTicket:
    """T-1701: `frob ticket land` must be able to publish a DROPPED
    ticket's ledger entry to main -- before this fix, `_close_finalized_
    ticket` unconditionally forced a `dropped -> done` transition
    (illegal, `InvalidTransition`, every single retry) and `_validate_
    closeable` unconditionally required evidence + a Done report (neither
    applicable to a ticket dropped, not done), leaving no path through
    `land` for a legitimate DROPPED outcome -- forcing an agent to bypass
    worktree isolation and run `frob ticket drop` directly against the
    root checkout (the live incident: T-1538, then independently again
    T-1683 within the same hour)."""

    # frob:ticket T-1721
    def test_dropped_ticket_with_a_reason_lands_cleanly(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandDroppedTicket.test_dropped_ticket_with_a_reason_lands_cleanly  # noqa: E501
        # frob:tests src/frob/tickets/_land_merge.py::_validate_closeable kind="unit"
        # frob:tests src/frob/tickets/_land_finalize.py::_close_finalized_ticket \
        # kind="unit"
        from frob.tickets import drop_ticket

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-dropped", str(wt)], repo)
        created = new_ticket(wt, _spec("Already fixed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        dropped = drop_ticket(wt, tid, "premise already resolved by an earlier ticket")
        assert dropped.is_ok, dropped.err
        _commit_all(wt, "drop the ticket")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        on_main = load_all(repo).danger_ok[result.danger_ok.final_id]
        assert on_main.state == TicketState.DROPPED
        assert "premise already resolved" in on_main.body

    def test_dropped_ticket_with_no_reason_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandDroppedTicket.test_dropped_ticket_with_no_reason_refuses  # noqa: E501
        # frob:tests src/frob/tickets/_land_merge.py::_validate_closeable kind="unit"
        """A `state: dropped` ticket whose body carries no `## Drop
        reason` section at all (only reachable by hand-editing the ledger
        -- `frob ticket drop` itself always refuses an empty reason at
        write time, `DropReasonMissing`) must still refuse to land: a
        drop with no recorded reason is indistinguishable from a silent
        discard, the exact hazard `_validate_closeable`'s DROPPED branch
        exists to keep unreachable end to end, not just at the CLI
        surface."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-dropped-blank", str(wt)], repo)
        created = new_ticket(wt, _spec("No reason recorded"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        assert transition(wt, tid, TicketState.DROPPED).is_ok
        _commit_all(wt, "drop with no recorded reason (hand-transitioned)")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable


# frob:ticket T-1818
# frob:ticket T-1736
# frob:ticket T-2550
class TestLandFailedTicket:
    """T-1818: `frob ticket land` must be able to publish a QUEUED ticket's
    `frob ticket fail` record to main -- before this fix, a ticket `fail`
    correctly returned to QUEUED had no path through `land` at all: the
    DONE preconditions below (evidence + Done report) never apply to a
    failed attempt, so the ONE artifact a dead end produces (the failure
    log) was stranded on the worktree branch, invisible to every later
    agent (the incident this ticket was filed from: T-1478)."""

    # frob:ticket T-1736
    # frob:ticket T-2550
    def test_failed_ticket_with_a_failure_log_lands_cleanly(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandFailedTicket.test_failed_ticket_with_a_failure_log_lands_cleanly  # noqa: E501
        # frob:tests src/frob/tickets/_land_merge.py::_validate_closeable kind="unit"
        # frob:tests src/frob/tickets/_land_merge.py::_has_failure_log \
        # kind="integration"
        # frob:tests src/frob/tickets/_land_finalize.py::_close_finalized_ticket \
        # kind="unit"
        # T-2550: `_has_failure_log` binding above is exercised only through
        # the full `land()` pipeline here -- same COV006 kind="integration"
        # trust-at-face-value convention as this file's other land-pipeline
        # findings.
        from frob.tickets import FailureEntry, record_failure

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-failed", str(wt)], repo)
        created = new_ticket(wt, _spec("Undoable as scoped"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        recorded = record_failure(
            wt,
            tid,
            FailureEntry(
                date=date.today(),
                attempt=1,
                summary="needs a new grammar production not in scope",
            ),
        )
        assert recorded.is_ok, recorded.err
        assert transition(wt, tid, TicketState.QUEUED).is_ok
        _commit_all(wt, "fail-log the ticket")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        on_main = load_all(repo).danger_ok[result.danger_ok.final_id]
        assert on_main.state == TicketState.QUEUED
        assert "needs a new grammar production" in on_main.body

    # frob:ticket T-1736
    def test_queued_ticket_with_no_failure_log_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandFailedTicket.test_queued_ticket_with_no_failure_log_still_refuses  # noqa: E501
        # frob:tests src/frob/tickets/_land_merge.py::_validate_closeable kind="unit"
        """A ticket that is merely QUEUED (never started, or requeued with
        no fail-log recorded) must NOT skip the DONE preconditions -- only
        a genuine `frob ticket fail` record (a `## Failure log` entry)
        earns the pass-through this ticket adds."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-queued-blank", str(wt)], repo)
        created = new_ticket(wt, _spec("Never started"))
        assert created.is_ok
        tid = created.danger_ok.id

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable



# frob:ticket T-0795
class TestLandRefusesWhenRootIsWorktree:
    """T-0795: `land()` invoked with `--worktree` resolving to the SAME
    path as `root` used to fall through to `_worktree_full_changeset`'s
    much later T-0640/T-0761 diagnosis ("`--worktree` almost certainly
    points at the same checkout/branch root has checked out ... create a
    real feature branch") -- a correct remedy for a worktree genuinely
    pointed at the wrong branch, but a misleading one for the far more
    common real cause: `root` defaults to the invoker's cwd, so running
    `frob ticket land` from a shell sitting INSIDE the worktree makes
    `root` resolve to `worktree` for free. This locks the new EARLY
    refusal (before any git mutation) that names the real mistake."""

    def test_refused_before_any_git_mutation_names_the_real_mistake(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree.test_refused_before_any_git_mutation_names_the_real_mistake  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        created = new_ticket(
            repo, _spec("Same path as root", scope=("src/samepath.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on root")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        assert "cwd" in caplog.text
        assert "ROOT checkout" in caplog.text

        # Refused before any git mutation at all: no merge/finalize/squash
        # commit, HEAD unmoved, tree exactly as found.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _status_ignoring_frob(repo) == ""
        still = load_all(repo).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS

    def test_still_refuses_when_worktree_has_diverged_commits(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree.test_still_refuses_when_worktree_has_diverged_commits  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        """T-0761 regression preserved under a different name: the exact
        prior scenario (a new file committed directly on the branch `root`
        has checked out, then `land(repo, tid, repo)`) still refuses with
        `IncompleteLand` -- just via the new, earlier, more specific check
        rather than falling through to `_worktree_full_changeset`."""
        (repo / "src" / "new_feature2.py").write_text("# brand new feature code\n")
        _commit_all(repo, "add new_feature2.py directly on the shared branch")

        created = new_ticket(
            repo, _spec("Same-branch land 2", scope=("src/new_feature2.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on the shared branch")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "land " not in log
        assert _status_ignoring_frob(repo) == ""



# frob:ticket T-1003
class TestLandChainedCdRootResolution:
    """T-1003 (churn item 4): `root` defaulting to the invoker's cwd makes
    it resolve to the IDENTICAL path as a REAL `--worktree` whenever the
    shell never `cd`ed out of the worktree first -- the "chained cd"
    ritual every land used to require. Unlike `TestLandRefusesWhenRootIs
    Worktree` (where `worktree` genuinely IS the primary checkout, no
    linked worktree exists at all, and refusing is correct), a REAL
    linked worktree's `git rev-parse --git-common-dir` resolves to a
    DIFFERENT primary checkout than `worktree` itself -- `land()` uses
    that to recover the true `root` and land onto it, transparently, with
    no manual `cd` required."""

    def test_root_equal_to_a_real_linked_worktree_resolves_and_lands(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_a_real_linked_worktree_resolves_and_lands  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_resolve_primary_checkout kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-chained-cd", str(wt)], repo)

        created = new_ticket(wt, _spec("Chained-cd ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance chained-cd ticket")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # Simulate a shell whose cwd never left the worktree: `root` here
        # is `wt`, identical to `--worktree wt`, exactly what `(cfg.
        # ticket_path or Path(".")).resolve()` produces from inside `wt`.
        with caplog.at_level("INFO", logger="frob.tickets._land"):
            result = land(wt, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert "resolved the primary checkout" in caplog.text

        # It actually landed onto the TRUE primary checkout (`repo`), not
        # `wt` -- the ticket is done there, and `repo`'s HEAD moved.
        final_id = result.danger_ok.final_id
        landed = load_all(repo).danger_ok[final_id]
        assert landed.state == TicketState.DONE
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() != before_main_sha
        )

    def test_root_equal_to_the_primary_checkout_itself_still_refuses(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_the_primary_checkout_itself_still_refuses  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_resolve_primary_checkout kind="unit"
        """Sanity companion: when `--worktree` genuinely IS the primary
        checkout (no linked worktree at all, `TestLandRefusesWhenRootIs
        Worktree`'s scenario), `_resolve_primary_checkout` resolves back
        to the SAME path, so `root` is left unchanged and the original
        `_refuse_if_root_is_worktree` refusal still fires -- T-1003 never
        weakens that guard."""
        created = new_ticket(
            repo, _spec("Genuinely no worktree", scope=("src/noworktree.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on root")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand


# frob:ticket T-0682
class TestMergeMainIntoWorktreeRicherState:
    """T-0682 integration lock: `_merge_main_into_worktree` (the "merge main
    into the worktree" stage every `frob ticket land` call runs, and the
    exact site where the registered `tickets.md` git merge driver
    auto-fires on `git merge --no-commit --no-ff`) must not let main's
    bare, reportless copy of the LANDING ticket's own block win over the
    worktree's Done-reported copy WHEN the worktree's copy also outranks
    it -- the original T-0682 field incident."""

    def test_landing_tickets_in_progress_report_survives_the_merge_stage(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestMergeMainIntoWorktreeRicherState.test_landing_tickets_in_progress_report_survives_the_merge_stage  # noqa: E501
        # Ticket is created ON main (a real id, not a draft) so it exists
        # in BOTH the worktree's and main's ledgers before either side
        # diverges it -- the scenario under test is a genuine same-id
        # divergence, not draft finalization (covered elsewhere).
        created = new_ticket(
            repo, _spec("Landing ticket", scope=("src/widget.py",)), no_commit=True
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "file landing ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-richer", str(wt)], repo)

        # Worktree: driven to `in-progress` with a substantive Done report
        # already attached -- a HIGHER state-rank than main's bare queued
        # AND a Done report, matching the real field incident (T-0633/
        # T-0637's landing tickets were in-progress+reported when the
        # merge stage regressed them).
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt).danger_ok[tid]
        with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(wt, with_report).is_ok
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "advance ticket to in-progress+report")
        ticket_before_merge = load_all(wt).danger_ok[tid]

        # Main's OWN copy of the SAME ticket never advanced past its bare
        # `queued` state -- unrelated main-side history, no divergence in
        # rank OR report to work in the worktree's favor by accident.
        (repo / "src" / "unrelated.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        result = _land_mod._merge_main_into_worktree(
            repo, wt, ticket_before_merge, "main"
        )
        assert result.is_ok, result.err

        merged_text = ledger_path(wt).read_text()
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(merged_text).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid].body


# frob:ticket T-1331
class TestFrobDirNeverLeaksIntoGitAdd:
    """T-1331: `.frob/` scratch state (per-ticket locks, the T-1257 v2
    index/archive cache files) must never become a TRACKED file via any
    fixture's blanket `git add -A` (`_commit_all`) -- an un-gitignored
    fixture repo previously let two branches each commit a DIFFERENT
    `.frob/tickets-index.json` as a real tracked file, colliding as a raw
    git add/add conflict at merge (`TestArchiveV2::
    test_archive_v2_regression_two_sided_divergence_no_clobber`) or
    tripping land's T-0463 completeness assertion (`LandError.
    IncompleteLand`) once the squash-apply's target checkout came up
    missing files the source checkout had committed. `_git_init` (T-1258)
    fixed this by writing a `.gitignore` with `.frob/` into every fixture
    repo from its very first commit; this locks that in as a regression
    test tied to T-1331 specifically, independent of `_git_init`'s own
    docstring."""

    # frob:ticket T-1331
    # frob:tests tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd.test_frob_scratch_files_are_gitignored_not_tracked kind="unit"  # noqa: E501
    def test_frob_scratch_files_are_gitignored_not_tracked(
        self, tmp_path: Path
    ) -> None:
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")

        # Simulate real frob scratch state a ticket operation would leave
        # behind before any commit happens (T-1257's v2 index/archive
        # cache files, a per-ticket lock file).
        frob_dir = main_repo / ".frob"
        frob_dir.mkdir()
        (frob_dir / "tickets-index.json").write_text("{}")
        (frob_dir / "tickets-archive-cache.json").write_text("{}")
        (frob_dir / "some.lock").write_text("")

        _commit_all(main_repo, "init")

        tracked = _run(["git", "ls-files"], main_repo).stdout.splitlines()
        assert not any(path.startswith(".frob/") for path in tracked), tracked

        status = _run(["git", "status", "--porcelain"], main_repo).stdout
        assert ".frob/" not in status

    # frob:ticket T-1331
    # frob:tests tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd.test_two_branches_with_divergent_frob_scratch_never_add_add_conflict  # noqa: E501
    def test_two_branches_with_divergent_frob_scratch_never_add_add_conflict(
        self, tmp_path: Path
    ) -> None:
        """The exact T-1331 incident shape: two independent checkouts each
        write a DIFFERENT `.frob/tickets-index.json` before committing --
        gitignoring `.frob/` means neither ever tracks the file, so
        merging one into the other can never hit a real git add/add
        conflict over it."""
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        _commit_all(main_repo, "init")

        clone = tmp_path / "clone"
        _run(["git", "clone", "-q", str(main_repo), str(clone)], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], clone)
        _run(["git", "config", "user.name", "Test"], clone)

        (main_repo / ".frob").mkdir()
        (main_repo / ".frob" / "tickets-index.json").write_text('{"side": "main"}')
        (main_repo / "src_a.py").write_text("# a\n")
        _commit_all(main_repo, "main side")

        (clone / ".frob").mkdir()
        (clone / ".frob" / "tickets-index.json").write_text('{"side": "clone"}')
        (clone / "src_b.py").write_text("# b\n")
        _commit_all(clone, "clone side")

        _run(["git", "fetch", "-q", str(main_repo), "main"], clone)
        merge = subprocess.run(
            ["git", "merge", "-q", "FETCH_HEAD", "-m", "merge"],
            cwd=str(clone),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, merge.stdout + merge.stderr
        assert "add/add" not in (merge.stdout + merge.stderr)


# frob:ticket T-1799
class TestCommitsTouchingPath:
    """T-1799: an `OutOfScopeWaiveDeletion` refusal used to say only
    "revert the offending commit" with no commit actually named --
    `_commits_touching_path` reads the REAL commit(s) off `git log`
    instead of leaving an agent to reconstruct which one by hand."""

    def test_names_the_real_commit_that_touched_the_file(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestCommitsTouchingPath.test_names_the_real_commit\
        # _that_touched_the_file
        # frob:ticket T-1799
        from frob.tickets._land_git_ops import _commits_touching_path

        base = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(repo, "a very specific commit subject for T-1799")

        found = _commits_touching_path(repo, base, "src/other.py")

        assert len(found) == 1
        assert "a very specific commit subject for T-1799" in found[0]

    def test_empty_when_the_path_was_never_touched(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestCommitsTouchingPath.test_empty_when_the_path_w\
        # as_never_touched
        # frob:ticket T-1799
        from frob.tickets._land_git_ops import _commits_touching_path

        base = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "src" / "unrelated.py").write_text("def h():\n    pass\n")
        _commit_all(repo, "touches a different file entirely")

        assert _commits_touching_path(repo, base, "src/other.py") == ()
