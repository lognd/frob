"""T-0323: `frob ticket merge-driver %O %A %B` -- the git merge-driver entry
point for `tickets.md` (docs/modules/tickets.md#git-merge-driver).

Two layers, matching this repo's `test_ticket_land.py` style:

1. `TestMergeDriverHandler` calls `frob.app.ticket_runner._merge_driver`
   directly against synthetic base/ours/theirs temp files -- fast, no git
   subprocess.
2. `TestMergeDriverViaRealGit` registers the driver with real `git config`
   and `.gitattributes` in a fixture repo, then runs an ACTUAL `git merge`
   between two branches that each independently appended a ticket near the
   same line -- the exact false-conflict class this ticket exists to
   eliminate -- and asserts git reports a clean merge with both sides'
   tickets present, not a conflict requiring a human.

frob:waive SCOPE001 reason="T-0323 scope omitted this file, filed T-draft-bc39c17f"
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _merge_driver
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    load_all,
    new_ticket,
    transition,
)
from frob.tickets._store import atomic_write, ledger_path, write_ticket


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


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


def _cfg(base: Path, ours: Path, theirs: Path, *, path: Path) -> AppConfig:
    return AppConfig(
        ticket_merge_base=base,
        ticket_merge_ours=ours,
        ticket_merge_theirs=theirs,
        ticket_path=path,
    )


class TestMergeDriverHandler:
    """`_merge_driver` against synthetic %O/%A/%B files -- no git subprocess."""

    def test_disjoint_ids_both_survive_the_splice(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_disjoint_ids_both_survive_the_splice  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")

        ours_created = new_ticket(root, _spec("Ours-side ticket"))
        assert ours_created.is_ok
        ours_text = ledger_path(root).read_text()

        theirs_root = tmp_path / "theirs"
        theirs_root.mkdir()
        theirs_ticket = ours_created.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Theirs-side ticket"}
        )
        atomic_write(ledger_path(theirs_root), "# Tickets\n\n")
        assert write_ticket(theirs_root, theirs_ticket).is_ok
        theirs_text = ledger_path(theirs_root).read_text()

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text("# Tickets\n\n")
        ours.write_text(ours_text)
        theirs.write_text(theirs_text)

        # A clean splice returns normally (no sys.exit) -- git treats the
        # command's plain exit(0) as a non-conflicted merge.
        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "Ours-side ticket" in result_text
        assert "Theirs-side ticket" in result_text

    def test_same_id_newer_state_wins_and_is_written_back(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_same_id_newer_state_wins_and_is_written_back  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")
        created = new_ticket(root, _spec("Shared ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(root).read_text()

        assert transition(root, tid, TicketState.PLANNED).is_ok
        theirs_text = ledger_path(root).read_text()

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text("# Tickets\n\n")
        ours.write_text(ours_text)
        theirs.write_text(theirs_text)

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "state: planned" in result_text
        assert "state: queued" not in result_text

    def test_malformed_theirs_exits_nonzero_and_leaves_ours_untouched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_malformed_theirs_exits_nonzero_and_leaves_ours_untouched  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")
        created = new_ticket(root, _spec("Ours ticket"))
        assert created.is_ok
        ours_text = ledger_path(root).read_text()

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text("# Tickets\n\n")
        ours.write_text(ours_text)
        theirs.write_text("# Tickets\n\n<!-- ticket:T-0002 -->\nno frontmatter here\n")

        with pytest.raises(SystemExit) as exc:
            _merge_driver(root, _cfg(base, ours, theirs, path=root))
        assert exc.value.code == 1

        # A failed splice must never overwrite ours -- git falls back to
        # its normal conflict report over whatever is on disk.
        assert ours.read_text() == ours_text

    def test_missing_args_exits_nonzero(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_missing_args_exits_nonzero  # noqa: E501
        cfg = AppConfig(ticket_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            _merge_driver(tmp_path, cfg)
        assert exc.value.code == 1


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger, the driver registered
    (`git config` + `.gitattributes`), and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    # .frob/ is local state (T-0178 telemetry writes .frob/telemetry.jsonl on
    # every CLI call); gitignore it so the clean-status assertions below are
    # not tripped by an incidental untracked telemetry file.
    (main_repo / ".gitignore").write_text(".frob/\n")
    (main_repo / ".gitattributes").write_text("tickets.md merge=frob-ledger\n")
    _run(
        [
            "git",
            "config",
            "merge.frob-ledger.name",
            "frob ticket ledger splice",
        ],
        main_repo,
    )
    _run(
        [
            "git",
            "config",
            "merge.frob-ledger.driver",
            "uv run frob ticket merge-driver %O %A %B",
        ],
        main_repo,
    )
    _commit_all(main_repo, "init")
    return main_repo


class TestMergeDriverViaRealGit:
    """End-to-end: a real `git merge` between two branches that each
    independently appended a ticket near the same ledger line -- the
    false-conflict class T-0323 removes the manual splice_ledger-by-hand
    step for."""

    def test_real_git_merge_auto_splices_both_sides_append(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit.test_real_git_merge_auto_splices_both_sides_append  # noqa: E501
        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        feature_created = new_ticket(repo, _spec("Feature-branch ticket"))
        assert feature_created.is_ok
        feature_tid = feature_created.danger_ok.id
        _commit_all(repo, "feature: file a ticket")

        _run(["git", "checkout", "-q", "main"], repo)
        main_created = new_ticket(repo, _spec("Main-branch ticket"))
        assert main_created.is_ok
        main_tid = main_created.danger_ok.id
        _commit_all(repo, "main: file a ticket")

        merge = subprocess.run(
            ["git", "merge", "-q", "--no-edit", "feature"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, (
            f"expected the frob-ledger driver to auto-splice cleanly, got "
            f"a real conflict instead: stdout={merge.stdout!r} "
            f"stderr={merge.stderr!r}"
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

        merged = load_all(repo)
        assert merged.is_ok
        assert feature_tid in merged.danger_ok
        assert main_tid in merged.danger_ok
        assert merged.danger_ok[feature_tid].title == "Feature-branch ticket"
        assert merged.danger_ok[main_tid].title == "Main-branch ticket"
