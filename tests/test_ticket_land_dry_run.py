"""T-4179 (consumer report F-380): `frob ticket land --dry-run` left three
modified files behind in the caller's worktree -- `_absorb_pre_land_fixes`
(T-1175's pre-land fmt/ruff-format/Tier-A absorption trio,
`frob.app.ticket_runner._land_cmd`) ran in write mode unconditionally,
`--dry-run` or not. These tests pin the fix directly at that function: a
dry run must leave the worktree BYTE-IDENTICAL (proven via the tree's own
git hash, not just a spot-checked file), while a real (non-dry-run) run
still applies the fixes exactly as before. The second class covers this
ticket's defect (3): a refusal caused by the tool's OWN uncommitted edit
now names the tool, not just the operator.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner._land_cmd import _absorb_pre_land_fixes
from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
from frob.tickets._land import (
    _attribute_own_fmt_rewrap,
    _check_uncommitted_waive_deletions,
    _uncommitted_change_is_own_fmt_rewrap,
)


# frob:waive DUP001 reason="the run/git-init/commit-all trio is an established \
# real-git-fixture idiom this test module family repeats (tests/test_ticket_land.py, \
# tests/test_ticket_work_and_land_finish.py, tests/test_tickets_collision.py, ... all \
# carry byte-identical copies already, none of them waived) -- extracting a shared \
# conftest helper is a real, independent cleanup outside T-4179's own scope"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="see _run's identical DUP001 waiver immediately above -- \
# same established fixture idiom, same real cleanup-later disposition"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:waive DUP001 reason="see _run's identical DUP001 waiver above -- same \
# established fixture idiom, same real cleanup-later disposition"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    status = _run(["git", "diff", "--cached", "--name-only"], root).stdout
    if not status.strip():
        return
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal git checkout with one committed file -- matching
    `TestAbsorbPreLandFixes`'s own `repo` fixture shape
    (tests/test_ticket_work_and_land_finish.py). Each test below then adds
    its own non-canonical `frob:` directive as an UNCOMMITTED (staged)
    change, so `_land_touched_paths`'s `main`-relative diff sees it as
    this "ticket"'s own touched file -- a file already committed on `main`
    itself has no diff to be touched by."""
    root = tmp_path / "repo"
    _git_init(root)
    (root / "src").mkdir()
    (root / "src" / "feature.py").write_text("# landed feature\n")
    (root / ".gitignore").write_text(".claude/\n.frob/\n")
    _commit_all(root, "init")
    return root


def _write_noncanonical_directive(repo: Path) -> Path:
    """Add `src/noncanon.py`, carrying one over-long `frob:waive`
    directive comment (forces `frob fmt`'s wrap), as an uncommitted staged
    change in `repo` -- the shape `_land_touched_paths`'s diff-against-
    `main` picks up as this "ticket"'s own touched file."""
    target = repo / "src" / "noncanon.py"
    target.write_text(
        '# frob:waive R reason="this reason is intentionally long so it '
        'overflows the line-length limit and must be wrapped"\n'
    )
    _run(["git", "add", "-A"], repo)
    return target


