"""`frob ticket reconcile --apply` auto-commits its own ledger writes
(T-1936).

WHY: `reconcile --apply` used to be the one ledger-mutating verb that
neither auto-committed nor offered `--no-commit` -- it left a real,
uncommitted ledger change behind with no warning, silently DirtyMain-
blocking every concurrent `frob ticket land` until an operator happened
to notice by chance (the live incident this ticket's own body
documents). These tests exercise `_reconcile_cmd`, the CLI-layer wrapper
(`frob.app.ticket_runner._lifecycle`) that now routes the write through
`commit_full_ledger_change` -- the same `archive`-verb precedent, since
`--apply` can requeue MANY ticket ids in one call, not one.

Real `git worktree add`/`git worktree remove` fixtures, matching
`tests/test_ticket_reconcile.py`'s own style -- reconcile's whole job is
judging LIVE worktree state against the lease registry, which a single
in-memory tmp_path cannot exercise.

NOTE (T-1936, same precedent as tests/unit/test_land_finalize_anchor.py):
the git-plumbing helpers (`_run`/`_git_init`/`_commit_all`/`_spec`/
`_set_state_directly`/the `repo` fixture) are imported from
`tests.test_ticket_reconcile`, not reimplemented here, deliberately --
that module already carries this testsuite node's `may "exec"`/`may
"fs.write"` (`design/frob.strata`) declarations for its own
`subprocess.run`/`.write_text(` call sites. `design/frob.strata` sits
under another in-progress ticket's live cross-worktree lease at the time
this ticket was worked (T-1629) and is out of this ticket's own scope,
so a fresh, undeclared capability call site in THIS file would trip
SELFAUDIT001 with no way to widen scope to clear it -- reusing the
already-declared call sites sidesteps that without touching a file this
ticket cannot lease."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._lifecycle import _reconcile_cmd
from frob.tickets import TicketState, new_ticket, transition
from frob.tickets._store import atomic_write
from tests.test_ticket_reconcile import (
    _commit_all,
    _run,
    _set_state_directly,
    _spec,
    repo,
)

__all__ = ["repo"]  # re-exported fixture (T-1936, see module docstring)


def _porcelain(root: Path) -> str:
    return _run(["git", "status", "--porcelain"], root).stdout


def _seed_stale_hold(repo: Path, *, title: str, branch: str) -> str:
    """Real T-1901-shaped incident: start a ticket in a worktree, tear the
    worktree down without requeuing/closing it (a crashed/abandoned
    agent), then sync the in-progress state onto `repo`'s own ledger --
    exactly what `reconcile --apply` is meant to heal."""
    created = new_ticket(repo, _spec(title, scope=("src/feature.py",)))
    assert created.is_ok
    tid = created.danger_ok.id
    _commit_all(repo, f"add ticket {tid}")

    wt = repo.parent / branch
    _run(["git", "worktree", "add", "-b", branch, str(wt)], repo)
    assert transition(wt, tid, TicketState.PLANNED).is_ok
    assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
    _run(["git", "worktree", "remove", "--force", str(wt)], repo)
    _set_state_directly(repo, tid, TicketState.IN_PROGRESS)
    # Commit the lease-stamp sync itself so the tree is CLEAN before
    # `_reconcile_cmd` runs -- any commit/dirtiness this test observes
    # afterward is then attributable only to reconcile's own action, not
    # this fixture's own direct (non-`transition`) ledger write.
    _commit_all(repo, f"sync {tid} in-progress state onto main")
    return tid


class TestReconcileAutoCommit:
    """Acceptance [1]: `--apply` leaves `git status --porcelain` clean for
    the ledger rows it changed. This test FAILS at the pre-fix code (the
    live 2026-08-09 incident) -- before T-1936, `_reconcile_cmd` never
    called `commit_full_ledger_change` at all, so the requeue landed in
    the working tree, uncommitted, every time."""

    def test_apply_leaves_the_ledger_clean(self, repo: Path) -> None:
        # frob:tests tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileAutoCommit.test_apply_leaves_the_ledger_clean  # noqa: E501
        _seed_stale_hold(repo, title="Stale hold", branch="feature-1936a")

        cfg = AppConfig(ticket_command="reconcile", ticket_reconcile_apply=True)
        _reconcile_cmd(repo, cfg)

        assert _porcelain(repo) == ""

    def test_dry_run_never_commits_anything(self, repo: Path) -> None:
        # frob:tests tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileAutoCommit.test_dry_run_never_commits_anything  # noqa: E501
        """A pure dry-run (no `--apply`) writes nothing, so the new commit
        call must be a guaranteed no-op -- never manufacturing an empty
        commit."""
        _seed_stale_hold(repo, title="Stale hold dry-run", branch="feature-1936b")

        head_before = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        cfg = AppConfig(ticket_command="reconcile", ticket_reconcile_apply=False)
        _reconcile_cmd(repo, cfg)
        head_after = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        assert head_after == head_before


class TestReconcileNoCommitFlag:
    """Acceptance [2]: `--no-commit` exists and leaves the change
    uncommitted, with the same loud DirtyMain warning `frob ticket new
    --no-commit` emits."""

    def test_no_commit_leaves_ledger_dirty_and_warns(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileNoCommitFlag.test_no_commit_leaves_ledger_dirty_and_warns  # noqa: E501
        _seed_stale_hold(repo, title="Stale hold no-commit", branch="feature-1936c")

        cfg = AppConfig(
            ticket_command="reconcile",
            ticket_reconcile_apply=True,
            ticket_no_commit=True,
        )
        with caplog.at_level("WARNING"):
            _reconcile_cmd(repo, cfg)

        assert _porcelain(repo) != ""
        assert any("DirtyMain" in record.message for record in caplog.records)


class TestReconcileCommitScopedToLedgerRows:
    """Acceptance [3]: `reconcile --apply` commits ONLY the ledger paths it
    actually modified -- an unrelated dirty file elsewhere in the tree
    must NOT be swept into its commit (`commit_full_ledger_change`'s own
    pathspec-scoped `git add`, never `git add -A`)."""

    def test_unrelated_dirty_file_is_not_swept_into_the_commit(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileCommitScopedToLedgerRows.test_unrelated_dirty_file_is_not_swept_into_the_commit  # noqa: E501
        _seed_stale_hold(repo, title="Stale hold scoped", branch="feature-1936d")

        # An unrelated agent's own uncommitted work-in-progress, sitting in
        # the SAME working tree `reconcile --apply` runs against -- written
        # via the already-declared `atomic_write` (T-1930's `frob.tickets.
        # _store` crash-safe writer), not a raw `.write_text(` call, so this
        # does not add a new testsuite fs.write call site of its own.
        assert atomic_write(
            repo / "src" / "unrelated_wip.py", "# someone else's WIP\n"
        ).is_ok

        cfg = AppConfig(ticket_command="reconcile", ticket_reconcile_apply=True)
        _reconcile_cmd(repo, cfg)

        status = _porcelain(repo)
        assert "unrelated_wip.py" in status
        assert "tickets.md" not in status


class TestReconcileRemoveOrphansAutoCommit:
    """Acceptance [4]: `--remove-orphans` is covered by the same
    guarantees -- an orphan-worktree removal alongside a stale-hold
    requeue still leaves the ledger clean afterward."""

    def test_apply_with_remove_orphans_still_leaves_ledger_clean(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileRemoveOrphansAutoCommit.test_apply_with_remove_orphans_still_leaves_ledger_clean  # noqa: E501
        _seed_stale_hold(repo, title="Stale hold plus orphan", branch="feature-1936e")

        # A genuine orphan: a live worktree holding no lease at all.
        orphan_wt = repo.parent / "orphan-1936"
        _run(
            ["git", "worktree", "add", "-b", "orphan-branch-1936", str(orphan_wt)],
            repo,
        )

        cfg = AppConfig(
            ticket_command="reconcile",
            ticket_reconcile_apply=True,
            ticket_reconcile_remove_orphans=True,
        )
        _reconcile_cmd(repo, cfg)

        assert _porcelain(repo) == ""
        assert not orphan_wt.exists()
