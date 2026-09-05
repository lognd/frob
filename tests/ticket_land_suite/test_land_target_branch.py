"""T-3787: `frob ticket land` onto a NON-main target branch.

Covers the three acceptance axes of the target-branch feature:
  (a) a real land onto a dedicated `dev` branch lands its commit on `dev`
      and NOT on `main`, reports `target_branch="dev"`, and the LAND-PROOF
      ancestry check verifies against `dev`;
  (b) the DEFAULT path (no target given) is unchanged -- the commit lands
      on `main` and `LandReport.target_branch` is `"main"`;
  (c) a missing target branch, and a target branch that root is not
      checked out on, both refuse clearly with
      `LandError.TargetBranchInvalid` instead of landing onto a wrong ref.

The land pipeline publishes onto and resyncs root's OWN checked-out
branch, so `--branch <name>` is validated to name an existing branch that
root is currently on; this suite exercises exactly that contract.
"""

import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner._land_cmd import _is_ancestor_with_retry, _land_proof_checks
from frob.tickets import TicketState, new_ticket
from frob.tickets._land import land
from frob.tickets._models import LandError
from frob.tickets._store import load_all
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _make_closeable,
    _run,
    _spec,
)

pytestmark = pytest.mark.heavy_subprocess


def _is_ancestor(root: Path, sha: str, branch: str) -> bool:
    """`git merge-base --is-ancestor sha branch` as a bool (returncode 0
    means `sha` is reachable from `branch`) -- the raw git check LAND-PROOF
    wraps, used here to assert WHICH branch a landed commit really sits on."""
    return (
        subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", sha, branch],
            capture_output=True,
        ).returncode
        == 0
    )


class TestLandOntoNonMainBranch:
    """Landing onto a dedicated dev branch while `main` stays frozen."""

    # frob:tests src/frob/tickets/_land.py::land kind="integration"
    # frob:tests src/frob/tickets/_land.py::_resolve_land_target_branch \
    # kind="integration"
    def test_real_land_onto_dev_lands_on_dev_not_main(self, repo: Path) -> None:
        # Freeze `main` at a known sha, then move root onto `dev`.
        main_sha_before = _run(["git", "rev-parse", "main"], repo).stdout.strip()
        _run(["git", "checkout", "-q", "-b", "dev"], repo)

        wt = repo.parent / "wt-dev"
        _run(["git", "worktree", "add", "-b", "feature-dev", str(wt)], repo)
        created = new_ticket(wt, _spec("Add dev widget", scope=("src/devw.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "devw.py").write_text("# dev widget\n")
        _commit_all(wt, "add dev widget")

        result = land(repo, tid, wt, dry_run=False, target_branch="dev")
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.target_branch == "dev"
        assert report.commit_sha is not None

        # The landed commit is on dev, and main is untouched.
        assert _is_ancestor(repo, report.commit_sha, "dev")
        assert not _is_ancestor(repo, report.commit_sha, "main")
        assert (
            _run(["git", "rev-parse", "main"], repo).stdout.strip() == main_sha_before
        )

        # LAND-PROOF verifies against dev, and would (correctly) NOT verify
        # against main -- the exact bug this ticket fixes.
        assert _is_ancestor_with_retry(repo, report.commit_sha, target_branch="dev")
        assert not _is_ancestor_with_retry(
            repo, report.commit_sha, target_branch="main"
        )
        ancestor_ok, _state, state_ok = _land_proof_checks(
            repo, report.final_id, report.commit_sha, target_branch="dev"
        )
        assert ancestor_ok and state_ok

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


class TestDefaultTargetUnchanged:
    """The no-flag default path must stay byte-for-byte the historical
    land-onto-main behavior (top acceptance criterion)."""

    # frob:tests src/frob/tickets/_land.py::land kind="integration"
    def test_default_land_targets_main_and_reports_main(self, repo: Path) -> None:
        wt = repo.parent / "wt-main"
        _run(["git", "worktree", "add", "-b", "feature-main", str(wt)], repo)
        created = new_ticket(wt, _spec("Add main gadget", scope=("src/mg.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "mg.py").write_text("# main gadget\n")
        _commit_all(wt, "add main gadget")

        # No target_branch -> historical behavior: lands onto main.
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.target_branch == "main"
        assert report.commit_sha is not None
        assert _is_ancestor(repo, report.commit_sha, "main")

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


class TestTargetBranchRefusals:
    """A target that does not exist, or that root is not checked out on,
    refuses rather than landing onto the wrong ref."""

    # frob:tests src/frob/tickets/_land.py::_resolve_land_target_branch \
    # kind="integration"
    def test_missing_target_branch_refuses(self, repo: Path) -> None:
        wt = repo.parent / "wt-missing"
        _run(["git", "worktree", "add", "-b", "feature-missing", str(wt)], repo)
        created = new_ticket(wt, _spec("Add x", scope=("src/x.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "x.py").write_text("# x\n")
        _commit_all(wt, "add x")

        result = land(repo, tid, wt, dry_run=False, target_branch="does-not-exist")
        assert result.is_err
        assert result.danger_err is LandError.TargetBranchInvalid
        # Nothing landed: the ticket never reached main's ledger.
        landed = load_all(repo)
        assert landed.is_ok
        assert tid not in landed.danger_ok

    # frob:tests src/frob/tickets/_land.py::_resolve_land_target_branch \
    # kind="integration"
    def test_target_branch_root_is_not_on_refuses(self, repo: Path) -> None:
        # `dev` exists but root stays checked out on `main`.
        _run(["git", "branch", "dev"], repo)
        wt = repo.parent / "wt-noton"
        _run(["git", "worktree", "add", "-b", "feature-noton", str(wt)], repo)
        created = new_ticket(wt, _spec("Add y", scope=("src/y.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "y.py").write_text("# y\n")
        _commit_all(wt, "add y")

        result = land(repo, tid, wt, dry_run=False, target_branch="dev")
        assert result.is_err
        assert result.danger_err is LandError.TargetBranchInvalid
