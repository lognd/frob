from pathlib import Path

import pytest

import frob.tickets._land_git_ops as _land_git_ops_mod
from frob.tickets import (
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import (
    AcceptanceCriterion,
    LandError,
)
from frob.tickets._store import (
    load_all,
    write_ticket,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _make_closeable,
    _run,
    _spec,
    _status_ignoring_frob,
)

pytestmark = pytest.mark.heavy_subprocess


# frob:ticket T-1699
class TestDirtOwnedByNoOpenTicket:
    """T-1699: `_dirt_owned_by_no_open_ticket` -- tells root dirt that
    matches SOME open ticket's declared scope (plausibly a crashed
    land's own leftover) apart from dirt no open ticket's scope covers
    at all (most often a coordinator working directly on the shared root
    outside the ticket workflow -- the shape three agents in one session
    each independently misdiagnosed as "a crashed land")."""

    def test_path_inside_an_open_tickets_scope_is_not_orphaned(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnedByNoOpenTicket.t\
        # est_path_inside_an_open_tickets_scope_is_not_orphaned
        from frob.tickets._land import _dirt_owned_by_no_open_ticket

        created = new_ticket(repo, _spec("Open work", scope=("src/owned.py",)))
        assert created.is_ok
        assert transition(repo, created.danger_ok.id, TicketState.PLANNED).is_ok

        assert _dirt_owned_by_no_open_ticket(repo, ("src/owned.py",)) is False

    def test_path_outside_every_open_tickets_scope_is_orphaned(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnedByNoOpenTicket.t\
        # est_path_outside_every_open_tickets_scope_is_orphaned
        from frob.tickets._land import _dirt_owned_by_no_open_ticket

        created = new_ticket(repo, _spec("Open work", scope=("src/owned.py",)))
        assert created.is_ok
        assert transition(repo, created.danger_ok.id, TicketState.PLANNED).is_ok

        assert _dirt_owned_by_no_open_ticket(repo, ("src/coordinator_edit.py",)) is True

    def test_a_done_tickets_scope_does_not_count(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnedByNoOpenTicket.t\
        # est_a_done_tickets_scope_does_not_count
        """A DONE ticket's scope must not exempt its old files forever --
        only currently OPEN (non-terminal) tickets count."""
        from frob.tickets._land import _dirt_owned_by_no_open_ticket

        created = new_ticket(repo, _spec("Finished work", scope=("src/finished.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        assert transition(repo, tid, TicketState.DONE).is_ok

        assert _dirt_owned_by_no_open_ticket(repo, ("src/finished.py",)) is True


# frob:ticket T-2118
class TestDirtOwnerTickets:
    """T-2118: `_dirt_owner_tickets` -- names WHICH other open ticket(s)
    own dirt that does not belong to the landing ticket's own scope, the
    refinement `_dirt_owned_by_no_open_ticket`'s binary signal cannot
    provide (T-2071's measured incident shape: dirt belongs to some
    OTHER open ticket, just not the landing one)."""

    # frob:ticket T-2118
    def test_path_owned_by_another_open_ticket_names_it(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnerTickets.test_pat\
        # h_owned_by_another_open_ticket_names_it
        from frob.tickets._land import _dirt_owner_tickets

        created = new_ticket(repo, _spec("Other work", scope=("src/other.py",)))
        assert created.is_ok
        other_id = created.danger_ok.id
        assert transition(repo, other_id, TicketState.PLANNED).is_ok

        landing = new_ticket(repo, _spec("Landing work", scope=("src/mine.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        assert transition(repo, landing_id, TicketState.PLANNED).is_ok

        owners = _dirt_owner_tickets(repo, ("src/other.py",), landing_id)
        assert owners == {"src/other.py": [other_id]}

    # frob:ticket T-2118
    def test_path_owned_by_landing_ticket_itself_is_excluded(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnerTickets.test_pat\
        # h_owned_by_landing_ticket_itself_is_excluded
        from frob.tickets._land import _dirt_owner_tickets

        landing = new_ticket(repo, _spec("Landing work", scope=("src/mine.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        assert transition(repo, landing_id, TicketState.PLANNED).is_ok

        owners = _dirt_owner_tickets(repo, ("src/mine.py",), landing_id)
        assert owners == {}

    # frob:ticket T-2118
    def test_path_owned_by_no_open_ticket_is_excluded(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnerTickets.test_pat\
        # h_owned_by_no_open_ticket_is_excluded
        from frob.tickets._land import _dirt_owner_tickets

        landing = new_ticket(repo, _spec("Landing work", scope=("src/mine.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        assert transition(repo, landing_id, TicketState.PLANNED).is_ok

        owners = _dirt_owner_tickets(repo, ("src/coordinator_edit.py",), landing_id)
        assert owners == {}

    # frob:ticket T-2118
    def test_dirty_main_refusal_names_the_owning_ticket(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnerTickets.test_dir\
        # ty_main_refusal_names_the_owning_ticket
        """T-2071's own measured incident shape: dirt in root belongs to
        SOME other open ticket's declared scope, not the landing ticket's.
        The refusal log line must name that other ticket explicitly rather
        than falling through to the generic 'has uncommitted changes in:'
        message with no hint who to ask."""
        from frob.tickets._land import _log_dirty_main_refusal

        created = new_ticket(repo, _spec("Other work", scope=("src/other_owned.py",)))
        assert created.is_ok
        other_id = created.danger_ok.id
        assert transition(repo, other_id, TicketState.PLANNED).is_ok

        landing = new_ticket(repo, _spec("Landing work", scope=("src/mine.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        assert transition(repo, landing_id, TicketState.PLANNED).is_ok

        (repo / "src").mkdir(exist_ok=True)
        (repo / "src" / "other_owned.py").write_text("dirty\n")
        _run(["git", "add", "src/other_owned.py"], repo)

        # T-2118: clear the setup-phase log records (ticket creation itself
        # logs INFO lines naming both ticket ids) so the assertion below can
        # only be satisfied by the REFUSAL message itself naming the owner,
        # not by an unrelated earlier log line that happens to mention the
        # same id.
        caplog.clear()
        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            _log_dirty_main_refusal(repo, repo / "worktree", landing_id)

        assert other_id in caplog.text
        assert "src/other_owned.py" in caplog.text

    # frob:ticket T-3216
    def test_status_unreadable_refusal_never_claims_uncommitted_work(
        self,
        repo: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnerTickets.test_sta\
        # tus_unreadable_refusal_never_claims_uncommitted_work
        """T-3216's exact incident: `_porcelain_dirty_paths`'s own `git
        status` call fails (index.lock contention), landing on the
        `_dirt_owned_by_no_open_ticket` branch with an empty path set --
        this must be short-circuited to a STATUS-UNREADABLE refusal
        BEFORE that branch, never a message claiming uncommitted work
        exists nor telling the reader retrying cannot help."""
        import frob.tickets._land_git_ops as land_git_ops_mod
        from frob.tickets._land import _log_dirty_main_refusal

        landing = new_ticket(repo, _spec("Landing work", scope=("src/mine.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        assert transition(repo, landing_id, TicketState.PLANNED).is_ok

        def _fail(*a: object, **k: object):
            from typani import Ok

            class _Proc:
                returncode = 128
                stdout = ""
                stderr = "fatal: Unable to create '.git/index.lock': File exists."

            return Ok(_Proc())

        monkeypatch.setattr(land_git_ops_mod, "run_argv", _fail)
        caplog.clear()
        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            _log_dirty_main_refusal(repo, repo / "worktree", landing_id)

        assert "STATUS-UNREADABLE" in caplog.text
        assert "index.lock" in caplog.text
        assert "cannot fix this by retrying" not in caplog.text
        assert "belonging to NO open ticket" not in caplog.text


# frob:ticket T-1740
class TestDescribeRootDirtNamesStagedState:
    """T-1740: `DirtyMain`'s message used to say only "uncommitted
    changes," which reads as working-tree edits and sent an agent
    looking for the wrong thing when the real cause was a PRIOR land's
    leftover STAGED index. `describe_root_dirt` now calls staged state
    out explicitly and first."""

    def test_working_tree_only_dirt_is_unchanged(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_dirt_ownership.py::TestDescribeRootDirtNamesStagedState.test_working_tree_only_dirt_is_unchanged  # noqa: E501
        (repo / "modified.txt").write_text("unstaged edit\n")
        described = _land_git_ops_mod.describe_root_dirt(repo)
        assert "modified.txt" in described
        assert "STAGED" not in described

    def test_staged_dirt_is_called_out_explicitly(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_dirt_ownership.py::TestDescribeRootDirtNamesStagedState.test_staged_dirt_is_called_out_explicitly  # noqa: E501
        (repo / "staged.txt").write_text("staged leftover\n")
        _run(["git", "add", "staged.txt"], repo)
        described = _land_git_ops_mod.describe_root_dirt(repo)
        assert "STAGED" in described
        assert "staged.txt" in described

    def test_porcelain_dirty_paths_staged_only_reports_index_status(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_dirt_ownership.py::TestDescribeRootDirtNamesStagedState.test_porcelain_dirty_paths_staged_only_reports_index_status  # noqa: E501
        (repo / "staged.txt").write_text("staged\n")
        _run(["git", "add", "staged.txt"], repo)
        (repo / "unstaged.txt").write_text("unstaged\n")

        staged_only = _land_git_ops_mod._porcelain_dirty_paths_staged(repo)
        assert staged_only == ("staged.txt",)


# frob:ticket T-1514
class TestPreCommitUnscopedSweep:
    """T-1514: `land`'s optional `pre_commit_sweep` callback, invoked at
    the last checkpoint before the final squash-apply commit -- `root`'s
    working tree holds only the staged, uncommitted merge-preview
    changeset at that point, so a `False` verdict unwinds via the same
    `_verified_reset_root` path every other pre-commit failure already
    uses and never touches a real commit."""

    # frob:ticket T-1514
    def _land_one(self, repo: Path, branch: str, filename: str) -> tuple[str, Path]:
        wt = repo.parent / branch
        _run(["git", "worktree", "add", "-b", branch, str(wt)], repo)
        created = new_ticket(wt, _spec(f"{branch} ticket", scope=(f"src/{filename}",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / filename).write_text(f"# {filename}\n")
        _commit_all(wt, f"add {filename}")
        return tid, wt

    # frob:ticket T-1514
    def test_true_verdict_lands_normally(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestPreCommitUnscopedSweep.te\
        # st_true_verdict_lands_normally
        # frob:ticket T-3442
        # T-3135 flipped `pre_commit_sweep`'s handed tree from `root` to
        # the persistent warm-sweep-stage worktree
        # (`root/.frob/warm-sweep-stage`) so the sweep measures a tree
        # that actually holds the staged changeset -- see
        # tests/unit/test_land_stage_flip.py::TestDisposableStageFlip.
        # test_pre_commit_sweep_engages_the_warm_stage_not_root, the
        # dedicated coverage for this exact contract. This assertion is
        # updated to match; it is not re-testing the flip itself.
        tid, wt = self._land_one(repo, "feature-sweep-ok", "sweepok.py")
        calls: list[tuple[Path, str]] = []

        def sweep(root: Path, final_id: str) -> bool:
            calls.append((root, final_id))
            return True

        result = land(repo, tid, wt, dry_run=False, pre_commit_sweep=sweep)
        assert result.is_ok, result.err
        assert len(calls) == 1
        assert calls[0][0] == repo / ".frob" / "warm-sweep-stage"

    # frob:ticket T-1514
    def test_none_verdict_is_a_skip_lands_normally(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestPreCommitUnscopedSweep.te\
        # st_none_verdict_is_a_skip_lands_normally
        tid, wt = self._land_one(repo, "feature-sweep-skip", "sweepskip.py")

        result = land(
            repo, tid, wt, dry_run=False, pre_commit_sweep=lambda root, fid: None
        )
        assert result.is_ok, result.err

    # frob:ticket T-1514
    def test_false_verdict_unwinds_and_commits_nothing(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestPreCommitUnscopedSweep.te\
        # st_false_verdict_unwinds_and_commits_nothing
        tid, wt = self._land_one(repo, "feature-sweep-refuse", "sweeprefuse.py")
        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(
            repo, tid, wt, dry_run=False, pre_commit_sweep=lambda root, fid: False
        )
        assert result.is_err
        assert result.danger_err == LandError.PreLandUnscopedSweepFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    # frob:ticket T-1514
    def test_no_callback_is_noop(self, repo: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_dirt_ownership.py::TestPreCommitUnscopedSweep.te\
        # st_no_callback_is_noop
        tid, wt = self._land_one(repo, "feature-sweep-none", "sweepnone.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err


class TestUnboundAcceptancePreflightBeforeMerge:
    """T-0763: an unbound acceptance criterion must be caught by land's
    PRE-merge closeability preflight (`_validate_closeable` ->
    `_validate_acceptance_bound`), not discovered only after the merge/
    finalize commits are already made. Before this fix, `_validate_closeable`
    checked only evidence-present/Done-report/cmd-evidence-kind, so an
    unbound acceptance criterion sailed through the precheck, `land` merged
    main into the worktree AND committed a finalize commit, and only then
    failed at `_close_finalized_ticket`'s `transition(..., DONE)` call with
    `LandError.CloseFailed` -- leaving a merge/finalize commit the caller
    had to `git reset --hard HEAD~1` before retrying. This test asserts the
    ENTIRE git log (both `repo`/main and `wt`/worktree) is byte-identical
    before and after the refused land -- not just that `land` returns an
    error -- since a fail-AFTER-merge regression would still return
    `Err(...)` while leaving exactly the commit(s) this asserts are absent.
    """

    def test_unbound_acceptance_refused_pre_merge_no_commits_created(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_dirt_ownership.py::TestUnboundAcceptancePreflightBeforeMerge.test_unbound_acceptance_refused_pre_merge_no_commits_created  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-unbound-acceptance", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with unbound acceptance", scope=("src/other3.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id

        # Attach an acceptance criterion whose own `evidence` tuple is
        # empty -- unbound by construction (T-0572) -- while the ticket
        # otherwise satisfies every OTHER closeability precondition
        # (evidence present, Done report present, evidence-kind
        # consistent), isolating this test to the acceptance-binding gate
        # alone.
        _make_closeable(wt, tid)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "acceptance": (
                    AcceptanceCriterion(text="GIVEN x WHEN y THEN z", evidence=()),
                )
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "advance ticket with unbound acceptance criterion")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout
        wt_status_before = _status_ignoring_frob(wt)

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Git log is UNCHANGED on both sides -- no merge commit, no
        # finalize commit, no squash-apply commit -- not merely "the same
        # HEAD sha", but the exact same full set of commits (a fail-after-
        # merge regression would add commits reachable only via a branch
        # ref, which `--all` catches even if `HEAD` itself were untouched).
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before
        # Working tree is clean -- no merge left half-applied/uncommitted.
        assert _status_ignoring_frob(wt) == wt_status_before
        assert _status_ignoring_frob(repo) == ""

        # The ticket itself is untouched: still in-progress, not closed.
        still = load_all(wt).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS


class TestScopeUnboundPreflightBeforeMerge:
    """T-0774: `EvidenceScopeUnbound` (D-05's injected `covers_scope`
    callable) must ALSO be caught by land's PRE-merge closeability
    preflight (`_land_precheck` -> `_validate_scope_covered_preflight`),
    not discovered only after the merge/finalize commits already exist.
    Before this fix, `_land_precheck` never consulted `covers_scope` at
    all -- it was invoked for the first time inside `_land_finalize_and_close`,
    AFTER the merge commit was already made, so a ticket whose evidence does
    not cover its scope still merged+committed before `land` refused
    (`LandError.CloseFailed`, not `NotCloseable`). This test asserts the
    ENTIRE git log (both `repo`/main and `wt`/worktree) is byte-identical
    before and after the refused land -- not just that `land` returns an
    error -- mirroring `TestUnboundAcceptancePreflightBeforeMerge`'s own
    assertion shape for the sibling D-05 check this ticket closes."""

    def test_scope_unbound_refused_pre_merge_no_commits_created(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_dirt_ownership.py::TestScopeUnboundPreflightBeforeMerge.test_scope_unbound_refused_pre_merge_no_commits_created  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-scope-unbound", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with scope-unbound evidence", scope=("src/other4.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id

        # Otherwise fully closeable (evidence present, Done report present,
        # no unbound acceptance criteria) -- isolating this test to the
        # covers_scope preflight alone.
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with scope-unbound evidence")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout
        wt_status_before = _status_ignoring_frob(wt)

        # A `covers_scope` callable that always answers False, exactly the
        # shape `frob.app.ticket_runner`'s `_land_covers_scope_fn` supplies
        # via `frob.gates.evidence_covers_scope` when no evidence id binds
        # to a touched/scope symbol.
        result = land(repo, tid, wt, dry_run=False, covers_scope=lambda _t: False)

        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Git log is UNCHANGED on both sides -- no merge commit, no
        # finalize commit, no squash-apply commit.
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before
        # Working tree is clean -- no merge left half-applied/uncommitted.
        assert _status_ignoring_frob(wt) == wt_status_before
        assert _status_ignoring_frob(repo) == ""

        # The ticket itself is untouched: still in-progress, not closed.
        still = load_all(wt).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS

    def test_covers_scope_true_still_lands_normally(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_dirt_ownership.py::TestScopeUnboundPreflightBeforeMerge.test_covers_scope_true_still_lands_normally  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-scope-bound", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with scope-bound evidence", scope=("src/other5.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with scope-bound evidence")

        result = land(repo, tid, wt, dry_run=False, covers_scope=lambda _t: True)

        assert result.is_ok, result.err
