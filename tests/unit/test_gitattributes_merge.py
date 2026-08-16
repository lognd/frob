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


@pytest.fixture
def autocrlf_repo(tmp_path: Path) -> Path:
    """A checkout carrying THIS repo's real `.gitattributes` (so the fixture
    exercises the actual rule under test, not a hand-rewritten copy that
    could silently drift from it) with `core.autocrlf=true` set LOCALLY on
    this throwaway repo only -- never touching the real clone's config,
    per T-2239's explicit "not a per-clone autocrlf=false fix" constraint.
    autocrlf=true reproduces the exact CRLF-conversion-on-checkout behavior
    T-1433/T-2239 exist to suppress."""
    main_repo = tmp_path / "autocrlf-main"
    _git_init(main_repo)
    _run(["git", "config", "core.autocrlf", "true"], main_repo)
    real_gitattributes = Path(__file__).parents[2] / ".gitattributes"
    (main_repo / ".gitattributes").write_text(real_gitattributes.read_text())
    _commit_all(main_repo, "init")
    return main_repo


class TestAttachmentCrlfSuppression:
    """T-2239: T-1433's `.gitattributes` `-text` rule only matched the OLD
    v1 flat attachment layout (`tickets/attachments/**`), never the v2
    per-ticket nested layout (`tickets/<id>/attachments/**`) ledger v2
    actually uses -- so v2 attachments were silently CRLF-converted on
    checkout, desyncing their on-disk sha256 from the sha256 recorded at
    attach time (LF content). Verified by REPRODUCTION: write an LF file,
    commit it, force a real checkout-time filter pass (delete + `git
    checkout --`, the same code path a fresh clone/checkout exercises,
    not merely a read of the committed blob), and assert the byte content
    -- and therefore its sha256 -- survives unconverted. A test that never
    re-checks out the file would prove nothing, since `-text` only takes
    effect on checkout, not on `git show`/`git add`.
    """

    @staticmethod
    def _write_lf_file(repo: Path, rel_path: str, body: str) -> str:
        """Write `body` as literal LF-terminated bytes at `rel_path` inside
        `repo`, commit it, then force a checkout-time filter re-application
        (delete the working-tree copy and `git checkout --` it back) --
        the same path a fresh clone/checkout takes -- and return the
        resulting on-disk sha256 hex digest."""
        full = repo / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(body.encode("utf-8"))
        _commit_all(repo, f"add {rel_path}")

        full.unlink()
        _run(["git", "checkout", "--", rel_path], repo)

        import hashlib

        return hashlib.sha256(full.read_bytes()).hexdigest()

    def test_v2_nested_attachment_survives_checkout_unconverted(
        self, autocrlf_repo: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression.test_v2\
        # _nested_attachment_survives_checkout_unconverted
        body = "line one\nline two\nline three\n"
        import hashlib

        expected_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()

        on_disk_sha = self._write_lf_file(
            autocrlf_repo,
            "tickets/T-9001/attachments/01-example.md",
            body,
        )

        assert on_disk_sha == expected_sha, (
            "v2-mode nested attachment path was CRLF-converted on checkout "
            "despite the .gitattributes -text rule -- the exact T-2239 "
            "regression this test guards against"
        )

    def test_v1_flat_attachment_still_covered(self, autocrlf_repo: Path) -> None:
        # frob:tests \
        # tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression.test_v1\
        # _flat_attachment_still_covered
        """MUST-STILL-PASS control (T-2239): the OLD v1 flat layout the
        original T-1433 rule targeted must remain covered after widening
        the glob to also match v2 -- a fix that replaced rather than
        extended coverage would silently regress it."""
        body = "flat layout line one\nflat layout line two\n"
        import hashlib

        expected_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()

        on_disk_sha = self._write_lf_file(
            autocrlf_repo,
            "tickets/attachments/T-9002/01-example.md",
            body,
        )

        assert on_disk_sha == expected_sha, (
            "v1-mode flat attachment path regressed -- no longer covered "
            "by the .gitattributes -text rule"
        )

    def test_unrelated_text_file_still_gets_autocrlf_conversion(
        self, autocrlf_repo: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression.test_un\
        # related_text_file_still_gets_autocrlf_conversion
        """Negative control: a plain file OUTSIDE any attachments path is
        NOT covered by the widened rule -- proves the glob is scoped to
        attachments, not accidentally suppressing autocrlf repo-wide."""
        full = autocrlf_repo / "some_unrelated_file.md"
        full.write_bytes(b"line one\nline two\n")
        _commit_all(autocrlf_repo, "add unrelated file")
        full.unlink()
        _run(["git", "checkout", "--", "some_unrelated_file.md"], autocrlf_repo)

        assert b"\r\n" in full.read_bytes(), (
            "unrelated file unexpectedly escaped autocrlf conversion -- "
            "the attachment glob is too broad"
        )
