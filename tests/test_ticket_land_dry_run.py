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

T-4475 regression: T-4179's own fix (never split an unbreakable directive
token) left the resulting over-limit physical line E501-dirty, so a REAL
(non-dry-run) land's own pre-land `ruff check` refused on a NEW violation
the absorption step it ran right before had JUST introduced -- and left
that rewrite uncommitted in the worktree afterward (T-4473's incident).
The third class here covers the worktree-left-dirty-after-refusal half of
that fix (the noqa-suppression half lives in
tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _land_cmd
from frob.app.ticket_runner._land_cmd import (
    _absorb_pre_land_fixes,
    _land_core_prepare,
    _restore_absorbed_paths,
)
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
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.test_dry_run_leaves_the_worktree_tree_hash_unchanged  # noqa: E501
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
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.test_dry_run_leaves_the_noncanonical_file_byte_identical  # noqa: E501
        target = _write_noncanonical_directive(repo)
        original = target.read_text()

        _absorb_pre_land_fixes(repo, "T-4179", dry_run=True)

        assert target.read_text() == original

    def test_running_dry_run_twice_is_still_a_noop_both_times(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.test_running_dry_run_twice_is_still_a_noop_both_times  # noqa: E501
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
        # tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly.test_real_run_still_rewrites_the_noncanonical_file  # noqa: E501
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
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap.test_own_fmt_rewrap_is_recognized  # noqa: E501
        _commit_noncanonical_waiver_on_a_ticket_branch(repo)
        tid = _new_out_of_scope_ticket(repo)

        # frob fmt's own rewrap of the committed content above, NOT a
        # hand edit.
        _absorb_pre_land_fixes(repo, tid, dry_run=False)

        assert _uncommitted_change_is_own_fmt_rewrap(repo, "src/other.py")

    def test_a_genuine_hand_deletion_is_not_misattributed(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap.test_a_genuine_hand_deletion_is_not_misattributed  # noqa: E501
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
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap.test_a_rewrap_that_stays_parseable_does_not_refuse_at_all  # noqa: E501
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
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap.test_attribute_helper_suffixes_an_own_rewrap_finding  # noqa: E501
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
        # tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap.test_attribute_helper_suffixes_only_own_rewrap_findings  # noqa: E501
        (repo / "src" / "hand_edited.py").write_text(
            '# frob:waive PERF002 reason="genuinely needed"\ndef h():\n    pass\n'
        )
        _commit_all(repo, "add hand_edited.py")
        (repo / "src" / "hand_edited.py").write_text("def h():\n    pass\n")

        rendered = _attribute_own_fmt_rewrap(repo, [("src/hand_edited.py", "PERF002")])

        assert rendered == ["src/hand_edited.py:PERF002"]
        assert "frob fmt" not in rendered[0]


# frob:ticket T-4475
class TestRestoreAbsorbedPathsOnRefusal:
    """T-4475: a pre-land refusal (`sys.exit(1)`, from any of the checks
    `_land_core_prepare` runs right after `_absorb_pre_land_fixes`) must
    not leave the absorption step's own rewrite uncommitted in the
    worktree (T-4473's incident: a canonicalized `frob:tests` directive
    left dirty after the land it was absorbed FOR was refused on the NEW
    E501 finding that same canonicalization introduced)."""

    def test_restore_absorbed_paths_reverts_a_real_rewrite(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestRestoreAbsorbedPathsOnRefusal.test_restore_absorbed_paths_reverts_a_real_rewrite  # noqa: E501
        # Unit-level: `_restore_absorbed_paths` on its own, given the exact
        # shape `_absorb_pre_land_fixes` produces -- a committed file,
        # rewritten uncommitted.
        target = repo / "src" / "feature.py"
        original = target.read_text()
        target.write_text(original + "# an absorbed rewrite\n")
        assert target.read_text() != original

        _restore_absorbed_paths(repo, "T-4475", ["src/feature.py"])

        assert target.read_text() == original
        status = _run(["git", "status", "--porcelain"], repo).stdout
        assert "src/feature.py" not in status

    def test_restore_absorbed_paths_is_a_noop_on_an_empty_list(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestRestoreAbsorbedPathsOnRefusal.test_restore_absorbed_paths_is_a_noop_on_an_empty_list  # noqa: E501
        target = repo / "src" / "feature.py"
        original = target.read_text()

        # No paths given -- nothing to restore, nothing raised.
        _restore_absorbed_paths(repo, "T-4475", [])

        assert target.read_text() == original

    def test_pre_land_refusal_restores_the_absorbed_rewrite(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestRestoreAbsorbedPathsOnRefusal.test_pre_land_refusal_restores_the_absorbed_rewrite  # noqa: E501
        # Integration-shaped: `_land_core_prepare` itself, with the FIRST
        # pre-land check it runs after absorption (`_assert_touched_files_
        # type_check_pre_land`) monkeypatched to refuse unconditionally --
        # standing in for T-4473's real refusal
        # (`_assert_touched_files_lint_clean_pre_land`, on a NEW E501
        # finding) without needing a real `ty`/`ruff` violation fixture.
        # `_absorb_pre_land_fixes` still runs for REAL here (`dry_run=
        # False`, matching a real land) and genuinely rewrites
        # `src/noncanon.py` before the monkeypatched check exits.
        target = _write_noncanonical_directive(repo)
        original = target.read_text()

        def _refuse(*_args: object, **_kwargs: object) -> None:
            sys.exit(1)

        monkeypatch.setattr(
            _land_cmd, "_assert_touched_files_type_check_pre_land", _refuse
        )

        cfg = AppConfig(ticket_command="land", ticket_id="T-4475", ticket_dry_run=False)

        with pytest.raises(SystemExit):
            _land_core_prepare(repo, cfg, repo)

        # The refusal propagated (proven by pytest.raises above) AND the
        # worktree is exactly as it was before this call -- the absorbed
        # rewrite was restored, not left dirty.
        assert target.read_text() == original
        status = _run(["git", "status", "--porcelain"], repo).stdout
        # The ORIGINAL staged addition of src/noncanon.py is still there
        # (untouched by fmt) -- only the fmt rewrite itself was undone.
        assert "src/noncanon.py" in status

    def test_pre_land_success_leaves_the_absorbed_rewrite_in_place(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_dry_run.py::TestRestoreAbsorbedPathsOnRefusal.test_pre_land_success_leaves_the_absorbed_rewrite_in_place  # noqa: E501
        # Control: when every pre-land check the try/except wraps
        # succeeds, the absorbed rewrite is left in place exactly as
        # before T-4475 -- restoration is refusal-only.
        target = _write_noncanonical_directive(repo)
        original = target.read_text()

        def _pass(*_args: object, **_kwargs: object) -> None:
            return None

        for name in (
            "_assert_touched_files_type_check_pre_land",
            "_assert_touched_files_lint_clean_pre_land",
            "_assert_new_public_symbols_have_doc_and_test_edge_pre_land",
            "_assert_diff_does_not_worsen_long_functions_pre_land",
            "_assert_diff_does_not_add_new_file_local_errors_pre_land",
        ):
            monkeypatch.setattr(_land_cmd, name, _pass)

        # `_land_core_prepare` also resolves the land root and reconciles
        # stale markers after the try/except block -- stub those too so
        # this test only exercises the absorb-then-checks seam T-4475
        # touches, not the rest of a real land's own preconditions.
        monkeypatch.setattr(_land_cmd, "_resolve_land_root", lambda root, *a, **k: root)
        monkeypatch.setattr(_land_cmd, "_report_stale_post_land_verify_markers", _pass)
        monkeypatch.setattr(
            _land_cmd, "_report_stale_land_finish_pending_markers", _pass
        )
        monkeypatch.setattr(_land_cmd, "_warn_land_override_flags", _pass)

        cfg = AppConfig(ticket_command="land", ticket_id="T-4475", ticket_dry_run=False)

        try:
            _land_core_prepare(repo, cfg, repo)
        except Exception:
            # This stub does not attempt to satisfy every precondition
            # `_land_core_prepare` checks past the try/except block (rapid
            # profile resolution, backpressure, ...) -- only that a
            # SUCCESSFUL pre-land-checks block does NOT restore.
            pass

        assert target.read_text() != original


# frob:ticket T-5813
class TestStaleNativesRebuildPrecedesTyCheck:
    """T-5813: `_land_core_prepare` must rebuild the worktree's
    stale natives (T-5518's `_rebuild_stale_worktree_natives`) BEFORE
    running the pre-land `ty` check (`_assert_touched_files_type_check_
    pre_land`) -- measured twice landing stale (T-3010, T-5366): `ty`
    reported a native extension missing a symbol the touched source
    genuinely defines, because the check ran against an extension built
    before that source existed."""

    # frob:tests \
    # tests/test_ticket_land_dry_run.py::TestStaleNativesRebuildPrecedesTyCheck.test_rebuild_call_precedes_the_ty_check_call  # noqa: E501
    def test_rebuild_call_precedes_the_ty_check_call(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control: patch both the rebuild helper (where
        `_land_core_prepare` actually imports it from,
        `frob.tickets._land_verify`) and the ty-check assertion, run
        `_land_core_prepare`, and assert the rebuild call landed in
        `call_order` strictly before the ty-check call."""
        import frob.tickets._land_verify as _land_verify

        call_order: list[str] = []

        def _fake_rebuild(worktree: Path) -> None:
            call_order.append("rebuild")

        def _fake_ty_check(*_args: object, **_kwargs: object) -> None:
            call_order.append("ty_check")

        monkeypatch.setattr(
            _land_verify, "_rebuild_stale_worktree_natives", _fake_rebuild
        )
        monkeypatch.setattr(
            _land_cmd, "_assert_touched_files_type_check_pre_land", _fake_ty_check
        )

        def _pass(*_args: object, **_kwargs: object) -> None:
            return None

        for name in (
            "_assert_touched_files_lint_clean_pre_land",
            "_assert_new_public_symbols_have_doc_and_test_edge_pre_land",
            "_assert_diff_does_not_worsen_long_functions_pre_land",
            "_assert_diff_does_not_add_new_file_local_errors_pre_land",
        ):
            monkeypatch.setattr(_land_cmd, name, _pass)
        monkeypatch.setattr(_land_cmd, "_resolve_land_root", lambda root, *a, **k: root)
        monkeypatch.setattr(_land_cmd, "_report_stale_post_land_verify_markers", _pass)
        monkeypatch.setattr(
            _land_cmd, "_report_stale_land_finish_pending_markers", _pass
        )
        monkeypatch.setattr(_land_cmd, "_warn_land_override_flags", _pass)

        cfg = AppConfig(ticket_command="land", ticket_id="T-5813", ticket_dry_run=False)

        try:
            _land_core_prepare(repo, cfg, repo)
        except Exception:
            # Same posture as the T-4475 success control above: this stub
            # does not satisfy every precondition past the try/except
            # block -- only the call-order assertion below matters.
            pass

        assert call_order == ["rebuild", "ty_check"]

    def test_rebuild_runs_even_when_natives_are_fresh(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-stay-quiet-shaped control: the rebuild call always
        precedes the ty check (it is unconditional, best-effort, and
        `_rebuild_stale_worktree_natives` itself already no-ops when
        nothing is stale) -- this asserts the ORDER invariant holds even
        when the ty check finds nothing to report, not only on the
        refusal path."""
        import frob.tickets._land_verify as _land_verify

        call_order: list[str] = []

        def _fake_rebuild(worktree: Path) -> None:
            call_order.append("rebuild")

        def _fake_ty_check_quiet(*_args: object, **_kwargs: object) -> None:
            call_order.append("ty_check")
            return None

        monkeypatch.setattr(
            _land_verify, "_rebuild_stale_worktree_natives", _fake_rebuild
        )
        monkeypatch.setattr(
            _land_cmd, "_assert_touched_files_type_check_pre_land", _fake_ty_check_quiet
        )

        def _pass(*_args: object, **_kwargs: object) -> None:
            return None

        for name in (
            "_assert_touched_files_lint_clean_pre_land",
            "_assert_new_public_symbols_have_doc_and_test_edge_pre_land",
            "_assert_diff_does_not_worsen_long_functions_pre_land",
            "_assert_diff_does_not_add_new_file_local_errors_pre_land",
        ):
            monkeypatch.setattr(_land_cmd, name, _pass)
        monkeypatch.setattr(_land_cmd, "_resolve_land_root", lambda root, *a, **k: root)
        monkeypatch.setattr(_land_cmd, "_report_stale_post_land_verify_markers", _pass)
        monkeypatch.setattr(
            _land_cmd, "_report_stale_land_finish_pending_markers", _pass
        )
        monkeypatch.setattr(_land_cmd, "_warn_land_override_flags", _pass)

        cfg = AppConfig(ticket_command="land", ticket_id="T-5813", ticket_dry_run=False)

        try:
            _land_core_prepare(repo, cfg, repo)
        except Exception:
            pass

        assert call_order == ["rebuild", "ty_check"]
