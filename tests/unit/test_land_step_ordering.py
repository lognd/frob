"""T-1932/T-1931: `land()`'s post-mutation re-verification of the
cross-ticket leakage guard.

THE GENERAL DEFECT (T-1932): on the land path, a guard's refusal can be
silently invalidated by a mutation that runs AFTER the guard already made
its decision. Three separate incidents (T-1903, T-1910/T-1920, T-1931)
shared this one shape; this module locks in the fix for the T-1931
instance -- `_check_cross_ticket_leakage`'s preflight copy (run inside
`_land_precheck`, before any git mutation) reads ONLY committed history
(`_branch_changed_files` diffs `base_ref...HEAD`), so it is structurally
blind to a mutation that lands as an UNCOMMITTED disk write -- exactly
what `frob ticket land`'s own T-1175 pre-land auto-fix absorption
(`_absorb_pre_land_fixes`, called by the CLI before `land()` even runs)
produces. `_reverify_cross_ticket_leakage_post_mutation` closes this by
re-running the identical check a second time, inside `land()` itself,
immediately after the wip-commit (`_land_merge_stage`) has captured every
prior mutation into history.

Real git fixture repos throughout, matching `tests/unit/test_land_cross_
ticket_leakage.py`'s own style and fixture helpers (deliberately
duplicated per that module's own DUP001 waiver precedent, not imported
across test files)."""

from __future__ import annotations

import inspect
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
    _land_locked,
    _reverify_cross_ticket_leakage_post_mutation,
    land,
)
from frob.tickets._models import LandError
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init/commit/closeable boilerplate already \
# duplicated verbatim across tests/unit/test_land_cross_ticket_leakage.py and others \
# -- see that module's own identical waiver for the same rationale (each land/ticket \
# test module owns its own tiny copy rather than importing across test files)"
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


