"""Unit tests for `scripts/branch_stranded_work_analysis.py` (T-2646).

`classify_branch`'s decision logic is pure once `_run` (the one
subprocess seam) is monkeypatched -- mirrors `test_coordinator_scripts.
py`'s own "no real subprocess, small fixture data" shape for the same
reason its module docstring gives.
"""

from __future__ import annotations

import pytest

from tests.unit.conftest import _load_script as _load

branch_analysis = _load("branch_stranded_work_analysis")


def _stub_run(
    monkeypatch: pytest.MonkeyPatch, table: dict[tuple[str, ...], tuple[int, str]]
) -> None:
    """Replace `branch_analysis._run` with a lookup over `table`, keyed by
    the exact argv tuple -- a missing key is a test bug (raises), never a
    silent `(1, "")` that could mask a wrong-argv assertion failure."""

    def fake_run(argv: tuple[str, ...]) -> tuple[int, str]:
        if argv not in table:
            raise AssertionError(f"unexpected argv in test: {argv}")
        return table[argv]

    monkeypatch.setattr(branch_analysis, "_run", fake_run)


class TestIsMerged:
    """`branch_analysis.is_merged`."""

    def test_true_when_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Exit code 0 from `merge-base --is-ancestor` means merged."""
        _stub_run(monkeypatch, {("git", "merge-base", "--is-ancestor", "b", "main"): (0, "")})
        assert branch_analysis.is_merged("b", "main") is True

    def test_false_when_not_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A nonzero exit code means not merged."""
        _stub_run(monkeypatch, {("git", "merge-base", "--is-ancestor", "b", "main"): (1, "")})
        assert branch_analysis.is_merged("b", "main") is False