class TestAbsorbPreLandFixesDryRunIsReadOnly:
    """T-4179 defect (1): a dry run must not write to the worktree."""

    def test_dry_run_leaves_the_worktree_tree_hash_unchanged(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.tes\
        # t_dry_run_leaves_the_worktree_tree_hash_unchanged
        _write_noncanonical_directive(repo)
        _run(["git", "add", "-A"], repo)
        before = _run(["git", "write-tree"], repo).stdout.strip()

        _absorb_pre_land_fixes(repo, "T-4179", dry_run=True)

        _run(["git", "add", "-A"], repo)
        after = _run(["git", "write-tree"], repo).stdout.strip()
        assert after == before

    def test_dry_run_leaves_the_noncanonical_file_byte_identical(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.tes\
        # t_dry_run_leaves_the_noncanonical_file_byte_identical
        target = _write_noncanonical_directive(repo)
        original = target.read_text()

        _absorb_pre_land_fixes(repo, "T-4179", dry_run=True)

        assert target.read_text() == original

    def test_running_dry_run_twice_is_still_a_noop_both_times(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.tes\
        # t_running_dry_run_twice_is_still_a_noop_both_times
        # T-4179 defect (3)'s regression fixture: since a dry run no
        # longer writes anything, a SECOND consecutive dry run cannot
        # trip over the first one's own edit -- there is no edit to trip
        # over. Two dry runs in a row report the identical (empty) diff.
        _write_noncanonical_directive(repo)

        def tree_hash() -> str:
            _run(["git", "add", "-A"], repo)
            return _run(["git", "write-tree"], repo).stdout.strip()

        before = tree_hash()
        _absorb_pre_land_fixes(repo, "T-4179", dry_run=True)
        mid = tree_hash()
        _absorb_pre_land_fixes(repo, "T-4179", dry_run=True)
        after = tree_hash()
        assert before == mid == after

    def test_real_run_still_rewrites_the_noncanonical_file(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.tes\
        # t_real_run_still_rewrites_the_noncanonical_file
        # Control: a REAL (non-dry-run) call keeps applying the fix exactly
        # as before T-4179 -- only `--dry-run` changed behavior.
        target = _write_noncanonical_directive(repo)
        original = target.read_text()

        _absorb_pre_land_fixes(repo, "T-4179", dry_run=False)

        assert target.read_text() != original


def _new_out_of_scope_ticket(repo: Path) -> str:
    """A ticket whose declared scope covers NEITHER `src/other.py` (the
    file the attribution tests rewrap/delete a waiver from) nor its Done
    report -- the exact "genuinely out of scope" shape
    `_check_uncommitted_waive_deletions` is built to refuse."""
    created = new_ticket(
        repo,
        TicketSpec(
            title="Unrelated ticket",
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            scope=("src/feature.py",),
        ),
    )
    assert created.is_ok, created.err
    return created.danger_ok.id


def _commit_noncanonical_waiver_on_a_ticket_branch(repo: Path) -> None:
    """Checkout a fresh branch off `repo`'s current `main` tip and commit
    `src/other.py` there, carrying one over-long `frob:waive` directive.
    `_land_touched_paths`'s diff is against the LIVE `main` ref, so this
    branch's own commit (not merely an uncommitted change) is what makes
    the file "touched" -- and, unlike an uncommitted-only file, `git show
    HEAD:src/other.py` now resolves, which `_uncommitted_change_is_own_
    fmt_rewrap` needs to diff a later uncommitted rewrap against."""
    _run(["git", "checkout", "-q", "-b", "ticket-branch"], repo)
    (repo / "src" / "other.py").write_text(
        '# frob:waive PERF001 reason="' + ("x" * 80) + '"\ndef g():\n    pass\n'
    )
    _commit_all(repo, "add other.py with an over-long waiver")


class TestOutOfScopeRefusalAttributesOwnFmtRewrap:
    """T-4179 defect (3): a `frob:waive`-deletion refusal caused by the
    TOOL's own uncommitted `frob fmt` rewrap must say so -- not read as
    though the operator made the edit."""

    def test_own_fmt_rewrap_is_recognized(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewra\
        # p.test_own_fmt_rewrap_is_recognized
        _commit_noncanonical_waiver_on_a_ticket_branch(repo)
        tid = _new_out_of_scope_ticket(repo)

        # frob fmt's own rewrap of the committed content above, NOT a
        # hand edit.
        _absorb_pre_land_fixes(repo, tid, dry_run=False)

        assert _uncommitted_change_is_own_fmt_rewrap(repo, "src/other.py")

    def test_a_genuine_hand_deletion_is_not_misattributed(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewra\
        # p.test_a_genuine_hand_deletion_is_not_misattributed
        _run(["git", "checkout", "-q", "-b", "ticket-branch-2"], repo)
        target = repo / "src" / "other.py"
        target.write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live waiver")

        # A real, by-hand deletion -- not anything `frob fmt` would ever
        # produce from the committed content above.
        target.write_text("def g():\n    pass\n")

        assert not _uncommitted_change_is_own_fmt_rewrap(repo, "src/other.py")

    def test_a_rewrap_that_stays_parseable_does_not_refuse_at_all(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewra\
        # p.test_a_rewrap_that_stays_parseable_does_not_refuse_at_all
        # T-4179's OWN fix (defect 2: never split a directive token) means
        # a legitimate `frob fmt` re-wrap can no longer corrupt a waiver
        # past `_uncommitted_out_of_scope_waive_deletions`'s own parser --
        # the exact end-to-end refusal F-380 reported cannot recur once
        # defect (2) holds. This attribution helper (defect 3) is
        # defense-in-depth for whatever OTHER tool-authored edit could
        # still trip this refusal, unit-tested directly above/below rather
        # than re-summoned end-to-end here (it no longer reproduces).
        _commit_noncanonical_waiver_on_a_ticket_branch(repo)
        tid = _new_out_of_scope_ticket(repo)
        _absorb_pre_land_fixes(repo, tid, dry_run=False)
        # The rewrap DID happen (round-trip preserving) ...
        assert _uncommitted_change_is_own_fmt_rewrap(repo, "src/other.py")

        from frob.tickets._store import load_all

        loaded = load_all(repo)
        assert loaded.is_ok, loaded.err
        ticket = loaded.danger_ok[tid]

        # ... but the waiver is still parseable, so nothing refuses.
        result = _check_uncommitted_waive_deletions(repo, ticket, tid)
        assert result.is_ok

    def test_attribute_helper_suffixes_an_own_rewrap_finding(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewra\
        # p.test_attribute_helper_suffixes_an_own_rewrap_finding
        _commit_noncanonical_waiver_on_a_ticket_branch(repo)
        tid = _new_out_of_scope_ticket(repo)
        _absorb_pre_land_fixes(repo, tid, dry_run=False)
        assert _uncommitted_change_is_own_fmt_rewrap(repo, "src/other.py")

        rendered = _attribute_own_fmt_rewrap(repo, [("src/other.py", "PERF001")])

        assert rendered == [
            "src/other.py:PERF001 [frob fmt's own rewrap, not an operator edit]"
        ]

    def test_attribute_helper_suffixes_only_own_rewrap_findings(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewra\
        # p.test_attribute_helper_suffixes_only_own_rewrap_findings
        (repo / "src" / "hand_edited.py").write_text(
            '# frob:waive PERF002 reason="genuinely needed"\ndef h():\n    pass\n'
        )
        _commit_all(repo, "add hand_edited.py")
        (repo / "src" / "hand_edited.py").write_text("def h():\n    pass\n")

        rendered = _attribute_own_fmt_rewrap(repo, [("src/hand_edited.py", "PERF002")])

        assert rendered == ["src/hand_edited.py:PERF002"]
        assert "frob fmt" not in rendered[0]
