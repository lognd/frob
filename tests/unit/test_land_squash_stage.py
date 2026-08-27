"""T-3089: `_land_squash_apply`'s `stage` target -- the checkout the whole
six-stage squash-apply transaction is performed in.

Deliberately a SEPARATE module from tests/test_ticket_land.py: that file's
`land()`-driven tests leave `FROB_WORKTREE` set in-process, so any test
running after them in the same worker refuses with
`TicketError.WorktreeLeaseViolation` (145 such refusals measured on an
unmodified `main`, so it is pre-existing and not this ticket's doing).
Evidence that has to RESOLVE cannot live behind that, so these two build
their own fixture repo from git plumbing and touch no ticket-mutating verb.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import frob.tickets._land_squash as _land_squash_mod
from frob.tickets._models import Origin, Ticket, TicketKind, TicketSpec
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import _serialize_ticket, atomic_write, v2_ticket_path


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """`subprocess.run` with `check=True` against `cwd` -- the fixture's
    only way of talking to git, kept identical in shape to the helper
    tests/test_ticket_land.py uses."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _seed(root: Path, ticket_id: str, scope: tuple[str, ...]) -> Ticket:
    """Write a QUEUED ticket into v2-mode storage (`tickets/<id>/
    ticket.md`), which is what flips `_store_mode(root)` to 'v2' and lets
    the land skip the monofile ledger splice entirely."""
    ticket = _ticket_from_spec(
        ticket_id,
        TicketSpec(
            title="Stage target",
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            scope=scope,
        ),
        (),
    )
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


@pytest.fixture
def v2_main(tmp_path: Path) -> Path:
    """A v2-mode main checkout with one committed ticket directory and one
    committed source file."""
    root = tmp_path / "v2main"
    root.mkdir(parents=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")
    _seed(root, "T-3000", ("src/seed.py",))
    (root / "src").mkdir()
    (root / "src" / "feature.py").write_text("# landed feature\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", "init v2"], root)
    return root


def _prepare(v2_main: Path, slug: str) -> tuple[Path, Ticket, str, str]:
    """A finalized feature worktree branch plus root's pre-land tip -- the
    exact inputs `_land_locked` hands `_land_squash_apply`."""
    wt = v2_main.parent / f"wt-stage-{slug}"
    _run(["git", "worktree", "add", "-q", "-b", f"stage-{slug}", str(wt)], v2_main)
    ticket_id = f"T-31{slug}"
    ticket = _seed(wt, ticket_id, ("src/staged.py",))
    (wt / "src" / "staged.py").write_text("# staged by the disposable stage\n")
    _run(["git", "add", "-A"], wt)
    _run(["git", "commit", "-q", "-m", f"add staged.py for {ticket_id}"], wt)
    pre_land_tip = _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip()
    return wt, ticket, ticket_id, pre_land_tip


# frob:ticket T-3089
class TestSquashApplyStageTarget:
    """T-3089's must-stay-quiet / must-fire pair for the `stage` parameter.

    Omitting `stage` must keep the historical behavior byte for byte (the
    whole transaction happens in the shared checkout, exactly as every land
    does today); passing a disposable worktree must move ALL of it off that
    checkout -- root's HEAD, index and working tree untouched, the landing
    commit sitting on the disposable stage instead."""

    def test_default_stage_runs_the_whole_transaction_in_root(
        self, v2_main: Path
    ) -> None:
        # frob:tests tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget.test_default_stage_runs_the_whole_transaction_in_root  # noqa: E501
        """MUST STAY QUIET: with no `stage` given, the landing commit is
        made on `root` and carries the worktree's changeset, exactly as
        before this parameter existed."""
        wt, ticket, ticket_id, pre_land_tip = _prepare(v2_main, "01")

        result = _land_squash_mod._land_squash_apply(
            v2_main,
            wt,
            ticket,
            ticket_id,
            ticket_id,
            False,
            False,
            "main",
            pre_land_tip=pre_land_tip,
        )

        assert result.is_ok, result.err
        assert (v2_main / "src" / "staged.py").exists()
        new_tip = _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip()
        assert new_tip != pre_land_tip
        assert _run(["git", "status", "--porcelain"], v2_main).stdout.strip() == ""

    def test_explicit_stage_leaves_root_completely_untouched(
        self, v2_main: Path, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget.test_explicit_stage_leaves_root_completely_untouched  # noqa: E501
        """MUST FIRE: with an explicit disposable `stage`, root's HEAD,
        index and working tree are all exactly as they were -- no
        intermediate staged squash is ever observable there -- while the
        landing commit and the full changeset land on the stage checkout.

        This is the point of the parameter: the staged-but-uncommitted
        window every sibling agent's `git status` could previously observe
        in the shared root moves onto a throwaway checkout nobody polls."""
        wt, ticket, ticket_id, pre_land_tip = _prepare(v2_main, "02")
        stage = tmp_path / "disposable-stage"
        _run(
            ["git", "worktree", "add", "-q", "--detach", str(stage), pre_land_tip],
            v2_main,
        )

        result = _land_squash_mod._land_squash_apply(
            v2_main,
            wt,
            ticket,
            ticket_id,
            ticket_id,
            False,
            False,
            "main",
            pre_land_tip=pre_land_tip,
            stage=stage,
        )

        assert result.is_ok, result.err
        # Root: nothing moved, nothing staged, nothing written.
        assert (
            _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip() == pre_land_tip
        )
        assert _run(["git", "status", "--porcelain"], v2_main).stdout.strip() == ""
        assert _run(["git", "diff", "--cached", "--name-only"], v2_main).stdout == ""
        assert not (v2_main / "src" / "staged.py").exists()
        # Stage: the real landing commit, carrying the real changeset.
        stage_tip = _run(["git", "rev-parse", "HEAD"], stage).stdout.strip()
        assert stage_tip != pre_land_tip
        landed = _run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], stage
        ).stdout.split()
        assert "src/staged.py" in landed
        assert (stage / "src" / "staged.py").exists()