class TestTicketIdsOnBranch:
    """`branch_analysis.ticket_ids_on_branch`."""

    def test_ledger_path_yields_its_own_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A changed `tickets/T-####/ticket.md` path signals that id
        directly, no blob read needed."""
        _stub_run(monkeypatch, {})
        ids = branch_analysis.ticket_ids_on_branch("b", ["tickets/T-0042/ticket.md"])
        assert ids == {"T-0042"}

    def test_directive_comment_in_non_ticket_file_is_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `frob:ticket T-####` mention in a changed non-ticket file's
        blob text is picked up via the fallback grep."""
        _stub_run(
            monkeypatch,
            {("git", "show", "b:src/foo.py"): (0, "# frob:ticket T-0099\ndef f(): pass\n")},
        )
        ids = branch_analysis.ticket_ids_on_branch("b", ["src/foo.py"])
        assert ids == {"T-0099"}

    def test_tickets_path_prefix_never_blob_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A `tickets/**` path that is NOT a recognized ledger file (e.g. an
        attachment) is skipped, never blob-read for a directive mention --
        a ticket's own files legitimately cite other ids, which is not a
        real cross-branch signal."""
        _stub_run(monkeypatch, {})
        ids = branch_analysis.ticket_ids_on_branch(
            "b", ["tickets/T-0042/attachments/notes.md"]
        )
        assert ids == set()


class TestClassifyBranch:
    """`branch_analysis.classify_branch` -- the full three-way decision."""

    def test_merged_when_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An ancestor branch classifies (a) merged without touching the
        diff/ticket-signal machinery at all."""
        _stub_run(monkeypatch, {("git", "merge-base", "--is-ancestor", "b", "main"): (0, "")})
        result = branch_analysis.classify_branch("b", "main")
        assert result.class_ == "merged"

    def test_ticket_done_when_all_ids_terminal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Not merged, but the branch's own referenced ticket is `done` on
        main -> class (b)."""
        _stub_run(
            monkeypatch,
            {
                ("git", "merge-base", "--is-ancestor", "b", "main"): (1, ""),
                ("git", "diff", "--quiet", "main...b"): (1, ""),
                ("git", "merge-base", "main", "b"): (0, "base-sha\n"),
                ("git", "diff", "--name-only", "base-sha..b"): (
                    0,
                    "tickets/T-0100/ticket.md\n",
                ),
                ("git", "show", "main:tickets/T-0100/ticket.md"): (0, "state: done\n"),
                ("git", "show", "main:tickets/archive/T-0100/ticket.md"): (1, ""),
            },
        )
        result = branch_analysis.classify_branch("b", "main")
        assert result.class_ == "ticket-done"
        assert result.ticket_ids == ["T-0100"]

    def test_stranded_when_ticket_not_terminal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The referenced ticket is still `queued` on main -> class (c),
        never silently promoted to (b)."""
        _stub_run(
            monkeypatch,
            {
                ("git", "merge-base", "--is-ancestor", "b", "main"): (1, ""),
                ("git", "diff", "--quiet", "main...b"): (1, ""),
                ("git", "merge-base", "main", "b"): (0, "base-sha\n"),
                ("git", "diff", "--name-only", "base-sha..b"): (
                    0,
                    "tickets/T-0101/ticket.md\n",
                ),
                ("git", "show", "main:tickets/T-0101/ticket.md"): (0, "state: queued\n"),
                ("git", "show", "main:tickets/archive/T-0101/ticket.md"): (1, ""),
            },
        )
        result = branch_analysis.classify_branch("b", "main")
        assert result.class_ == "stranded"

    def test_stranded_when_no_ticket_signal_but_real_diff(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A real, non-empty diff with no ticket trace at all -> class (c)
        -- the highest-confidence stranded shape."""
        _stub_run(
            monkeypatch,
            {
                ("git", "merge-base", "--is-ancestor", "b", "main"): (1, ""),
                ("git", "diff", "--quiet", "main...b"): (1, ""),
                ("git", "merge-base", "main", "b"): (0, "base-sha\n"),
                ("git", "diff", "--name-only", "base-sha..b"): (0, "src/foo.py\n"),
                ("git", "show", "b:src/foo.py"): (0, "no directive here\n"),
            },
        )
        result = branch_analysis.classify_branch("b", "main")
        assert result.class_ == "stranded"
        assert result.ticket_ids == []

    def test_merged_when_tree_identical_despite_diverged_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Not an ancestor by history, but the tree diff is empty -- a
        rebase-in-place -- still classifies (a) merged."""
        _stub_run(
            monkeypatch,
            {
                ("git", "merge-base", "--is-ancestor", "b", "main"): (1, ""),
                ("git", "diff", "--quiet", "main...b"): (0, ""),
            },
        )
        result = branch_analysis.classify_branch("b", "main")
        assert result.class_ == "merged"

    def test_merged_when_own_diff_against_merge_base_is_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Diverged history, non-identical full tree diff against main
        (so `tree_identical` says no), but an EMPTY diff against the
        branch's own merge-base -- nothing this branch itself added, so
        still merged rather than a hollow class-(c) entry."""
        _stub_run(
            monkeypatch,
            {
                ("git", "merge-base", "--is-ancestor", "b", "main"): (1, ""),
                ("git", "diff", "--quiet", "main...b"): (1, ""),
                ("git", "merge-base", "main", "b"): (0, "base-sha\n"),
                ("git", "diff", "--name-only", "base-sha..b"): (0, ""),
            },
        )
        result = branch_analysis.classify_branch("b", "main")
        assert result.class_ == "merged"


class TestLocalBranches:
    """`branch_analysis.local_branches`."""

    def test_excludes_ref_and_blanks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`main` itself and blank lines are filtered out of the listing."""
        _stub_run(
            monkeypatch,
            {("git", "branch", "--format=%(refname:short)"): (0, "main\nfeat-a\n\nfeat-b\n")},
        )
        assert branch_analysis.local_branches("main") == ["feat-a", "feat-b"]

    def test_empty_on_git_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A nonzero exit code degrades to an empty list, never a raise --
        matches `frob.tickets._unlanded._local_branch_names`'s own
        best-effort posture."""
        _stub_run(monkeypatch, {("git", "branch", "--format=%(refname:short)"): (1, "")})
        assert branch_analysis.local_branches("main") == []


class TestTreeIdentical:
    """`branch_analysis.tree_identical`."""

    def test_true_on_empty_diff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`git diff --quiet` exit 0 means no content difference."""
        _stub_run(monkeypatch, {("git", "diff", "--quiet", "main...b"): (0, "")})
        assert branch_analysis.tree_identical("b", "main") is True

    def test_false_on_real_diff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`git diff --quiet` exit 1 means a real difference."""
        _stub_run(monkeypatch, {("git", "diff", "--quiet", "main...b"): (1, "")})
        assert branch_analysis.tree_identical("b", "main") is False


class TestOwnChangedFiles:
    """`branch_analysis.own_changed_files`."""

    def test_returns_diff_against_merge_base(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Paths come from `git diff --name-only <merge-base>..<branch>`,
        not a diff against `ref` directly."""
        _stub_run(
            monkeypatch,
            {
                ("git", "merge-base", "main", "b"): (0, "base-sha\n"),
                ("git", "diff", "--name-only", "base-sha..b"): (0, "a.py\nb.py\n"),
            },
        )
        assert branch_analysis.own_changed_files("b", "main") == ["a.py", "b.py"]

    def test_empty_when_merge_base_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A merge-base failure degrades to an empty list, never a raise."""
        _stub_run(monkeypatch, {("git", "merge-base", "main", "b"): (1, "")})
        assert branch_analysis.own_changed_files("b", "main") == []


class TestBlobText:
    """`branch_analysis.blob_text`."""

    def test_returns_stdout_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A successful `git show <ref>:<path>` returns its stdout verbatim."""
        _stub_run(monkeypatch, {("git", "show", "main:a.py"): (0, "content\n")})
        assert branch_analysis.blob_text("main", "a.py") == "content\n"

    def test_none_when_path_does_not_exist(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A nonzero exit (path/ref does not resolve) returns `None`, not
        an empty string -- callers rely on this to distinguish "no blob"
        from "empty blob"."""
        _stub_run(monkeypatch, {("git", "show", "main:missing.py"): (1, "")})
        assert branch_analysis.blob_text("main", "missing.py") is None


class TestTicketStateOnMain:
    """`branch_analysis.ticket_state_on_main`."""

    def test_reads_active_ledger_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The active `tickets/T-####/ticket.md` path is tried first."""
        _stub_run(
            monkeypatch,
            {("git", "show", "main:tickets/T-0042/ticket.md"): (0, "state: queued\n")},
        )
        assert branch_analysis.ticket_state_on_main("T-0042", "main") == "queued"

    def test_falls_back_to_archive_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A ticket absent from the active ledger but present in the v2
        archive still resolves its state."""
        _stub_run(
            monkeypatch,
            {
                ("git", "show", "main:tickets/T-0042/ticket.md"): (1, ""),
                ("git", "show", "main:tickets/archive/T-0042/ticket.md"): (
                    0,
                    "state: done\n",
                ),
            },
        )
        assert branch_analysis.ticket_state_on_main("T-0042", "main") == "done"

    def test_none_when_neither_path_resolves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Neither the active nor the archive path exists -> `None`, not a
        raise (an id `main` has genuinely never heard of, e.g. a template
        example like `T-9001`)."""
        _stub_run(
            monkeypatch,
            {
                ("git", "show", "main:tickets/T-0042/ticket.md"): (1, ""),
                ("git", "show", "main:tickets/archive/T-0042/ticket.md"): (1, ""),
            },
        )
        assert branch_analysis.ticket_state_on_main("T-0042", "main") is None


class TestMain:
    """`branch_analysis.main` -- the CLI entry point, end to end against a
    stubbed `_run`."""

    def test_reports_zero_branches_cleanly(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No local branches (besides `main`) -> a clean zero-count report,
        exit 0, no exception."""
        monkeypatch.setattr(
            "sys.argv", ["branch_stranded_work_analysis.py", "--ref", "main"]
        )
        _stub_run(monkeypatch, {("git", "branch", "--format=%(refname:short)"): (0, "main\n")})
        assert branch_analysis.main() == 0
        out = capsys.readouterr().out
        assert "scanned 0 branch(es) against main" in out