# frob:ticket T-1932
# frob:ticket T-1931
class TestCrossTicketLeakagePostMutationRecheck:
    """T-1931's live repro, modelled directly: the guard refuses once
    against a committed leak; the leak is reverted+committed (satisfying
    the preflight check); an auto-fix pass (Tier-A, standing in for the
    real `_absorb_pre_land_fixes` step that runs before `land()` is ever
    called) then silently re-writes the SAME content back to disk as an
    UNCOMMITTED change -- exactly what `land()` sees at call time in the
    real T-1931 incident. Before the T-1932 fix, `land()` succeeds anyway
    (the preflight check never sees the uncommitted write, and nothing
    re-checks after the wip-commit folds it into history). After the fix,
    the post-mutation re-check catches it and the land still refuses."""

    def _seed_leaked_worktree(self, repo: Path) -> tuple[Path, str, str]:
        """T-1370's own precedent (`test_refuses_when_sibling_ticket_
        still_open`): TWO worktrees, so the same-worktree exemption
        (`_find_leaked_tickets`'s T-1370 rule -- a sibling leased to the
        SAME worktree as the landing ticket is never reported as leaked)
        does not mask this test. `held_id` is leased to `wt2`, standing
        in for a different agent's own series; its work is then
        simulated leaking onto `wt`'s branch, matching the real T-1931
        incident's own committed-then-refused starting state."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)
        wt2 = repo.parent / "wt2"
        _run(["git", "worktree", "add", "-b", "other-agent", str(wt2)], repo)

        held = new_ticket(wt2, _spec("Paused work", scope=("src/held.py",)))
        assert held.is_ok
        held_id = held.danger_ok.id
        assert transition(wt2, held_id, TicketState.PLANNED).is_ok
        assert transition(wt2, held_id, TicketState.IN_PROGRESS).is_ok

        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "held.py").write_text(
            "# T-held's own work, leaked onto series-a\n"
        )
        held_ticket = load_all(wt2).danger_ok[held_id]
        assert write_ticket(wt, held_ticket).is_ok
        _commit_all(wt, f"{held_id}: leaked onto series-a")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        return wt, held_id, landing_id

    def test_guard_refusal_survives_an_uncommitted_reintroduction(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck.test_guard_refusal_survives_an_uncommitted_reintroduction  # noqa: E501
        wt, held_id, landing_id = self._seed_leaked_worktree(repo)

        # Attempt 1: land() correctly refuses -- held.py is a committed
        # leak of held_id's own open scope.
        first = land(repo, landing_id, wt, dry_run=False)
        assert first.is_err
        assert first.danger_err == LandError.CrossTicketLeakage

        # The leak is reverted BY HAND and committed, exactly as T-1931's
        # narrative describes -- this satisfies the preflight check on its
        # own (nothing committed carries held_id's scope any more).
        (wt / "src" / "held.py").unlink()
        _commit_all(wt, f"{landing_id}: revert leaked held.py before retry")

        # An auto-fix pass (standing in for the real `_absorb_pre_land_
        # fixes`, which runs BEFORE `land()` is invoked in the real CLI)
        # silently re-writes the identical leaked content back to disk,
        # UNCOMMITTED -- the exact shape Tier-A's undeclared-capability
        # fixer produced in the real incident.
        (wt / "src" / "held.py").write_text(
            "# T-held's own work, deliberately paused\n"
        )

        # Attempt 2: the preflight check (committed-diff-only) would pass
        # -- the wip-commit is what folds the uncommitted reintroduction
        # into history, and the T-1932 post-mutation re-check is what must
        # catch it there.
        second = land(repo, landing_id, wt, dry_run=False)

        assert second.is_err, (
            "land() must still refuse: held.py was silently reintroduced "
            "as an uncommitted mutation after the preflight leakage check "
            "already ran -- the exact T-1931 shape"
        )
        assert second.danger_err == LandError.CrossTicketLeakage
        # Nothing landed -- main's tree carries neither file.
        assert not (repo / "src" / "fix.py").exists()
        assert not (repo / "src" / "held.py").exists()

    def test_clean_land_is_unaffected(self, repo: Path) -> None:
        # frob:tests tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck.test_clean_land_is_unaffected  # noqa: E501
        # Sanity/regression guard: the new post-mutation re-check must not
        # false-positive an ordinary, single-ticket land with no leakage
        # at all -- the common case every land takes.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo", str(wt)], repo)
        created = new_ticket(wt, _spec("Solo work", scope=("src/solo.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "solo.py").write_text("# solo work\n")
        _commit_all(wt, "add solo work")

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "solo.py").exists()


# frob:ticket T-1932
class TestPostMutationRecheckOrdering:
    """Acceptance 1 (a single documented, enforced ordering) and
    acceptance 4 (a NEW guard/auto-fix handler cannot silently violate it)
    of T-1932, made mechanically checkable rather than left as prose: the
    post-mutation re-check call must appear, in `_land_locked`'s own
    source, strictly AFTER the `_land_merge_stage` call whose wip-commit
    is what makes the re-check meaningful. A future edit that moves the
    re-check ahead of the wip-commit (reintroducing the exact T-1931
    ordering bug) fails this test; so does deleting the re-check
    entirely (the source pattern simply would not be found)."""

    def test_leakage_recheck_runs_after_the_wip_commit_in_land_locked(self) -> None:
        # frob:tests tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering.test_leakage_recheck_runs_after_the_wip_commit_in_land_locked  # noqa: E501
        source = inspect.getsource(_land_locked)
        merge_stage_pos = source.index("_land_merge_stage(")
        recheck_pos = source.index("_reverify_cross_ticket_leakage_post_mutation(")
        assert merge_stage_pos < recheck_pos, (
            "_reverify_cross_ticket_leakage_post_mutation must be called "
            "AFTER _land_merge_stage's wip-commit -- calling it earlier "
            "reproduces the T-1931 ordering defect (the guard would see "
            "pre-mutation state again)"
        )

    def test_post_mutation_recheck_delegates_to_the_same_check_preflight_uses(
        self,
    ) -> None:
        # frob:tests tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering.test_post_mutation_recheck_delegates_to_the_same_check_preflight_uses  # noqa: E501
        # Documents (and mechanically pins) T-1932 acceptance 4's answer
        # for THIS guard: there is exactly one leakage-check
        # implementation (`_check_cross_ticket_leakage`); the preflight
        # and post-mutation call sites both delegate to it rather than
        # each maintaining their own copy that could drift apart.
        source = inspect.getsource(_reverify_cross_ticket_leakage_post_mutation)
        assert "_check_cross_ticket_leakage(" in source
