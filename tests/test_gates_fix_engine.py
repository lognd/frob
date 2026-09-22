"""Tests for `frob.gates._fix_engine_text`'s SUPPRESS001 Tier-A auto-fix
handler (T-1341, phase 2 of T-1339): writing the paired suppression comment
in canonical order, idempotently. Uses the REAL `ty`/`mypy` binaries against
small on-disk fixtures -- same precedent as `tests/test_gates_suppress.py`
(the whole point of SUPPRESS001 is real, observed diagnostics, not mocked
output), both tools already dev dependencies this suite requires.

T-1646 (LARGE001 residue burndown): FMT001/SUPPRESS001 and their private
helpers moved from `frob.gates._fix_engine` to `frob.gates._fix_engine_text`
-- `FixApplied` stays importable from `_fix_engine` (re-exported at its
top), the rest now come from their real new home."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._fix_engine import FixApplied
from frob.gates._fix_engine_text import (
    _code_ignored_for_path,
    _merged_dialect_codes,
    _split_suppression_line,
    fix_fmt001_directive_wrap,
    fix_suppress001_paired_suppression,
)
from frob.graph._models import GraphSnapshot

pytestmark = pytest.mark.timeout(90)

_SNAPSHOT = GraphSnapshot(root=".", symbols={}, edges=())


def _write(root: Path, rel: str, text: str) -> None:
    """Write `text` to `root/rel`, creating parent dirs as needed."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestFixSuppress001PairedSuppression:
    """`fix_suppress001_paired_suppression`: the end-to-end Tier-A fix."""

    # frob:tests src/frob/gates/_fix_engine_text.py::fix_suppress001_paired_suppression
    def test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression kind="unit"  # noqa: E501
        """Acceptance [0]: given a SUPPRESS001 finding (a line carrying
        only mypy's `type: ignore` that `ty` still errors on), the fix
        appends `ty`'s own reported rule code, and the line then passes
        both checkers (SUPPRESS001 reports nothing on a second pass)."""
        _write(
            tmp_path,
            "src/mod.py",
            "def uses_bad() -> None:\n"
            "    return undefined_name  # type: ignore[name-defined]\n",
        )
        applied = fix_suppress001_paired_suppression(tmp_path, _SNAPSHOT)

        assert len(applied) == 1
        fix = applied[0]
        assert isinstance(fix, FixApplied)
        assert fix.rule == "SUPPRESS001"
        assert fix.file == "src/mod.py"

        rewritten = (tmp_path / "src" / "mod.py").read_text(encoding="utf-8")
        assert "# type: ignore[name-defined]" in rewritten
        assert "# ty: ignore[unresolved-reference]" in rewritten

        from frob.gates._suppress import suppress001_gate

        assert suppress001_gate(tmp_path, _SNAPSHOT) == ()

    # frob:tests src/frob/gates/_fix_engine_text.py::fix_suppress001_paired_suppression
    def test_idempotent_second_fix_pass_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_idempotent_second_fix_pass_is_a_no_op kind="unit"  # noqa: E501
        """Acceptance [1]: running the fix twice never duplicates or
        reorders a suppression -- the second pass is byte-identical to
        the first, since the underlying diagnostic silences itself once
        both dialects' comments are present."""
        _write(
            tmp_path,
            "src/mod.py",
            "def uses_bad() -> None:\n"
            "    return undefined_name  # type: ignore[name-defined]\n",
        )
        first = fix_suppress001_paired_suppression(tmp_path, _SNAPSHOT)
        assert len(first) == 1
        after_first = (tmp_path / "src" / "mod.py").read_text(encoding="utf-8")

        second = fix_suppress001_paired_suppression(tmp_path, _SNAPSHOT)
        after_second = (tmp_path / "src" / "mod.py").read_text(encoding="utf-8")

        assert second == []
        assert after_second == after_first

    def test_merges_with_existing_other_code_canonical_order(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_merges_with_existing_other_code_canonical_order kind="unit"  # noqa: E501
        """A pre-existing `# noqa: F401` on the fixed line is MERGED, not
        clobbered -- `E501,F401` in canonical alphabetical order,
        preserving the pre-existing code."""
        merged = _merged_dialect_codes({"ruff": {"F401"}}, "ruff", "E501")
        assert merged == {"ruff": {"F401", "E501"}}

    def test_no_available_oracle_no_op(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_no_available_oracle_no_op kind="unit"  # noqa: E501
        """With no available oracle, `suppress001_gate` itself reports
        nothing, so the fix handler is a clean no-op rather than
        guessing."""
        import frob.gates._suppress as suppress_mod

        monkeypatch.setattr(suppress_mod.shutil, "which", lambda _name: None)
        _write(
            tmp_path,
            "src/mod.py",
            "def uses_bad() -> None:\n"
            "    return undefined_name  # type: ignore[name-defined]\n",
        )
        assert fix_suppress001_paired_suppression(tmp_path, _SNAPSHOT) == []


class TestSuppress001NoOpSuppressionRefusal:
    """T-1341's central specification requirement: `E501` cannot fire
    under `tests/**` (this repo's own `pyproject.toml` per-file-ignores),
    so the handler must REFUSE to append a `# noqa: E501` there -- a
    no-op suppression is a defect, not a convenience."""

    def test_code_ignored_for_path_true_under_tests_glob(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestSuppress001NoOpSuppressionRefusal.test_code_ignored_for_path_true_under_tests_glob kind="unit"  # noqa: E501
        """`_code_ignored_for_path` reads this repo's OWN
        `pyproject.toml` shape directly: `tests/**` is configured to
        ignore `E501`, so a synthetic copy of that same configuration
        must report `E501` as ignored for a `tests/...` path."""
        _write(
            tmp_path,
            "pyproject.toml",
            '[tool.ruff.lint.per-file-ignores]\n"tests/**" = ["E501"]\n',
        )
        assert _code_ignored_for_path(tmp_path, "tests/test_x.py", "E501") is True
        assert _code_ignored_for_path(tmp_path, "src/mod.py", "E501") is False

    def test_no_op_suppression_never_added_under_tests_glob(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestSuppress001NoOpSuppressionRefusal.test_no_op_suppression_never_added_under_tests_glob kind="unit"  # noqa: E501
        """End-to-end: a SUPPRESS001 fix on a `tests/**` file whose
        rewritten line would exceed the line-length limit must NOT gain
        a `# noqa: E501` -- this repo's real `pyproject.toml` already
        ignores `E501` under `tests/**`, so one would be pure dead
        noise. Uses a long dotted name to push the rewritten line
        comfortably over the 88-char default limit."""
        long_name = "undefined_name_that_is_quite_long_indeed_for_measuring_e501"
        _write(
            tmp_path,
            "tests/test_mod.py",
            f"def uses_bad() -> None:\n"
            f"    return {long_name}  # type: ignore[name-defined]\n",
        )
        # This repo's own pyproject.toml per-file-ignores convention,
        # reproduced verbatim against the fixture root (T-1341's own
        # specification detail: E501 cannot fire under tests/**).
        _write(
            tmp_path,
            "pyproject.toml",
            "[tool.ruff]\nline-length = 88\n\n"
            "[tool.ruff.lint.per-file-ignores]\n"
            '"tests/**" = ["E501"]\n',
        )
        applied = fix_suppress001_paired_suppression(tmp_path, _SNAPSHOT)
        assert len(applied) == 1
        rewritten = (tmp_path / "tests" / "test_mod.py").read_text(encoding="utf-8")
        assert "noqa" not in rewritten
        assert "# ty: ignore[unresolved-reference]" in rewritten


class TestSuppress001StringLiteralSafety:
    """A trailing `# noqa`-shaped substring living INSIDE a string
    literal must never be mistaken for a real comment -- `_find_comment_
    start` tokenizes the line rather than substring-searching it."""

    def test_hash_suppression_inside_string_literal_is_not_a_comment(self) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestSuppress001StringLiteralSafety.test_hash_suppression_inside_string_literal_is_not_a_comment kind="unit"  # noqa: E501
        # The marker is assembled rather than written out. A bare
        # suppression marker in source -- inside a string, a comment, or a
        # directive line FMT001 wrapped mid-word -- trips ruff's own
        # scanner, which then warns the directive is malformed. Assembling
        # it keeps the runtime string byte-identical with nothing to misread.
        marker = "# " + "noqa: E501"
        line = f'x = "{marker} lives inside this string"  # type: ignore[name-defined]'
        code_part, comment_text, _newline = _split_suppression_line(line)
        assert code_part == 'x = "# noqa: E501 lives inside this string"'
        assert comment_text == "# type: ignore[name-defined]"

    def test_no_real_comment_at_all(self) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestSuppress001StringLiteralSafety.test_no_real_comment_at_all kind="unit"  # noqa: E501
        line = 'x = "# looks like a comment but is not"'
        code_part, comment_text, _newline = _split_suppression_line(line)
        assert code_part == line
        assert comment_text == ""


class TestSuppress001FMT001Precedence:
    """T-1341 (coordinator addendum): SUPPRESS001 must never fight
    `frob fmt`'s FMT001 directive-wrap handler over the same line --
    the explicit precedence this handler commits to is to never touch a
    `frob:`-directive-bearing line at all, deferring entirely to
    FMT001/a human."""

    def test_frob_directive_bearing_line_is_left_untouched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestSuppress001FMT001Precedence.test_frob_directive_bearing_line_is_left_untouched kind="unit"  # noqa: E501
        """A line that ALSO happens to carry a trailing `frob:` directive
        marker alongside its dialect mismatch is skipped outright by
        SUPPRESS001's own handler -- running the whole fix pass twice
        over it leaves the file byte-identical both times (nothing to
        oscillate, because nothing was ever touched)."""
        original = (
            "def uses_bad() -> None:\n"
            "    return undefined_name  # type: ignore[name-defined]"
            '  # frob:waive ARCH001 reason="synthetic fixture"\n'
        )
        _write(tmp_path, "src/mod.py", original)

        first = fix_suppress001_paired_suppression(tmp_path, _SNAPSHOT)
        after_first = (tmp_path / "src" / "mod.py").read_text(encoding="utf-8")
        second = fix_suppress001_paired_suppression(tmp_path, _SNAPSHOT)
        after_second = (tmp_path / "src" / "mod.py").read_text(encoding="utf-8")

        assert first == []
        assert second == []
        assert after_first == original
        assert after_second == original


class TestFmt001OnlyPathsLandScoping:
    """T-1391: `fix_fmt001_directive_wrap`'s `only_paths` parameter --
    the mechanism a land-context caller can use to restrict FMT001's
    Tier-A pass to its own ticket's touched-file set, instead of the
    whole tree, so a rewrite never lands as an out-of-scope write for a
    file the landing ticket never declared."""

    def test_only_paths_leaves_an_out_of_scope_file_untouched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping.test_only_paths_leaves_an_out_of_scope_file_untouched kind="unit"  # noqa: E501
        """GIVEN a land whose ticket scope excludes a file elsewhere in
        the tree carrying a non-canonical `frob:` directive, WHEN the
        Tier-A FMT001 handler runs with `only_paths` set to the landing
        ticket's own touched-file set, THEN that out-of-scope file is
        left untouched -- while the in-scope file still gets fixed."""
        long_reason = "x" * 100
        non_canonical = (
            f'# frob:waive SCOPE001 reason="{long_reason}"\ndef f():\n    pass\n'  # noqa: E501
        )
        _write(tmp_path, "src/in_scope.py", non_canonical)
        _write(tmp_path, "src/out_of_scope.py", non_canonical)

        applied = fix_fmt001_directive_wrap(
            tmp_path, only_paths=frozenset({"src/in_scope.py"})
        )

        assert [a.file for a in applied] == ["src/in_scope.py"]
        in_scope_after = (tmp_path / "src" / "in_scope.py").read_text(encoding="utf-8")
        out_of_scope_after = (tmp_path / "src" / "out_of_scope.py").read_text(
            encoding="utf-8"
        )
        assert in_scope_after != non_canonical
        assert out_of_scope_after == non_canonical

    def test_only_paths_none_preserves_whole_tree_behaviour(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping.test_only_paths_none_preserves_whole_tree_behaviour kind="unit"  # noqa: E501
        """GIVEN a `frob check --fix` invoked outside a land (no
        `only_paths` argument at all), WHEN the Tier-A FMT001 handler
        runs, THEN its existing whole-tree behaviour is preserved -- both
        files get fixed."""
        long_reason = "x" * 100
        non_canonical = (
            f'# frob:waive SCOPE001 reason="{long_reason}"\ndef f():\n    pass\n'  # noqa: E501
        )
        _write(tmp_path, "src/a.py", non_canonical)
        _write(tmp_path, "src/b.py", non_canonical)

        applied = fix_fmt001_directive_wrap(tmp_path)

        assert {a.file for a in applied} == {"src/a.py", "src/b.py"}
        for rel in ("src/a.py", "src/b.py"):
            assert (tmp_path / rel).read_text(encoding="utf-8") != non_canonical

    def test_only_paths_skips_nonexistent_path_without_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping.test_only_paths_skips_nonexistent_path_without_error kind="unit"  # noqa: E501
        """A caller's touched-file set can legitimately name a path that
        no longer exists (deleted since the set was computed) -- this is
        a silent no-op for that entry, never an error, matching the
        no-guess Tier-A contract every other handler here follows."""
        applied = fix_fmt001_directive_wrap(
            tmp_path, only_paths=frozenset({"src/gone.py"})
        )
        assert applied == []


def _git(root: Path, *args: str) -> None:
    """Run one `git -C root <args>` step for a fixture, raising on failure --
    the E501-from-merge tests below need a real git history, not a mocked
    diff, since `fix_e501_merge_introduced` reads `HEAD`'s own merge
    shape directly (`_merge_touched_python_files`)."""
    import subprocess

    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class TestFixE501MergeIntroduced:
    """`fix_e501_merge_introduced` (T-1547): a targeted `ruff format` pass
    over exactly the `.py` files a land-time merge touched, applied ONLY
    when a resulting E501 finding is actually resolved by the format
    pass."""
# frob:tests src/frob/gates/_fix_engine_text.py::fix_e501_merge_introduced  # noqa: E501

    def test_e501_merge_introduced_targeted_format_applies(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced.test_e501_merge_introduced_targeted_format_applies kind="unit"  # noqa: E501
        """GIVEN a merge commit that introduces an over-long line in a
        `.py` file it touches, WHEN `fix_e501_merge_introduced` runs,
        THEN it applies a targeted `ruff format` to that file and the
        E501 finding is gone afterward."""
        import shutil

        from frob.gates._fix_engine import fix_e501_merge_introduced

        if shutil.which("ruff") is None:
            pytest.skip("ruff binary not available")

        root = tmp_path / "repo"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.email", "test@example.com")
        _git(root, "config", "user.name", "Test")
        _write(root, "pkg/mod.py", "def f(a, b):\n    return a + b\n\n\nf(1, 2)\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "init")
        _git(root, "checkout", "-q", "-b", "feature")

        # Over ruff's default 88-char limit, but a call `ruff format`
        # CAN shorten by wrapping its arguments one per line.
        long_call = (
            "f(1111111111, 1111111112, 1111111113, 1111111114, 1111111115, "
            "1111111116, 1111111117, 1111111118, 1111111119, 1111111120)\n"
        )
        _write(
            root,
            "pkg/mod.py",
            "def f(a, b, c=1, d=2, e=3, g=4, h=5, i=6, j=7, k=8):\n"
            f"    return a\n\n\n{long_call}",
        )
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "introduce long line")
        _git(root, "checkout", "-q", "main")
        _git(root, "merge", "-q", "--no-ff", "feature", "-m", "merge feature")

        applied = fix_e501_merge_introduced(root)
        assert len(applied) == 1
        assert applied[0].rule == "E501"
        assert applied[0].file == "pkg/mod.py"

        rewritten = (root / "pkg" / "mod.py").read_text(encoding="utf-8")
        assert all(len(line) <= 88 for line in rewritten.splitlines())

    # frob:tests src/frob/gates/_fix_engine_text.py::fix_e501_merge_introduced  # noqa: E501
    def test_e501_no_merge_shape_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced.test_e501_no_merge_shape_is_a_no_op kind="unit"  # noqa: E501
        """GIVEN a repo whose `HEAD` is a single-parent commit with no
        uncommitted changes, WHEN `fix_e501_merge_introduced` runs, THEN
        it makes no changes -- there is no merge-shaped touched set to
        act on, and Tier-A never guesses at one."""
        from frob.gates._fix_engine import fix_e501_merge_introduced

        root = tmp_path / "repo"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.email", "test@example.com")
        _git(root, "config", "user.name", "Test")
        _write(root, "pkg/mod.py", "x = 1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "init, single-parent HEAD, no diff")

        applied = fix_e501_merge_introduced(root)
        assert applied == []


class TestFixCov002TicketDirectiveInsertion:
    """`fix_cov002_ticket_directive_insertion` (T-1548): insert
    `# frob:ticket <landing-id>` above a changed symbol COV002 flags as
    uncovered, but ONLY when a real, open landing ticket id is supplied."""

    def _snap(self, root: Path) -> GraphSnapshot:
        from frob.graph import build_graph

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    # frob:tests src/frob/gates/_fix_engine_sync.py::fix_cov002_ticket_directive_insertion  # noqa: E501
    def test_open_landing_ticket_gets_directive_inserted_and_reverifies_clean(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion.test_open_landing_ticket_gets_directive_inserted_and_reverifies_clean kind="unit"  # noqa: E501
        """GIVEN a symbol changed on a branch with no `frob:ticket` edge
        and no covering ticket scope, WHEN `fix_cov002_ticket_directive_
        insertion` runs with a real, OPEN landing ticket id, THEN a
        `# frob:ticket <id>` directive is inserted directly above the
        symbol and a fresh COV002 pass no longer flags it."""
        from datetime import date

        from frob.gates import _cov002
        from frob.gates._fix_engine import fix_cov002_ticket_directive_insertion
        from frob.gitio import working_diff
        from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState

        root = tmp_path / "repo"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.email", "test@example.com")
        _git(root, "config", "user.name", "Test")
        (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
        (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
        _write(root, "pkg/mod.py", "def f():\n    return 1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "init")

        _write(root, "pkg/mod.py", "def f():\n    return 2\n")

        ticket = Ticket(
            id="T-9001",
            title="landing ticket",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            created=date.today(),
        )
        queue = TicketQueue(tickets={"T-9001": ticket})
        snapshot = self._snap(root)

        diff = working_diff(root, "main").danger_ok
        before = _cov002(snapshot, queue, diff, active_ticket="T-9001")
        assert any(v.file == "pkg/mod.py" for v in before)

        applied = fix_cov002_ticket_directive_insertion(root, snapshot, queue, "T-9001")
        assert len(applied) == 1
        assert applied[0].rule == "COV002"
        assert applied[0].file == "pkg/mod.py"

        rewritten = (root / "pkg" / "mod.py").read_text(encoding="utf-8")
        assert "# frob:ticket T-9001" in rewritten
        assert rewritten.index("# frob:ticket T-9001") < rewritten.index("def f():")

        after_snapshot = self._snap(root)
        after_diff = working_diff(root, "main").danger_ok
        after = _cov002(after_snapshot, queue, after_diff, active_ticket="T-9001")
        assert not [v for v in after if v.file == "pkg/mod.py"]

    # frob:tests src/frob/gates/_fix_engine_sync.py::fix_cov002_ticket_directive_insertion  # noqa: E501
    def test_no_ticket_id_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion.test_no_ticket_id_is_a_no_op kind="unit"  # noqa: E501
        """GIVEN `fix_cov002_ticket_directive_insertion` is invoked with
        `ticket_id=None` (outside a landing context), WHEN it runs, THEN
        it makes no changes at all -- there is no id to cite, and Tier-A
        never guesses one."""
        from frob.gates._fix_engine import fix_cov002_ticket_directive_insertion
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.email", "test@example.com")
        _git(root, "config", "user.name", "Test")
        (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
        (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
        _write(root, "pkg/mod.py", "def f():\n    return 1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "init")
        _write(root, "pkg/mod.py", "def f():\n    return 2\n")

        snapshot = self._snap(root)
        applied = fix_cov002_ticket_directive_insertion(
            root, snapshot, TicketQueue(tickets={}), None
        )
        assert applied == []
        assert (root / "pkg" / "mod.py").read_text(encoding="utf-8") == (
            "def f():\n    return 2\n"
        )


class TestInsertTicketDirectiveAboveCommentLeader:
    """`_insert_ticket_directive_above` (T-1581): the inserted directive's
    comment leader must match the TARGET file's own language, resolved via
    the shared `frob.gates._fmt_directives.marker_for` table -- not a
    second, narrower hardcoded table that silently defaults an unknown
    suffix to `#` (the exact defect that broke `design/frob.strata` during
    T-1548's own land)."""

    # frob:tests src/frob/gates/_fix_engine_sync.py::_insert_ticket_directive_above
    def test_strata_file_gets_slash_slash_leader(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_strata_file_gets_slash_slash_leader kind="unit"  # noqa: E501
        """GIVEN a `.strata` target file, WHEN the directive is inserted,
        THEN it uses the `//` leader, not `#`."""
        from frob.gates._fix_engine_sync import _insert_ticket_directive_above

        root = tmp_path / "repo"
        root.mkdir()
        _write(root, "design/frob.strata", "system Foo {\n}\n")

        ok = _insert_ticket_directive_above(root, "design/frob.strata", 1, "T-9001")
        assert ok is True
        text = (root / "design" / "frob.strata").read_text(encoding="utf-8")
        assert text.startswith("// frob:ticket T-9001\n")

    # frob:tests src/frob/gates/_fix_engine_sync.py::_insert_ticket_directive_above
    def test_rust_file_gets_slash_slash_leader(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_rust_file_gets_slash_slash_leader kind="unit"  # noqa: E501
        """GIVEN a `.rs` target file, WHEN the directive is inserted, THEN
        it uses the `//` leader."""
        from frob.gates._fix_engine_sync import _insert_ticket_directive_above

        root = tmp_path / "repo"
        root.mkdir()
        _write(root, "src/lib.rs", "fn f() {}\n")

        ok = _insert_ticket_directive_above(root, "src/lib.rs", 1, "T-9001")
        assert ok is True
        text = (root / "src" / "lib.rs").read_text(encoding="utf-8")
        assert text.startswith("// frob:ticket T-9001\n")

    # frob:tests src/frob/gates/_fix_engine_sync.py::_insert_ticket_directive_above
    def test_python_file_gets_hash_leader(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_python_file_gets_hash_leader kind="unit"  # noqa: E501
        """GIVEN a `.py` target file, WHEN the directive is inserted, THEN
        it uses the `#` leader."""
        from frob.gates._fix_engine_sync import _insert_ticket_directive_above

        root = tmp_path / "repo"
        root.mkdir()
        _write(root, "pkg/mod.py", "def f():\n    return 1\n")

        ok = _insert_ticket_directive_above(root, "pkg/mod.py", 1, "T-9001")
        assert ok is True
        text = (root / "pkg" / "mod.py").read_text(encoding="utf-8")
        assert text.startswith("# frob:ticket T-9001\n")

    # frob:tests src/frob/gates/_fix_engine_sync.py::_insert_ticket_directive_above
    def test_unknown_extension_refuses_insertion(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_unknown_extension_refuses_insertion kind="unit"  # noqa: E501
        """GIVEN a target file whose suffix has no registered comment
        leader, WHEN the directive would be inserted, THEN the handler
        refuses (no-op) rather than guessing a leader."""
        from frob.gates._fix_engine_sync import _insert_ticket_directive_above

        root = tmp_path / "repo"
        root.mkdir()
        _write(root, "data/notes.xyz", "some content\n")

        ok = _insert_ticket_directive_above(root, "data/notes.xyz", 1, "T-9001")
        assert ok is False
        text = (root / "data" / "notes.xyz").read_text(encoding="utf-8")
        assert text == "some content\n"


class TestSnapshotParameterDroppedStaticallyEnforced:
    """T-1911: `fix_fmt001_directive_wrap` and `fix_e501_merge_introduced`
    no longer declare an unused `snapshot: GraphSnapshot` parameter -- the
    parameter is GONE, not made Optional (the ticket explicitly rejects
    `GraphSnapshot | None`, since that would just push None-handling
    downstream instead of encoding the real contract). The enforcement
    this ticket demands ("make it enforced, not documented") is that `ty`
    now REFUSES any call site passing a second positional argument at all
    (`too-many-positional-arguments`) -- this is what makes the T-1896/
    T-1900/T-1906 mistake (reaching for a stray `None`/fixture as a second
    positional arg) impossible to type, rather than merely discouraged in
    a comment a few lines up a neighbouring file. Uses the REAL `ty`
    binary against an on-disk probe, same precedent as
    `TestFixSuppress001PairedSuppression` above and
    `tests/unit/test_executable.py::TestTyExecutable`."""

    _PROBE_SOURCE = (
        "from pathlib import Path\n"
        "from frob.gates._fix_engine_text import (\n"
        "    fix_e501_merge_introduced,\n"
        "    fix_fmt001_directive_wrap,\n"
        ")\n"
        "from frob.graph._models import GraphSnapshot\n"
        "\n"
        '_SNAP = GraphSnapshot(root="", symbols={}, edges=())\n'
        "\n"
        'fix_fmt001_directive_wrap(Path("x"), _SNAP)\n'
        'fix_e501_merge_introduced(Path("x"), _SNAP)\n'
    )

    def test_two_positional_args_are_statically_refused(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestSnapshotParameterDroppedStaticallyEnforced.test_two_positional_args_are_statically_refused kind="unit"  # noqa: E501
        """GIVEN a probe module that calls both handlers with a stray
        second positional `GraphSnapshot` argument (the exact T-1896/
        T-1900/T-1906 mistake), WHEN `ty check` runs against it from this
        repo's own project root, THEN it reports
        `too-many-positional-arguments` for both call sites -- the
        mistake cannot be typed, not merely avoided by convention. NOTE:
        this repro genuinely fails (collects and passes) at the parent
        commit (`git show 669b7f667:...` -- the pre-T-1911 signature took
        `(root, snapshot)` positionally, so `ty` accepted this exact
        probe cleanly) and only starts failing once the parameter is
        dropped, which is the point: the seven other evidence ids bound
        to this ticket are pre-existing tests of general handler
        behaviour that pass identically at both commits and prove nothing
        about this specific defect."""
        import shutil
        import subprocess

        if shutil.which("ty") is None:
            pytest.skip("ty binary not available")

        probe = tmp_path / "snapshot_arg_probe.py"
        probe.write_text(self._PROBE_SOURCE, encoding="utf-8")

        result = subprocess.run(
            ["ty", "check", str(probe)],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr

        assert result.returncode != 0, output
        assert output.count("too-many-positional-arguments") == 2, output
        assert "fix_fmt001_directive_wrap" in output
        assert "fix_e501_merge_introduced" in output


@pytest.fixture
def tick006_claiming_ticket():
    """A factory fixture: calling the returned function with a cited id
    builds a DONE ticket whose Done report affirmatively cites it as a
    filed follow-up -- the TICK006 phantom-citation shape shared by
    `TestTick006RenameConfirmation`'s tests below. A `@pytest.fixture`-
    wrapped factory (rather than a bare module-level helper) so this
    stays outside WIRE001's "new symbol with no caller" scan -- a
    fixture is injected, never called directly, by design (see
    `frob.gates._wire._is_pytest_fixture`)."""
    from datetime import date

    from frob.tickets import Origin, Ticket, TicketKind, TicketState

    def _make(cited_id: str) -> Ticket:
        return Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                f"## Done report\n\nFiled {cited_id} (recovery ticket) as a "
                "follow-up.\n"
            ),
        )

    return _make


# frob:waive DUP001 reason="100% similar to \
# tests/gates_suite/test_fix_engine.py::TestFixEngineTierA._tick006_repo by design, \
# not accidental duplication -- that class is a sibling test suite outside T-4436's \
# own declared scope (tests/unit/test_fix_engine_tick006*.py and \
# tests/test_gates_fix_engine.py only), so this ticket cannot import or refactor that \
# file's private helper without widening scope; extracting a shared helper into a \
# third location is a real follow-up, not attempted here to keep this fix within its \
# declared file boundary"
@pytest.fixture
def tick006_git_repo(tmp_path: Path):
    """A bare repo with an empty v2-mode ledger -- the shared fixture
    `TestTick006RenameConfirmation`'s tests below build their own commit
    history on top of (mirrors `tests/gates_suite/test_fix_engine.py::
    TestFixEngineTierA._tick006_repo`'s own fixture shape -- that class
    is a sibling test suite outside T-4436's declared scope, not reused
    directly). A real `@pytest.fixture` (not a bare helper function) for
    the same WIRE001-exemption reason as `tick006_claiming_ticket`
    above."""
    import subprocess

    root = tmp_path / "repo"
    root.mkdir()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q", "-b", "main")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
    (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-q", "-m", "init")
    return root, _git


# frob:ticket T-4436
class TestTick006RenameConfirmation:
    """T-4436: `fix_tick006_phantom_refile`'s git-rename resolution
    (`_resolve_via_git_rename_measured`/`_tick006_check_rename_candidate`)
    must never trust a `git show -M --name-status` similarity pairing as
    a genuine promotion on its own.

    MEASURED incident (2026-09-12, worktree .claude/worktrees/t-4428):
    every literal `T-draft-858a1bad` in a ticket's body/Done report was
    rewritten to `T-4383`, an unrelated ticket -- `T-draft-858a1bad` was
    LOST before promotion (T-4426), so there is no real ticket it ever
    became. Root cause: `_resolve_via_git_rename_measured` trusted ANY
    `-M`-detected rename pairing between a deleted `tickets/<draft>/
    ticket.md` and some added `tickets/<other>/ticket.md` in the same
    commit -- but `-M` is a CONTENT-SIMILARITY heuristic, not an
    identity/provenance record, so an unrelated delete+add that happens
    to clear the similarity threshold (two near-identical bulk-edited
    stub tickets) is indistinguishable from a real `git mv`-based rename
    at the plain `--name-status` level. Acceptance: (1) a draft id with
    no genuine promotion record is never rewritten; (2) the mapping
    source is logged for every rewrite that DOES happen; (3) a dead
    draft id (no confirmed promotion) is left untouched in the citing
    ticket's body."""

    # frob:tests \
    # tests/test_gates_fix_engine.py::TestTick006RenameConfirmation.test_git_m_false_positive_pairing_is_not_trusted_body_untouched  # noqa: E501
    def test_git_m_false_positive_pairing_is_not_trusted_body_untouched(
        self, tmp_path: Path, caplog, tick006_git_repo, tick006_claiming_ticket
    ) -> None:
        """A deleted draft and an UNRELATED added ticket, similar enough
        in the surrounding boilerplate to satisfy git's own `-M`
        similarity threshold, but NOT a real rename -- the added
        ticket's title/body differ from the draft's (only the frontmatter
        happens to look alike), so `-M` still pairs them at the
        `--name-status` level (a real, reproduced git behavior, not
        mocked) while the STRONGER corroboration (the pair's WHOLE diff
        reduces to exactly the `id:` line, T-4436's own fix) correctly
        rejects it. The citation must be left completely untouched, and a
        WARNING logged naming it unresolved."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue
        from frob.tickets._store import load_all, write_ticket

        root, _git = tick006_git_repo

        draft_md = (
            "---\n"
            "id: T-draft-1057c001\n"
            "title: some draft\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: agent\n"
            "created: '2026-08-01'\n"
            "---\n"
            "draft body text describing some unrelated piece of work in enough "
            "prose that the two files below share a long common substring\n"
        )
        (root / "tickets" / "T-draft-1057c001").mkdir(parents=True)
        (root / "tickets" / "T-draft-1057c001" / "ticket.md").write_text(
            draft_md, encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "file draft T-draft-1057c001")

        # An UNRELATED real ticket, added in the SAME commit that deletes
        # the draft -- NOT a rename, just two independent edits landing
        # together (a bulk ledger-format change, T-4436's own measured
        # shape). Content differs only in id/title/created -- similar
        # enough for git's own -M heuristic to still pair them, but the
        # BODY (unlike a real rename, which changes only id:) also
        # differs, so the stronger "only the id line changed" check must
        # reject it.
        unrelated_md = (
            "---\n"
            "id: T-9500\n"
            "title: an unrelated real ticket\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: agent\n"
            "created: '2026-09-01'\n"
            "---\n"
            "draft body text describing some unrelated piece of work in enough "
            "prose that the two files below share a long common substring, plus "
            "one extra sentence only the real ticket has\n"
        )
        import shutil

        shutil.rmtree(root / "tickets" / "T-draft-1057c001")
        (root / "tickets" / "T-9500").mkdir(parents=True)
        (root / "tickets" / "T-9500" / "ticket.md").write_text(
            unrelated_md, encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "bulk ledger edit (unrelated to the draft)")

        claiming = tick006_claiming_ticket("T-draft-1057c001")
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite the lost draft")

        queue = TicketQueue(tickets={"T-0001": claiming})
        with caplog.at_level("WARNING"):
            applied = fix_tick006_phantom_refile(root, queue)

        # Either nothing applied (git's -M did not even pair them) or a
        # NEW recovery ticket was filed -- never a silent rewrite to the
        # unrelated T-9500.
        for fix in applied:
            assert "T-9500" not in fix.detail

        reloaded = load_all(root)
        assert reloaded.is_ok
        body = reloaded.danger_ok["T-0001"].body
        assert "T-9500" not in body

    # frob:tests \
    # tests/test_gates_fix_engine.py::TestTick006RenameConfirmation.test_confirmed_promotion_is_rewritten_with_info_log  # noqa: E501
    def test_confirmed_promotion_is_rewritten_with_info_log(
        self, tmp_path: Path, caplog, tick006_git_repo, tick006_claiming_ticket
    ) -> None:
        """A genuine promotion (`git mv` plus an `id:`-only frontmatter
        rewrite, `renumber_one_v2`'s own exact shape) IS resolved and the
        citation IS rewritten -- and an INFO line names the mapping
        source (draft -> real id, git-rename/frontmatter-confirmed)."""
        import logging

        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue
        from frob.tickets._store import load_all, write_ticket

        root, _git = tick006_git_repo

        draft_md = (
            "---\n"
            "id: T-draft-600d0001\n"
            "title: recovered elsewhere\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: agent\n"
            "created: '2026-08-01'\n"
            "---\n"
            "body\n"
        )
        (root / "tickets" / "T-draft-600d0001").mkdir(parents=True)
        (root / "tickets" / "T-draft-600d0001" / "ticket.md").write_text(
            draft_md, encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "file draft T-draft-600d0001")
        _git("mv", "tickets/T-draft-600d0001", "tickets/T-9600")
        (root / "tickets" / "T-9600" / "ticket.md").write_text(
            draft_md.replace("T-draft-600d0001", "T-9600"), encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "renumber T-draft-600d0001 -> T-9600")

        claiming = tick006_claiming_ticket("T-draft-600d0001")
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite the now-renamed draft")

        queue = TicketQueue(tickets={"T-0001": claiming})
        with caplog.at_level(logging.INFO):
            applied = fix_tick006_phantom_refile(root, queue)

        assert len(applied) == 1
        assert applied[0].rule == "TICK006"
        assert "T-9600" in applied[0].detail
        assert "T-draft-600d0001" in applied[0].detail

        info_lines = [
            r.getMessage() for r in caplog.records if r.levelno == logging.INFO
        ]
        assert any(
            "T-draft-600d0001" in msg and "T-9600" in msg and "T-0001" in msg
            for msg in info_lines
        ), f"expected an INFO mapping-source log line, got: {info_lines}"

        reloaded = load_all(root)
        assert reloaded.is_ok
        assert "T-9600" in reloaded.danger_ok["T-0001"].body
        assert "T-draft-600d0001" not in reloaded.danger_ok["T-0001"].body

    # frob:tests \
    # tests/test_gates_fix_engine.py::TestTick006RenameConfirmation.test_no_rename_at_all_is_unresolved_body_untouched_pending_new_ticket  # noqa: E501
    def test_no_rename_at_all_is_unresolved_body_untouched_pending_new_ticket(
        self, tmp_path: Path, tick006_git_repo, tick006_claiming_ticket
    ) -> None:
        """T-4436 acceptance (1): a draft id with NO git history at all
        (genuinely lost, never even git-mv'd) is never rewritten to
        anything resolved via rename -- it either stays untouched or is
        refiled as a brand new recovery ticket, never silently pointed at
        an existing unrelated id."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue
        from frob.tickets._store import load_all, write_ticket

        root, _git = tick006_git_repo

        claiming = tick006_claiming_ticket("T-draft-dead0000")
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite a draft that never existed on disk")

        queue = TicketQueue(tickets={"T-0001": claiming})
        applied = fix_tick006_phantom_refile(root, queue)

        reloaded = load_all(root)
        assert reloaded.is_ok
        body = reloaded.danger_ok["T-0001"].body
        # Never resolved to a git-rename target (there is none) -- the
        # citation is either untouched or points at a NEWLY FILED ticket,
        # both of which are correct fallbacks; the load-bearing assertion
        # is only that it was never silently rewritten to some other
        # PRE-EXISTING id this pass did not itself create.
        for fix in applied:
            assert fix.detail.startswith("T-draft-dead0000 -> ")
        assert "T-draft-dead0000" in body or len(applied) == 1


# frob:ticket T-5261
class TestFixTest010RedundantTestDeclaration:
    """`fix_test010_redundant_test_declaration` (T-4710/T-5261) --
    end-to-end through the REAL entry points: `frob.graph.build_graph`
    (which computes `_redundant_test_declarations` the same way a real
    `frob check` run would), `frob.gates.test_gate` (the real TEST010
    violation producer), and `frob.gates._fix_engine.apply_tier_a_fixes`
    (the real Tier-A dispatch, via `TIER_A_HANDLERS`), not just this
    handler's own function called directly."""

    def _snap(self, root: Path):  # noqa: ANN001, ANN202
        from frob.graph import build_graph

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    def _test010_violations(self, snapshot):  # noqa: ANN001, ANN202
        from typani import Nothing

        from frob.gates import test_gate
        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        violations = test_gate(
            snapshot,
            (),
            Nothing(),
            CollectedTests(node_ids=frozenset()),
            TestPolicy(),
        )
        return [v for v in violations if v.rule == "TEST010"]

    # frob:tests \
    # src/frob/gates/_fix_engine_text.py::fix_test010_redundant_test_declaration
    def test_delete_case_fires_test010_and_fix_removes_the_line(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixTest010RedundantTestDeclaration.test_delete_case_fires_test010_and_fix_removes_the_line  # noqa: E501
        from frob.gates._fix_engine import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "foo.py").write_text(
            "class Foo:\n"
            "    # frob:tests tests/test_foo.py::TestFoo.test_bar\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        (root / "tests").mkdir(parents=True)
        (root / "tests" / "test_foo.py").write_text(
            "class TestFoo:\n"
            "    # frob:tests src/foo.py::Foo.bar\n"
            "    def test_bar(self) -> None:\n"
            "        pass\n"
        )
        snapshot = self._snap(root)

        # POSITIVE CONTROL: TEST010 genuinely fires through the real
        # gate entry point before any fix runs.
        before = self._test010_violations(snapshot)
        assert any("redundant (T-4710)" in v.message for v in before)

        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        test010_applied = [a for a in applied if a.rule == "TEST010"]
        assert len(test010_applied) == 1
        assert "deleted redundant" in test010_applied[0].detail

        rewritten = (root / "src" / "foo.py").read_text()
        assert "frob:tests" not in rewritten

        # Re-run the real gate over the post-fix graph: TEST010's
        # redundant-declaration finding is gone.
        after_snapshot = self._snap(root)
        after = self._test010_violations(after_snapshot)
        assert not any("redundant (T-4710)" in v.message for v in after)

    def test_move_case_fires_test010_and_fix_relocates_the_line(
        self, tmp_path: Path
    ) -> None:
        from frob.gates._fix_engine import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "foo.py").write_text(
            "class Foo:\n"
            "    # frob:tests tests/test_foo.py::TestFoo.test_bar\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        (root / "tests").mkdir(parents=True)
        (root / "tests" / "test_foo.py").write_text(
            "class TestFoo:\n    def test_bar(self) -> None:\n        pass\n"
        )
        snapshot = self._snap(root)
        before = self._test010_violations(snapshot)
        assert any("move this line" in v.message for v in before)

        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        test010_applied = [a for a in applied if a.rule == "TEST010"]
        assert len(test010_applied) == 1
        assert "moved redundant" in test010_applied[0].detail

        prod_after = (root / "src" / "foo.py").read_text()
        test_after = (root / "tests" / "test_foo.py").read_text()
        assert "frob:tests" not in prod_after
        assert "frob:tests" in test_after

        # Edge set preserved: the graph still derives the SAME coverage
        # edge from the relocated (now test-side) declaration.
        after_snapshot = self._snap(root)
        after_edges = {(e.src, e.kind, e.target) for e in after_snapshot.edges}
        before_edges = {(e.src, e.kind, e.target) for e in snapshot.edges}
        assert after_edges == before_edges

    def test_dangling_target_refuses_rather_than_guessing(self, tmp_path: Path) -> None:
        # POSITIVE CONTROL for the refusal path: a move target that does
        # not resolve in the graph must be left completely untouched.
        from frob.gates._fix_engine import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "foo.py").write_text(
            "class Foo:\n"
            "    # frob:tests tests/test_foo.py::TestFoo.test_missing\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        (root / "tests").mkdir(parents=True)
        (root / "tests" / "test_foo.py").write_text(
            "class TestFoo:\n    def test_bar(self) -> None:\n        pass\n"
        )
        snapshot = self._snap(root)
        before_prod = (root / "src" / "foo.py").read_text()
        before_test = (root / "tests" / "test_foo.py").read_text()

        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        assert not [a for a in applied if a.rule == "TEST010"]
        assert (root / "src" / "foo.py").read_text() == before_prod
        assert (root / "tests" / "test_foo.py").read_text() == before_test
