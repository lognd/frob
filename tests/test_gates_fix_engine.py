"""Tests for `frob.gates._fix_engine`'s SUPPRESS001 Tier-A auto-fix handler
(T-1341, phase 2 of T-1339): writing the paired suppression comment in
canonical order, idempotently. Uses the REAL `ty`/`mypy` binaries against
small on-disk fixtures -- same precedent as `tests/test_gates_suppress.py`
(the whole point of SUPPRESS001 is real, observed diagnostics, not mocked
output), both tools already dev dependencies this suite requires."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._fix_engine import (
    FixApplied,
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

    def test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_mypy\
        # _suppressed_ty_unsuppressed_gets_paired_suppression kind="unit"
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

    def test_idempotent_second_fix_pass_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_idem\
        # potent_second_fix_pass_is_a_no_op kind="unit"
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
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_merg\
        # es_with_existing_other_code_canonical_order kind="unit"
        """A pre-existing `# noqa: F401` on the fixed line is MERGED, not
        clobbered -- `E501,F401` in canonical alphabetical order,
        preserving the pre-existing code."""
        merged = _merged_dialect_codes({"ruff": {"F401"}}, "ruff", "E501")
        assert merged == {"ruff": {"F401", "E501"}}

    def test_no_available_oracle_no_op(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_no_a\
        # vailable_oracle_no_op kind="unit"
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
        # tests/test_gates_fix_engine.py::TestSuppress001NoOpSuppressionRefusal.test_co\
        # de_ignored_for_path_true_under_tests_glob kind="unit"
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
        # tests/test_gates_fix_engine.py::TestSuppress001NoOpSuppressionRefusal.test_no\
        # _op_suppression_never_added_under_tests_glob kind="unit"
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
        # tests/test_gates_fix_engine.py::TestSuppress001StringLiteralSafety.test_hash_\
        # suppression_inside_string_literal_is_not_a_comment kind="unit"
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
        # tests/test_gates_fix_engine.py::TestSuppress001StringLiteralSafety.test_no_re\
        # al_comment_at_all kind="unit"
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
        # tests/test_gates_fix_engine.py::TestSuppress001FMT001Precedence.test_frob_dir\
        # ective_bearing_line_is_left_untouched kind="unit"
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
        # tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping.test_only_path\
        # s_leaves_an_out_of_scope_file_untouched kind="unit"
        """GIVEN a land whose ticket scope excludes a file elsewhere in
        the tree carrying a non-canonical `frob:` directive, WHEN the
        Tier-A FMT001 handler runs with `only_paths` set to the landing
        ticket's own touched-file set, THEN that out-of-scope file is
        left untouched -- while the in-scope file still gets fixed."""
        long_reason = "x" * 100
        non_canonical = (
            f'# frob:waive INV006 reason="{long_reason}"\ndef f():\n    pass\n'  # noqa: E501
        )
        _write(tmp_path, "src/in_scope.py", non_canonical)
        _write(tmp_path, "src/out_of_scope.py", non_canonical)

        applied = fix_fmt001_directive_wrap(
            tmp_path, _SNAPSHOT, only_paths=frozenset({"src/in_scope.py"})
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
        # tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping.test_only_path\
        # s_none_preserves_whole_tree_behaviour kind="unit"
        """GIVEN a `frob check --fix` invoked outside a land (no
        `only_paths` argument at all), WHEN the Tier-A FMT001 handler
        runs, THEN its existing whole-tree behaviour is preserved -- both
        files get fixed."""
        long_reason = "x" * 100
        non_canonical = (
            f'# frob:waive INV006 reason="{long_reason}"\ndef f():\n    pass\n'  # noqa: E501
        )
        _write(tmp_path, "src/a.py", non_canonical)
        _write(tmp_path, "src/b.py", non_canonical)

        applied = fix_fmt001_directive_wrap(tmp_path, _SNAPSHOT)

        assert {a.file for a in applied} == {"src/a.py", "src/b.py"}
        for rel in ("src/a.py", "src/b.py"):
            assert (tmp_path / rel).read_text(encoding="utf-8") != non_canonical

    def test_only_paths_skips_nonexistent_path_without_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping.test_only_path\
        # s_skips_nonexistent_path_without_error kind="unit"
        """A caller's touched-file set can legitimately name a path that
        no longer exists (deleted since the set was computed) -- this is
        a silent no-op for that entry, never an error, matching the
        no-guess Tier-A contract every other handler here follows."""
        applied = fix_fmt001_directive_wrap(
            tmp_path, _SNAPSHOT, only_paths=frozenset({"src/gone.py"})
        )
        assert applied == []
