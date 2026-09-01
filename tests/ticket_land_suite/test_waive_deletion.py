from pathlib import Path

import pytest

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
    load_all,
    write_ticket,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _make_closeable,
    _run,
    _spec,
)

pytestmark = pytest.mark.heavy_subprocess



# frob:ticket T-1323
class TestUncommittedWaiveDeletionRefusal:
    """T-1323 incident guard: the 2026-07-29 land that wip-snapshotted an
    uncommitted, out-of-scope `frob:waive` DELETION and squash-applied it
    onto main. `land` must refuse BEFORE any git mutation (no wip-commit,
    no merge) when the worktree's dirty state removes a `frob:waive`
    directive whose file is neither in the landing ticket's scope nor
    named in its Done report."""

    def test_out_of_scope_undeclared_waive_deletion_refuses_before_merge(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-1", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Uncommitted deletion of the waiver comment -- out of ticket
        # scope, never mentioned in its Done report. Deliberately left
        # UNCOMMITTED: this is the exact laundering shape (dirty worktree
        # state that a wip-commit would otherwise fold into the merge
        # unattributed).
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion
        # Refused before any mutation: no wip-commit, no merge attempt --
        # the worktree's dirty state is untouched.
        status = _run(["git", "status", "--porcelain"], wt).stdout
        assert "src/other.py" in status
        assert (repo / "src" / "other.py").read_text().count("frob:waive") == 1

    def test_in_scope_waive_deletion_is_allowed(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-2", str(wt)], repo)

        created = new_ticket(wt, _spec("Retire stale waiver", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_declared_in_done_report_waive_deletion_is_allowed(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-3", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nAlso removed the stale "
                    + "frob:waive PERF001 in src/other.py (found while "
                    + "working this ticket).\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_prose_mention_outside_done_report_is_not_a_declaration(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-1323 review fix: a rule id appearing in ordinary body prose
        # (not the Done report section) must NOT satisfy the declaration
        # escape hatch -- the append-only ledger accumulates incidental
        # mentions, and substring-anywhere matching laundered exactly the
        # incident this guard exists to refuse.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="load-bearing, must not vanish"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-4", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\nEarlier discussion mentioned PERF001 and "
                    + "src/other.py in passing, long before any work "
                    + "happened.\n"
                    + "\n## Done report\n\nImplemented the feature in "
                    + "src/feature.py; no waivers were touched.\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion


# frob:ticket T-1468
# frob:ticket T-1332
# frob:ticket T-1636
class TestWaiveRewrapNotDeletion:
    """T-1468: a `frob fmt` re-wrap of a multi-line `frob:waive` comment's
    `reason="..."` continuation (changing how many physical lines it spans
    without changing its actual content) must NOT trip the T-1323/T-1326
    out-of-scope waive-deletion refusal -- only a genuine content removal
    should."""

    # frob:ticket T-1468
    # frob:ticket T-1636
    def test_rewrap_only_diff_is_not_flagged_as_a_deletion(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_uncommitted_waive_deletions \
        # kind="integration"
        # T-1636: exercised only through the full `land(..., dry_run=True)`
        # pipeline several call-hops deep, not a direct call a static call-graph can
        # see -- COV006's own kind="integration" trust-at-face-value convention.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used to fit on \\\n'
            '# two lines like this"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a wrapped PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rewrap", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Re-wrap the SAME reason text across three physical lines instead
        # of two -- a `frob fmt` line-length absorption, not a content
        # change. Out of this ticket's scope, uncommitted (the exact T-1323
        # laundering shape), but it must not refuse: the normalized content
        # is byte-identical to what it replaces.
        (wt / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used \\\n'
            "# to fit \\\n"
            '# on two lines like this"\n'
            "def g():\n    pass\n"
        )

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1468
    # frob:ticket T-1636
    def test_rewrap_that_also_changes_content_still_refuses(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_uncommitted_waive_deletions \
        # kind="integration"
        # T-1636: exercised only through the full `land(..., dry_run=True)`
        # pipeline several call-hops deep, not a direct call a static call-graph can
        # see -- COV006's own kind="integration" trust-at-face-value convention.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used to fit on \\\n'
            '# two lines like this"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a wrapped PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-rewrap-changed", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Re-wrapped AND the reason text itself genuinely changed -- this
        # must still refuse, since the normalized content differs.
        (wt / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="a completely different reason \\\n'
            '# spanning two lines now"\n'
            "def g():\n    pass\n"
        )

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion

    # frob:ticket T-1388
    def test_real_fmt001_fixer_rewrap_does_not_trip_the_guard(self, repo: Path) -> None:
        """T-1388: the incident this ticket reports is land's OWN pre-land
        Tier-A auto-fix pass (FMT001, `frob.gates._fmt_directives.
        format_paths`) rewrapping an out-of-scope file's `frob:waive`
        comment and then self-refusing on the very edit it just made.
        `TestWaiveRewrapNotDeletion`'s other tests prove the underlying
        `_uncommitted_out_of_scope_waive_deletions` mechanism (T-1468) is
        rewrap-insensitive against a HAND-WRITTEN rewrap; this test drives
        the same guard against the REAL fixer's OWN output instead, to
        pin the exact mechanism the ticket names rather than a synthetic
        stand-in for it."""
        # frob:tests \
        # tests/test_ticket_land.py::TestWaiveRewrapNotDeletion.test_real_fmt001_fixer_\
        # rewrap_does_not_trip_the_guard
        from frob.gates._fmt_directives import format_paths

        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used to fit on '
            'a single physical line under the default 88-col limit ok"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with an over-long single-line PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-fmt001-real-rewrap", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # This is what land's own pre-land Tier-A/FMT001 pass does: run
        # the real fixer against the whole tree (the pre-T-1404 unscoped
        # shape, still the fallback path when a touched-set cannot be
        # computed), rewrapping `other.py`'s over-long waiver line even
        # though `other.py` is entirely outside this ticket's scope.
        report = format_paths(wt, check_only=False, limit=88)
        assert any(c.path == "src/other.py" for c in report.changes)

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err


# frob:ticket T-1326
# frob:ticket T-1332
class TestCommittedWaiveDeletionRefusal:
    """T-1326: extends the T-1323 guard from the worktree's UNCOMMITTED
    state to its COMMITTED branch history (`merge-base..HEAD`) -- the
    reviewer-flagged laundering gap left open at T-1323's own approval,
    where a `frob:waive` deletion COMMITTED mid-ticket (rather than left
    uncommitted) rode the merge unattributed."""

    def test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-1", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Deletion of the waiver comment is COMMITTED to the branch, not
        # left dirty -- the exact laundering shape T-1323's own guard
        # could not see (it only ever inspected `git diff HEAD`).
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "unrelated cleanup that happens to drop a waiver")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion
        # Refused before any mutation: no merge attempt against main.
        assert (repo / "src" / "other.py").read_text().count("frob:waive") == 1

    def test_committed_in_scope_waive_deletion_is_allowed(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-2", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Retire stale waiver", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "retire the stale PERF001 waiver, in scope")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_committed_declared_in_done_report_waive_deletion_is_allowed(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-3", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nAlso removed the stale "
                    + "frob:waive PERF001 in src/other.py (found while "
                    + "working this ticket).\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "remove the stale waiver, declared in the Done report")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_merge_base_drift_deletion_on_main_side_not_counted(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # The waiver is deleted on MAIN's own side of the merge-base --
        # never touched by the landing ticket's branch at all -- so it
        # must NOT appear in the branch's `merge-base..HEAD` range and
        # must NOT be counted against this land.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, unrelated"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-4", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # main deletes the waiver AFTER the branch point -- not part of
        # the branch's own committed history.
        (repo / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(repo, "main-side: drop the PERF001 waiver, unrelated to the ticket")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1332
    def test_branch_merges_main_after_main_deletes_a_waiver_still_allowed(
        self, repo: Path
    ) -> None:
        """T-1332 acceptance [0]: unlike `test_merge_base_drift_deletion_
        on_main_side_not_counted` above (main deletes the waiver but the
        branch never re-syncs with main at all), this scenario has the
        landing branch run a real `git merge main` AFTER main's deletion
        commit -- the shape every agent worktree actually goes through
        (playbook section 1's mandatory warm-up merge, and any mid-ticket
        `git merge main`). The merge commit's own diff against the branch's
        PRE-merge tip textually contains the deletion (that is what a merge
        commit IS), so a naive `merge_base..HEAD` computed against a STALE
        merge-base would wrongly see it as the branch's own doing. `_true_
        merge_base` is computed FRESH at land time, so after the merge the
        true common ancestor advances to (at least) main's deletion commit
        itself, and the deletion drops out of `merge_base..HEAD` entirely --
        this test locks that in with a REAL `git merge main`, not just an
        unmerged branch-point scenario."""
        # frob:tests \
        # tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal.test_branch_merg\
        # es_main_after_main_deletes_a_waiver_still_allowed
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, unrelated"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-merge-main", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # main legitimately deletes the waiver AFTER the branch point.
        (repo / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(repo, "main-side: drop the PERF001 waiver, unrelated to the ticket")

        # The branch pulls that deletion in via a real merge -- the exact
        # mid-flight sync every worktree agent performs.
        _run(["git", "fetch", str(repo), "main:refs/remotes/origin/main"], wt)
        _run(["git", "merge", "refs/remotes/origin/main", "--no-edit"], wt)

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1550
    def test_already_landed_sibling_deletion_on_shared_worktree_not_recounted(
        self, repo: Path
    ) -> None:
        """T-1550: the exact multi-ticket-worktree shape T-1225/T-1444 hit
        for real. Ticket A declares its own out-of-scope waiver deletion in
        its Done report, lands (a REAL, non-dry-run land, so the deletion
        is now genuinely reflected on `main`) -- then ticket B, continuing
        on the SAME worktree branch (never re-merging main, exactly the
        shape a multi-ticket worktree agent runs per the playbook), lands
        with no waiver deletion of its own. Before T-1550, B's committed-
        history scan diffed from the STALE `merge_base` captured before A
        ever landed, so A's now-landed deletion still showed up in
        `merge_base..HEAD` and B's land was wrongly refused with
        `OutOfScopeWaiveDeletion` even though B never touched it and A's
        deletion is already legitimately on `main`."""
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, ticket A retires this"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-shared-1550", str(wt)], repo)

        # Ticket A: declares and commits the waiver deletion, then lands
        # for real -- `other.py`'s waiver is now genuinely gone on main.
        created_a = new_ticket(wt, _spec("Ticket A", scope=("src/feature.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(wt, tid_a, TicketState.PLANNED).is_ok
        assert transition(wt, tid_a, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket_a = loaded.danger_ok[tid_a]
        ticket_a = ticket_a.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket_a.body
                    + "\n## Done report\n\nAlso removed the stale "
                    + "frob:waive PERF001 in src/other.py (found while "
                    + "working this ticket).\n"
                ),
            }
        )
        assert write_ticket(wt, ticket_a).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "ticket A: retire the stale waiver, declared in Done report")

        land_a = land(repo, tid_a, wt, dry_run=False)
        assert land_a.is_ok, land_a.err
        assert "frob:waive" not in (repo / "src" / "other.py").read_text()

        # Ticket B: same worktree, same branch, no re-merge of main -- the
        # multi-ticket-worktree shape this ticket fixes. B never touches
        # other.py at all.
        created_b = new_ticket(wt, _spec("Ticket B", scope=("src/feature.py",)))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        _make_closeable(wt, tid_b)

        result_b = land(repo, tid_b, wt, dry_run=True)

        assert result_b.is_ok, result_b.err

    # frob:ticket T-1922
    def test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse(  # noqa: E501
        self, repo: Path
    ) -> None:
        """T-1922's own live incident: main REWORDS a `frob:waive` line's
        reason text (an unrelated, already-landed ticket's own edit, on a
        file this branch NEVER committed to at all) while this worktree's
        branch forked from an OLDER commit and has not re-merged main
        since. `_committed_waive_deletions`'s T-1550 two-dot content diff
        (`main_branch..HEAD`) reads the OLD text as "deleted" purely
        because main's current tip has the NEW text and this branch's own
        stale copy still has the OLD one -- even though the branch's own
        commits never touched the file. Before the T-1922 fix this
        refused with `OutOfScopeWaiveDeletion`; after it, the finding is
        filtered out because the file never appears in this branch's own
        `_branch_changed_files` set."""
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="old wording"\ndef g():\n    pass\n'
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-1922", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # This branch's OWN commit never touches other.py at all.
        (wt / "src" / "feature.py").write_text("# unrelated feature work\n")
        _commit_all(wt, "unrelated feature work, never touches other.py")

        # main independently REWORDS the same waiver line -- standing in
        # for T-1918's own real edit -- WITHOUT this worktree ever
        # merging it forward.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="new wording, unrelated edit"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "main-side: reword the waiver's reason text, unrelated")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1922
    def test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses(
        self, repo: Path
    ) -> None:
        """T-1922's own fix must not weaken the guard for the case it
        still needs to catch: a `frob:waive` deletion the landing
        branch's OWN commits made, out of scope and undeclared -- this is
        `test_committed_out_of_scope_undeclared_waive_deletion_refuses_
        before_merge` again, but run alongside an UNRELATED upstream
        reword on a different file, to prove the T-1922 filter narrows
        correctly rather than accidentally suppressing the whole check."""
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        (repo / "src" / "third.py").write_text(
            '# frob:waive DUP001 reason="old wording"\ndef h():\n    pass\n'
        )
        _commit_all(repo, "add other.py and third.py, each with a live waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-1922-genuine", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # The branch's OWN commit genuinely deletes other.py's waiver,
        # out of scope and undeclared.
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "unrelated cleanup that happens to drop a waiver")

        # main independently rewords third.py's waiver -- a file this
        # branch never touches -- so the filter has something real to
        # narrow away alongside the genuine finding.
        (repo / "src" / "third.py").write_text(
            '# frob:waive DUP001 reason="new wording, unrelated edit"\n'
            "def h():\n    pass\n"
        )
        _commit_all(repo, "main-side: reword third.py's waiver, unrelated")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion


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
