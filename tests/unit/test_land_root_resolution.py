"""T-1638: regression tests for `land()`'s root-resolution guard
(`_refuse_if_root_is_worktree`) against the second, more dangerous shape
`_resolve_primary_checkout` did not previously cover -- `root` resolving
(via a shell's sticky cwd) to a DIFFERENT registered worktree than the one
named by `--worktree`, rather than the identical path T-0795/T-1003
already handle. Real git fixture repos throughout, matching `tests/
test_ticket_land.py::TestLandChainedCdRootResolution`'s own style for
exercising this exact guard family."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, TicketSpec, TicketState, new_ticket
from frob.tickets._land import land
from frob.tickets._models import LandError
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init/commit/closeable boilerplate already \
# duplicated verbatim across tests/test_ticket_land.py, \
# tests/unit/test_land_cross_ticket_leakage.py, and others -- each land/ticket test \
# module owns its own tiny copy rather than importing across test files (the existing \
# convention this repo's test suite already follows for fixture helpers)"
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
    from frob.tickets import transition

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


# frob:ticket T-1638
class TestRootResolvesToADifferentWorktree:
    """The T-1638 incident shape: a shell's cwd is sitting inside worktree
    A (some OTHER ticket's worktree, not the one being landed) when `frob
    ticket land <id> --worktree B` runs. `root` (defaulted to cwd => A)
    and `worktree` (B) are trivially unequal, so the pre-T-1638
    root==worktree check alone never fires -- yet landing must still
    refuse, since `root` is not the true primary checkout."""

    def test_refuses_when_root_is_a_different_registered_worktree(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree.test_refuses_when_root_is_a_different_registered_worktree  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        wt_a = repo.parent / "wt-a"
        _run(["git", "worktree", "add", "-b", "ticket-a", str(wt_a)], repo)
        wt_b = repo.parent / "wt-b"
        _run(["git", "worktree", "add", "-b", "ticket-b", str(wt_b)], repo)

        created = new_ticket(wt_b, _spec("Independent fix", scope=("src/fix.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt_b, tid)
        (wt_b / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt_b, f"{tid}: independent fix")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        before_a_sha = _run(["git", "rev-parse", "HEAD"], wt_a).stdout.strip()

        # Simulate cwd sitting inside wt_a (a DIFFERENT worktree entirely)
        # while landing tid from wt_b: root=wt_a, worktree=wt_b.
        result = land(wt_a, tid, wt_b, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        # Nothing mutated anywhere: neither the real primary checkout nor
        # the unrelated worktree the bug would have silently treated as
        # "main".
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == (
            before_main_sha
        )
        assert _run(["git", "rev-parse", "HEAD"], wt_a).stdout.strip() == before_a_sha
        assert not (repo / "src" / "fix.py").exists()
        assert not (wt_a / "src" / "fix.py").exists()

    def test_root_equal_to_the_primary_checkout_is_unaffected(
        self, repo: Path
    ) -> None:
        # frob:tests tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree.test_root_equal_to_the_primary_checkout_is_unaffected  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        # Sanity companion: the ordinary case (root IS the true primary
        # checkout, worktree is some linked worktree) must still land
        # cleanly -- the new T-1638 check is a no-op here since `_resolve_
        # primary_checkout(root)` resolves back to `root` itself.
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
