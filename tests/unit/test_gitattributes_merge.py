"""T-1873: `rapid-debt.jsonl`/`force-overrides.jsonl` merge via git's
BUILT-IN `merge=union` driver (`.gitattributes`), not a new frob driver --
union is exactly append-only "keep both sides" semantics and needs no
per-clone `git config` registration, unlike `merge=frob-ledger`
(tests/test_ticket_merge_driver.py's own precedent, which DOES need
registration and is the wrong shape for a plain append-only file).

Verifies by REPRODUCTION, matching the ticket body's explicit requirement:
two branches each appending a different record to the same tracked file,
merged via a REAL `git merge`, both records surviving with zero conflict
markers and no manual step -- not by inspecting `.gitattributes` text.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="minimal git-fixture-repo helper duplicated verbatim across \
# tests/test_gates_tick005.py, tests/test_serve_daemon.py, and \
# tests/test_ticket_merge_driver.py (this ticket's own closest sibling test file) -- \
# extracting a shared tests/conftest.py fixture is a real, worthwhile follow-up but \
# touches N other test files pre-dating this one, out of T-1873's declared scope"
def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:waive DUP001 reason="minimal git-commit-all helper duplicated verbatim across \
# tests/test_gates_tick005.py, tests/test_serve_daemon.py, and \
# tests/test_ticket_land.py -- same shared-fixture-extraction follow-up as _git_init \
# above, out of T-1873's declared scope"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout carrying THIS repo's real `.gitattributes` rule
    for `rapid-debt.jsonl` (T-1873) plus one seed record, so the fixture
    exercises the actual rule under test rather than a hand-rewritten
    copy that could silently drift from it."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / ".gitignore").write_text(".frob/\n.coverage*\n")
    real_gitattributes = Path(__file__).parents[2] / ".gitattributes"
    (main_repo / ".gitattributes").write_text(real_gitattributes.read_text())
    (main_repo / "rapid-debt.jsonl").write_text(
        '{"commit": "seed0000", "skipped": "post-land-unscoped-sweep-deferred", '
        '"ticket": "T-0000"}\n'
    )
    _commit_all(main_repo, "init")
    return main_repo


class TestRapidDebtUnionMerge:
    """T-1873 item 3: reproduction, not inspection."""

    def test_two_branches_appending_different_records_both_survive(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_gitattributes_merge.py::TestRapidDebtUnionMerge.test_two_bran\
        # ches_appending_different_records_both_survive
        _run(["git", "checkout", "-q", "-b", "worktree-a"], repo)
        with (repo / "rapid-debt.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(
                '{"commit": "aaaaaaaa", "skipped": "land-evidence-scope-unbound", '
                '"ticket": "T-1111"}\n'
            )
        _commit_all(repo, "worktree-a: rapid debt record")

        _run(["git", "checkout", "-q", "main"], repo)
        _run(["git", "checkout", "-q", "-b", "worktree-b"], repo)
        with (repo / "rapid-debt.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(
                '{"commit": "bbbbbbbb", "skipped": "post-land-unscoped-sweep-deferred", '
                '"ticket": "T-2222"}\n'
            )
        _commit_all(repo, "worktree-b: rapid debt record")

        _run(["git", "checkout", "-q", "worktree-a"], repo)
        merge = subprocess.run(
            ["git", "merge", "-q", "--no-edit", "worktree-b"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, (
            f"expected merge=union to auto-resolve cleanly, got a real "
            f"conflict instead: stdout={merge.stdout!r} stderr={merge.stderr!r}"
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

        text = (repo / "rapid-debt.jsonl").read_text()
        assert '"commit": "aaaaaaaa"' in text
        assert '"commit": "bbbbbbbb"' in text
        assert "<<<<<<<" not in text
        assert "=======" not in text
        assert ">>>>>>>" not in text

    def test_identical_line_appended_on_both_sides_deduplicates(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_gitattributes_merge.py::TestRapidDebtUnionMerge.test_identica\
        # l_line_appended_on_both_sides_deduplicates
        """T-1873 item 4: whether union merge can duplicate a record when
        both sides append the byte-identical line. Measured: git's native
        `merge=union` DEDUPLICATES an exact duplicate line rather than
        keeping two copies -- the surviving file has the line exactly
        once, not twice. This is harmless for rapid-debt.jsonl's shape
        (each real record embeds a unique commit sha, so a genuine
        duplicate can only arise from a retry re-emitting a byte-
        identical record for the same commit, which collapsing to one
        entry is the correct outcome, not data loss) -- no dedup-on-read
        pass is warranted in the reader."""
        same_line = (
            '{"commit": "cccccccc", "skipped": "land-evidence-scope-unbound", '
            '"ticket": "T-3333"}\n'
        )
        _run(["git", "checkout", "-q", "-b", "worktree-c"], repo)
        with (repo / "rapid-debt.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(same_line)
        _commit_all(repo, "worktree-c: rapid debt record")

        _run(["git", "checkout", "-q", "main"], repo)
        _run(["git", "checkout", "-q", "-b", "worktree-d"], repo)
        with (repo / "rapid-debt.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(same_line)
        _commit_all(repo, "worktree-d: rapid debt record")

        _run(["git", "checkout", "-q", "worktree-c"], repo)
        merge = subprocess.run(
            ["git", "merge", "-q", "--no-edit", "worktree-d"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, (
            f"expected merge=union to auto-resolve cleanly, got a real "
            f"conflict instead: stdout={merge.stdout!r} stderr={merge.stderr!r}"
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

        text = (repo / "rapid-debt.jsonl").read_text()
        assert text.count('"commit": "cccccccc"') == 1
