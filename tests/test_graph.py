"""Tests for frob.graph -- obligation graph registry (docs/modules/graph.md)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from frob.graph import (
    GraphError,
    build_graph,
    edges_from,
    edges_to,
    load_graph,
    resolve,
)
from frob.graph import cache as graph_cache
from frob.graph.digest import compute_digests
from frob.graph.dsl import markdown_anchors, parse_directives
from frob.lang import parse_file


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


_BASE_PY = '''"""Module docstring."""


class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        # frob:doc docs/x.md#widget
        data = value + 1
        return str(data)
'''


class TestDigests:
    def _parse(self, tmp_path: Path, text: str, name: str = "sample.py"):
        path = _write(tmp_path, name, text)
        return parse_file(path).danger_ok

    def _method(self, pf):
        return next(s for s in pf.symbols if s.qualname == "Widget.render")

    def test_reformat_identical_digests(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/digest.py::compute_digests
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        reformatted = _BASE_PY.replace("    def render", "    def   render") + "\n\n"
        rf = self._parse(tmp_path, reformatted, "b.py")
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(rf))
        assert d1.sig == d2.sig
        assert d1.body == d2.body

    def test_param_rename_moves_sig_only(self, tmp_path: Path) -> None:
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        renamed = self._parse(
            tmp_path,
            _BASE_PY.replace(
                "def render(self, value: int)", "def render(self, amount: int)"
            ),
            "b.py",
        )
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(renamed))
        assert d1.sig != d2.sig
        assert d1.body == d2.body
        assert d1.doc == d2.doc

    def test_body_edit_changes_body_only(self, tmp_path: Path) -> None:
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        edited = self._parse(
            tmp_path, _BASE_PY.replace("data = value + 1", "data = value + 2"), "b.py"
        )
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(edited))
        assert d1.sig == d2.sig
        assert d1.body != d2.body
        assert d1.doc == d2.doc

    def test_docstring_edit_changes_doc_only(self, tmp_path: Path) -> None:
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        edited = self._parse(
            tmp_path,
            _BASE_PY.replace('"""Render the widget."""', '"""Render it."""'),
            "b.py",
        )
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(edited))
        assert d1.sig == d2.sig
        assert d1.body == d2.body
        assert d1.doc != d2.doc

    def test_digest_sig_body_doc_are_independent_facets(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/digest.py::_digest_sig
        # frob:tests src/frob/graph/digest.py::_digest_body
        # frob:tests src/frob/graph/digest.py::_digest_doc
        from frob.graph.digest import _digest_body, _digest_doc, _digest_sig

        method = self._method(self._parse(tmp_path, _BASE_PY, "a.py"))
        sig = _digest_sig(method)
        body = _digest_body(method)
        doc = _digest_doc(method)
        # each facet is a distinct sha256 hex digest of a different token
        # stream, so a signature change must not perturb the other two.
        assert len(sig) == 64
        assert len(body) == 64
        assert len(doc) == 64
        assert sig != body
        renamed_method = self._method(
            self._parse(
                tmp_path,
                _BASE_PY.replace(
                    "def render(self, value: int)", "def render(self, amount: int)"
                ),
                "b.py",
            )
        )
        assert _digest_sig(renamed_method) != sig
        assert _digest_body(renamed_method) == body
        assert _digest_doc(renamed_method) == doc


class TestSymbolRecord:
    def test_symref_renders_canonical_path_qualname(self) -> None:
        # frob:tests src/frob/graph/_models.py::SymbolRecord.symref
        from frob.graph._models import Digests, SymbolId, SymbolRecord
        from frob.lang import SymbolKind

        record = SymbolRecord(
            id=SymbolId(path="src/a.py", qualname="Widget.render"),
            kind=SymbolKind.METHOD,
            public=True,
            digests=Digests(sig="s", body="b", doc="d"),
            span=(1, 2),
        )
        assert record.symref == "src/a.py::Widget.render"
        assert record.symref == str(record.id)


class TestDsl:
    def test_hash_comment_directive(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        src = """def foo() -> None:
    # frob:ticket T-0042
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "T-0042"
        assert edges[0].src.endswith("::foo")

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_slash_slash_directive(self, tmp_path: Path) -> None:
        src = """function foo(): void {
    // frob:invariant INV-007
}
"""
        pf = parse_file(_write(tmp_path, "a.ts", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "INV-007"

    def test_block_comment_directive(self, tmp_path: Path) -> None:
        src = """int foo(void) {
    /* frob:waive RULE-1 reason="known issue" */
    return 0;
}
"""
        pf = parse_file(_write(tmp_path, "a.c", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "RULE-1"
        assert edges[0].attrs["reason"] == "known issue"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_binds_to_enclosing_symbol(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:ticket T-0001
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_binds_to_following_symbol(self, tmp_path: Path) -> None:
        src = """# frob:ticket T-0002
def foo() -> None:
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_binds_to_nested_method_not_enclosing_class(self, tmp_path: Path) -> None:
        # frob:ticket T-0044
        src = """class Foo:
    # frob:ticket T-0044
    def bar(self) -> None:
        pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].src == f"{pf.path}::Foo.bar"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_binds_three_stacked_directives_to_def(self, tmp_path: Path) -> None:
        # frob:ticket T-0100
        src = """# frob:ticket T-0100
# frob:tests tests/a.py::foo kind="unit"
# frob:doc docs/a.md#foo
def foo() -> None:
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 3
        for edge in edges:
            assert edge.src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_binds_five_stacked_directives_to_def(self, tmp_path: Path) -> None:
        # frob:ticket T-0100
        src = """# frob:ticket T-0100
# frob:ticket T-0101
# frob:ticket T-0102
# frob:ticket T-0103
# frob:ticket T-0104
def foo() -> None:
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 5
        for edge in edges:
            assert edge.src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_directive_binds_past_trailing_comment_on_def_line(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-0100
        #
        # A trailing comment on the def line itself (e.g. a lint-suppression
        # marker like the one on the fixture's `def foo()` below)
        # must not be treated as a continuation of the directive's block --
        # doing so pushes the following-window past the def and loses the
        # binding entirely.
        src = """# frob:ticket T-0100
def foo():  # noqa: N802 - rule-id naming convention
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_stacked_directives_bind_past_trailing_comment_on_def_line(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-0100
        src = """# frob:ticket T-0100
# frob:tests tests/a.py::foo kind="unit"
# frob:doc docs/a.md#foo
def foo():  # noqa: N802 - rule-id naming convention
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 3
        for edge in edges:
            assert edge.src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_directive_does_not_chain_upward_through_prior_trailing_comment(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-0100
        #
        # The line above the directive has its own trailing comment (on a
        # statement, not the def). That trailing comment must not extend
        # the directive's block upward either -- the directive's binding to
        # the def below is unaffected by what precedes it.
        src = """x = 1  # a trailing comment on unrelated code
# frob:ticket T-0100
def foo() -> None:
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_directive_separated_from_def_by_non_directive_comment(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-0100
        #
        # A plain (non-frob:) comment directly between a directive and its
        # def is part of the same contiguous comment block, so the
        # directive still binds to the def below.
        src = """# frob:ticket T-0100
# a plain explanatory comment, not a directive
def foo() -> None:
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].src == f"{pf.path}::foo"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_directive_separated_from_def_by_blank_line(self, tmp_path: Path) -> None:
        # frob:ticket T-0100
        #
        # A single blank line between the directive and its def is still
        # within the following-window (2 lines), so it still binds.
        src = """# frob:ticket T-0100

def foo() -> None:
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].src == f"{pf.path}::foo"

    def test_bare_file_when_no_binding(self, tmp_path: Path) -> None:
        src = "# frob:ticket T-0003\n\n\n\n\ndef far_away() -> None:\n    pass\n"
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].src == pf.path

    # frob:tests tests/test_graph.py::TestDsl.test_module_docstring_directive_binds_to_bare_file
    # frob:ticket T-0342
    def test_module_docstring_directive_binds_to_bare_file(
        self, tmp_path: Path
    ) -> None:
        # A `frob:` directive inside a MODULE docstring (not a `#` comment)
        # must still resolve to an edge, bound to the bare file path since
        # no symbol encloses the whole module -- the python walker never
        # scanned docstrings at all before T-0342, so this silently
        # produced zero edges and zero MalformedDirective reports.
        src = '"""Module summary.\n\nfrob:ticket T-0342\n"""\n\ndef foo() -> None:\n    pass\n'
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].kind.value == "ticket"
        assert edges[0].target == "T-0342"
        assert edges[0].src == pf.path

    # frob:tests tests/test_graph.py::TestDsl.test_function_docstring_directive_binds_to_function
    # frob:ticket T-0342
    def test_function_docstring_directive_binds_to_function(
        self, tmp_path: Path
    ) -> None:
        # Same gap, but inside a FUNCTION docstring: the directive must
        # bind to the enclosing function, same as if it had been written
        # as a `#` comment on the first line of the function body.
        src = (
            "def foo() -> None:\n"
            '    """Do the thing.\n'
            "\n"
            '    frob:tests tests/a.py::test_foo kind="unit"\n'
            '    """\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].kind.value == "tests"
        assert edges[0].target == "tests/a.py::test_foo"
        assert edges[0].src == f"{pf.path}::foo"

    # frob:tests tests/test_graph.py::TestDsl.test_invalid_kind_in_module_docstring_is_surfaced_not_silent
    # frob:ticket T-0269
    def test_invalid_kind_in_module_docstring_is_surfaced_not_silent(
        self, tmp_path: Path
    ) -> None:
        # T-0269: once T-0342 makes docstring directives visible, a
        # tests-kind directive carrying an invalid kind value inside a
        # module docstring must surface as a MalformedDirective (which
        # TEST010 then escalates), never a silently-dropped no-op. This is the
        # exact failure the two kind="drift" instances in
        # tests/unit/test_strata_tmlanguage.py and
        # test_extending_guides_complete.py exhibited -- invisible before
        # T-0342, and (had they stayed kind="drift") a silent malformed
        # after it without this coupling being enforced.
        src = (
            '"""Module summary.\n'
            "\n"
            'frob:tests some/target.py::thing kind="drift"\n'
            '"""\n'
            "\n"
            "def foo() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "frob:tests" in malformed[0].reason

    def test_tests_verb_attrs(self, tmp_path: Path) -> None:
        src = """def test_it() -> None:
    # frob:tests src/foo.py::Widget.render kind="e2e"
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert edges[0].attrs["kind"] == "e2e"

    def test_tests_verb_default_kind(self, tmp_path: Path) -> None:
        src = """def test_it() -> None:
    # frob:tests src/foo.py::Widget.render
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].attrs["kind"] == "unit"

    def test_tests_verb_invalid_kind_is_malformed(self, tmp_path: Path) -> None:
        """T-0237: `kind=` must be one of unit/integration/e2e -- a
        misspelled or invented kind (e.g. "drift") never becomes an Edge,
        it degrades to a `MalformedDirective` whose `reason` names the
        `frob:tests` verb literally so `frob.gates._test010_violations` can
        pick it out and report it as a real gate violation (TEST010),
        instead of it staying a silent parse-time warning."""
        src = """def test_it() -> None:
    # frob:tests src/foo.py::Widget.render kind="drift"
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "frob:tests" in malformed[0].reason
        assert "drift" in malformed[0].reason

    def test_unknown_verb_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:bogus target
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert malformed[0].file == pf.path

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_missing_target_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:ticket
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert len(malformed) == 1

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_waive_without_reason_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:waive RULE-1
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert len(malformed) == 1

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_bad_attr_syntax_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:ticket T-1 not-an-attr
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert len(malformed) == 1


class TestMarkdownAnchors:
    def test_describes_edge_with_heading_slug_and_facet(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        text = """# Top Heading

## Lock File

<!-- frob:describes src/frob/graph/lock.py::LockFile body -->
Some text.
"""
        edges = markdown_anchors("docs/modules/graph.md", text)
        assert len(edges) == 1
        edge = edges[0]
        assert edge.src == "docs/modules/graph.md#lock-file"
        assert edge.target == "src/frob/graph/lock.py::LockFile"
        assert edge.attrs["facet"] == "body"

    def test_default_facet_is_sig(self) -> None:
        text = "<!-- frob:describes src/foo.py::bar -->\n"
        edges = markdown_anchors("docs/foo.md", text)
        assert edges[0].attrs["facet"] == "sig"


class TestSlugify:
    def test_lowercases_and_strips_disallowed_punctuation(self) -> None:
        # frob:tests src/frob/graph/dsl.py::slugify kind="unit"
        from frob.graph.dsl import slugify

        assert slugify("The enables cascade") == "the-enables-cascade"
        assert slugify("Public API") == "public-api"
        assert slugify("`DupError`") == "duperror"

    def test_empty_falls_back_to_top(self) -> None:
        from frob.graph.dsl import slugify

        assert slugify("") == "top"

    # frob:ticket T-0212
    @pytest.mark.parametrize(
        ("heading", "expected"),
        [
            # T-0212: GitHub does not collapse punctuation runs to a single
            # `-` the way frob's old slugger did -- it deletes disallowed
            # punctuation outright and turns each remaining space into its
            # own `-`, so runs of spaces (left behind by deleted punctuation)
            # survive as runs of hyphens. These are the exact tricky cases
            # from the T-0212 ticket plus the pilot-repo false positives
            # (docs/guides/agent-playbook.md, tickets.md T-0212).
            ("10.1 DataTable", "101-datatable"),
            ("Output & layouts", "output--layouts"),
            ("Public/Private Boundary", "publicprivate-boundary"),
            ("Hello, World!", "hello-world"),
            ("snake_case_name", "snake_case_name"),
            ("already-hyphenated", "already-hyphenated"),
            ("  leading and trailing  ", "leading-and-trailing"),
            ("Cafe Resume", "cafe-resume"),
            ("100% Done", "100-done"),
            ("C++ vs Rust", "c-vs-rust"),
            ("---", "---"),
        ],
    )
    def test_github_slug_table(self, heading: str, expected: str) -> None:
        # frob:tests src/frob/graph/dsl.py::slugify kind="unit"
        from frob.graph.dsl import slugify

        assert slugify(heading) == expected

    def test_unicode_letters_survive_emoji_are_stripped(self) -> None:
        """Word chars are unicode-aware (accented letters keep), but emoji
        (not \\w) are deleted like other punctuation -- built via chr() to
        stay pure ASCII in the source file (T-0212)."""
        # frob:tests src/frob/graph/dsl.py::slugify kind="unit"
        from frob.graph.dsl import slugify

        e_acute = chr(0xE9)
        heading = "Caf" + e_acute + " R" + e_acute + "sum" + e_acute
        expected = "caf" + e_acute + "-r" + e_acute + "sum" + e_acute
        assert slugify(heading) == expected

        emoji = chr(0x1F389)
        great_job = "Great " + emoji + " Job"
        assert slugify(great_job) == "great--job"

    def test_dedupe_slug_suffixes_repeats(self) -> None:
        # frob:tests src/frob/graph/dsl.py::dedupe_slug kind="unit"
        from frob.graph.dsl import dedupe_slug, slugify

        seen: dict[str, int] = {}
        slugs = [dedupe_slug(slugify(h), seen) for h in ["Usage", "Usage", "Usage"]]
        assert slugs == ["usage", "usage-1", "usage-2"]


class TestBuildIncremental:
    def _tree(self, tmp_path: Path) -> Path:
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(tmp_path, "src/b.py", "def bar() -> None:\n    pass\n")
        return tmp_path

    def test_second_build_is_all_cache_hits(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::build_graph
        root = self._tree(tmp_path)
        cache = root / ".frob" / "cache.db"
        first = build_graph(root, cache).danger_ok
        assert first.stats.parsed == 2
        second = build_graph(root, cache).danger_ok
        assert second.stats.parsed == 0
        assert second.stats.cache_hits == 2

    def test_touching_one_file_reparses_only_it(self, tmp_path: Path) -> None:
        root = self._tree(tmp_path)
        cache = root / ".frob" / "cache.db"
        build_graph(root, cache).danger_ok
        _write(root, "src/a.py", "def foo() -> None:\n    return None\n")
        third = build_graph(root, cache).danger_ok
        assert third.stats.parsed == 1
        assert third.stats.cache_hits == 1

    def test_touch_without_edit_skips_reparse(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::build_graph
        """T-0245: a `touch` that moves a file's mtime but not its content
        must still be reported as a cache hit -- the stat-first fast path
        falls back to a content hash on the stat mismatch, and a hash match
        there must skip the reparse, only refreshing the stored stat."""
        import os
        import time

        root = self._tree(tmp_path)
        cache = root / ".frob" / "cache.db"
        build_graph(root, cache).danger_ok

        target = root / "src" / "a.py"
        st = target.stat()
        time.sleep(0.01)
        os.utime(target, ns=(st.st_atime_ns + 1_000_000, st.st_mtime_ns + 1_000_000))

        second = build_graph(root, cache).danger_ok
        assert second.stats.parsed == 0
        assert second.stats.cache_hits == 2

    def test_fingerprint_bump_rebuilds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/graph/cache.py::_compute_fingerprint
        """T-0243: a cache written under one frob/tree-sitter fingerprint
        must not be silently reused after that fingerprint changes -- a
        stale cache served wrong symbol counts across a real frob upgrade
        (malmberg pilot P3). Simulate the upgrade by bumping the fake
        fingerprint between builds and assert the second build is a cold
        rebuild (parsed == all files), not a cache hit."""
        root = self._tree(tmp_path)
        cache = root / ".frob" / "cache.db"

        monkeypatch.setattr(graph_cache, "_compute_fingerprint", lambda: "frob==0.0.1")
        first = build_graph(root, cache).danger_ok
        assert first.stats.parsed == 2
        assert first.stats.cache_hits == 0

        same_fingerprint = build_graph(root, cache).danger_ok
        assert same_fingerprint.stats.parsed == 0
        assert same_fingerprint.stats.cache_hits == 2

        monkeypatch.setattr(graph_cache, "_compute_fingerprint", lambda: "frob==0.0.2")
        after_upgrade = build_graph(root, cache).danger_ok
        assert after_upgrade.stats.parsed == 2
        assert after_upgrade.stats.cache_hits == 0

    def test_fingerprint_packages_derived_from_lang_registry(self) -> None:
        # frob:tests src/frob/graph/cache.py::_compute_fingerprint
        # frob:waive COV006 reason="T-0536: _FINGERPRINT_PACKAGES is a \
        # module-level tuple computed once at import time (cache.py's top- \
        # level *_NON_LANGUAGE_FINGERPRINT_PACKAGES, \
        # *sorted(GRAMMAR_FINGERPRINT_PACKAGES) expression), not a \
        # function call this test's body could ever name -- the same \
        # module-constant-drift-lock shape as T-0516's tests/test_gates.py \
        # waiver. Retargeting frob:tests directly at the constant instead \
        # was tried and rejected: DRIFT002 then reports it as an \
        # unresolvable edge (module-level assignments are not graph \
        # nodes), trading one false positive for another -- this waiver on \
        # the pre-existing _compute_fingerprint binding is the honest fix."
        """T-0433 (G6 full fix): `_FINGERPRINT_PACKAGES` must contain every
        package `frob.lang.GRAMMAR_FINGERPRINT_PACKAGES` declares -- derived,
        not a second hand-copied tuple that can silently drift from it (the
        exact T-0243/G6 failure mode: a new/changed grammar package serving
        a stale cache under an unchanged fingerprint)."""
        from frob.lang import GRAMMAR_FINGERPRINT_PACKAGES

        assert GRAMMAR_FINGERPRINT_PACKAGES <= set(graph_cache._FINGERPRINT_PACKAGES)
        assert "frob" in graph_cache._FINGERPRINT_PACKAGES
        assert "strata-core" in graph_cache._FINGERPRINT_PACKAGES

    def test_stored_hash_matches_bytes_actually_parsed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/graph/__init__.py::_parse_source_file_fresh
        """T-0433 (G7 fix): the row `build_graph` stores for a reparsed file
        carries `parsed.content_hash` -- the hash of the bytes `frob.lang`
        itself read and parsed -- not a hash the caller read separately
        beforehand. Simulate the old TOCTOU by making the early decision
        hash (`frob.graph._content_hash`) return a value that does NOT
        match what `parse_file` will actually hash; if the fix regressed
        back to storing that stale value, the stored hash would equal the
        deliberately-wrong decision hash instead of the real parsed hash."""
        import frob.graph as graph_mod

        root = self._tree(tmp_path)
        cache = root / ".frob" / "cache.db"

        real_content_hash = graph_mod._content_hash
        monkeypatch.setattr(
            graph_mod, "_content_hash", lambda path: "deliberately-wrong-hash"
        )
        build_graph(root, cache).danger_ok

        conn = sqlite3.connect(cache)
        try:
            stored = dict(
                conn.execute("SELECT path, content_hash FROM files").fetchall()
            )
        finally:
            conn.close()

        real_hash = real_content_hash(root / "src" / "a.py")
        assert stored["src/a.py"] == real_hash
        assert stored["src/a.py"] != "deliberately-wrong-hash"

    def test_cache_hit_build_reports_real_edge_count(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::build_graph
        """T-0218: an all-cache-hit rebuild must report the loaded graph's
        actual edge count, not 0 -- the build summary is always derived from
        `len(snapshot.edges)` (the fully reassembled graph loaded from the
        db), never from a fresh-parse-only counter, so a cache hit must not
        zero it out."""
        root = tmp_path
        _write(
            root,
            "src/a.py",
            '"""Module docstring."""\n\n\n'
            "def foo() -> None:\n"
            "    # frob:doc docs/x.md#foo\n"
            "    pass\n",
        )
        cache = root / ".frob" / "cache.db"
        first = build_graph(root, cache).danger_ok
        assert first.stats.parsed == 1
        assert len(first.edges) > 0

        second = build_graph(root, cache).danger_ok
        assert second.stats.parsed == 0
        assert second.stats.cache_hits == 1
        assert len(second.edges) == len(first.edges)
        assert len(second.edges) > 0


class TestMalformedFileVisibility:
    """T-0216: `malformed=N` in the build summary must never be a dead end --
    every malformed file's path has to be findable in WARN-level output, on
    a fresh parse and on an all-cache-hit rebuild alike."""

    def _tree_with_malformed_directive(self, tmp_path: Path) -> Path:
        _write(tmp_path, "src/good.py", "def foo() -> None:\n    pass\n")
        _write(
            tmp_path,
            "src/bad_directive.py",
            "def broken() -> None:\n    # frob:ticket\n    pass\n",
        )
        return tmp_path

    def test_fresh_build_names_malformed_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        root = self._tree_with_malformed_directive(tmp_path)
        cache = root / ".frob" / "cache.db"
        with caplog.at_level("WARNING"):
            snapshot = build_graph(root, cache).danger_ok
        assert len(snapshot.malformed) == 1
        assert any(
            "src/bad_directive.py" in record.getMessage() for record in caplog.records
        )

    def test_cache_hit_rebuild_still_names_malformed_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        root = self._tree_with_malformed_directive(tmp_path)
        cache = root / ".frob" / "cache.db"
        build_graph(root, cache).danger_ok

        caplog.clear()
        with caplog.at_level("WARNING"):
            snapshot = build_graph(root, cache).danger_ok
        assert snapshot.stats.parsed == 0
        assert len(snapshot.malformed) == 1
        assert any(
            "src/bad_directive.py" in record.getMessage() for record in caplog.records
        )


class TestExclude:
    """`[graph] exclude` in frob.toml is additive to the built-in dir excludes.

    frob:ticket T-0544
    """

    def test_glob_excludes_matching_files(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(tmp_path, "tests/fixtures/bad.py", "def broken(:\n")
        _write(
            tmp_path,
            "frob.toml",
            '[graph]\nexclude = ["tests/fixtures/**"]\n',
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        paths = {rec.id.path for rec in snap.symbols.values()}
        assert "src/a.py" in paths
        assert not any(p.startswith("tests/fixtures/") for p in paths)

    def test_no_config_excludes_nothing_extra(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(tmp_path, "tests/fixtures/b.py", "def bar() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        paths = {rec.id.path for rec in snap.symbols.values()}
        assert "src/a.py" in paths
        assert "tests/fixtures/b.py" in paths

    def test_nested_git_worktree_pruned_without_config(self, tmp_path: Path) -> None:
        """A nested git checkout (own `.git` dir) is pruned by default, with
        no `[graph] exclude` entry needed -- T-0239: `.claude/worktrees/*`
        agent checkouts were walked and parsed wholesale, ~73pct wasted
        work, until pruned before descent."""
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        nested = tmp_path / ".claude" / "worktrees" / "agent-x"
        _write(nested, "src/a.py", "def broken(:\n")
        (nested / ".git").mkdir(parents=True, exist_ok=True)
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        paths = {rec.id.path for rec in snap.symbols.values()}
        assert "src/a.py" in paths
        assert not any(".claude/worktrees" in p for p in paths)

    def test_walk_source_files_prunes_before_descent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_walk_repo_files` never calls `os.walk` into an excluded
        subtree -- directory pruning happens via `dirnames[:]` before the
        walk descends, not by filtering files after a full traversal
        (T-0239's actual perf bug: filtering post-walk still pays the full
        `os.walk`/stat cost of every excluded subtree). T-0245 merged the
        old `_walk_source_files`/`_walk_doc_files` pair into one combined
        walk; this still exercises the source-file half of it."""
        import os as os_mod

        from frob.graph import _walk_repo_files

        _write(tmp_path, "src/a.py", "x = 1\n")
        excluded_dir = tmp_path / "tests" / "fixtures"
        _write(excluded_dir, "deep/deeper/b.py", "y = 2\n")

        visited: list[Path] = []
        real_walk = os_mod.walk

        def _counting_walk(root, *a, **kw):  # noqa: ANN001, ANN002, ANN003
            for dirpath, dirnames, filenames in real_walk(root, *a, **kw):
                visited.append(Path(dirpath))
                yield dirpath, dirnames, filenames

        monkeypatch.setattr("frob.graph.os.walk", _counting_walk)
        found, _docs = _walk_repo_files(tmp_path, exclude_globs=("tests/fixtures/**",))

        found_rel = {p.relative_to(tmp_path).as_posix() for p in found}
        assert found_rel == {"src/a.py"}
        visited_rel = {p.relative_to(tmp_path).as_posix() for p in visited}
        # os.walk must never even enter the excluded subtree's children --
        # if pruning happened only via post-walk file filtering, "tests/fixtures"
        # and its "deep"/"deep/deeper" children would all appear here too.
        assert not any(v.startswith("tests/fixtures") for v in visited_rel if v)

    def test_walk_repo_files_classifies_top_level_readme_as_doc(
        self, tmp_path: Path
    ) -> None:
        """T-0544: a `frob:describes` anchor in README.md (or any other
        top-level *.md note) must be discoverable -- before this fix,
        `_walk_repo_files` only ever classified files under `docs/` as doc
        files, so a repo-root README.md was silently invisible to the
        design graph and its DESCRIBES edge never existed."""
        from frob.graph import _walk_repo_files

        _write(tmp_path, "README.md", "# Title\n")
        _write(tmp_path, "docs/modules/foo.md", "# Foo\n")
        _write(tmp_path, "notes/deep.md", "# Not top-level\n")

        _source, docs = _walk_repo_files(tmp_path)
        docs_rel = {p.relative_to(tmp_path).as_posix() for p in docs}
        assert docs_rel == {"README.md", "docs/modules/foo.md"}


class TestResolve:
    def _snapshot(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/a.py",
            "class Widget:\n    def render(self) -> None:\n        pass\n",
        )
        _write(tmp_path, "src/b.py", "def render() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        return build_graph(tmp_path, cache).danger_ok

    def test_exact_match(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::resolve
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "src/a.py::Widget.render")
        assert result.is_ok
        assert result.danger_ok.id.qualname == "Widget.render"

    def test_suffix_unique_match(self, tmp_path: Path) -> None:
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "Widget.render")
        assert result.is_ok

    def test_exact_qualname_wins_over_suffix_match(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::resolve
        # G10 (T-0402): a bare top-level `render` exactly matches one
        # qualname (`render` in b.py) AND loosely `.endswith`-matches
        # another (`Widget.render` in a.py). Exact qualname matches must be
        # checked -- and win -- strictly before suffix candidates are even
        # pooled in, or this collapses into a false `AmbiguousSymbol`.
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "render")
        assert result.is_ok
        assert result.danger_ok.id.qualname == "render"

    def test_ambiguous_suffix_match(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::resolve
        # Genuine ambiguity: two DIFFERENT symbols both suffix-match a bare
        # `render`, and neither is an exact qualname hit (no top-level
        # `render` here) -- this must still be `AmbiguousSymbol`,
        # distinguishing "exact wins" (G10) from "suffix matching stops
        # detecting real ambiguity".
        _write(
            tmp_path,
            "src/a.py",
            "class Widget:\n    def render(self) -> None:\n        pass\n",
        )
        _write(
            tmp_path,
            "src/c.py",
            "class Other:\n    def render(self) -> None:\n        pass\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        result = resolve(snap, "render")
        assert result.is_err
        assert result.danger_err == GraphError.AmbiguousSymbol

    def test_unknown(self, tmp_path: Path) -> None:
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "nonexistent")
        assert result.is_err
        assert result.danger_err == GraphError.UnknownSymbol


class TestEdgesFromTo:
    def test_edges_from_and_to(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::edges_from
        # frob:tests src/frob/graph/__init__.py::edges_to
        _write(
            tmp_path,
            "src/a.py",
            "def foo() -> None:\n    # frob:uses-contract src/a.py::bar\n    pass\n\n\ndef bar() -> None:\n    pass\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        src_ref = "src/a.py::foo"
        target_ref = "src/a.py::bar"
        assert len(edges_from(snap, src_ref)) == 1
        assert len(edges_to(snap, target_ref)) == 1


class TestLoadGraph:
    def test_cache_stale_after_edit(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    return None\n")
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheStale

    def test_cache_corrupt_on_garbage(self, tmp_path: Path) -> None:
        cache = tmp_path / ".frob" / "cache.db"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"not a sqlite database at all, definitely garbage bytes")
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

    def test_cache_corrupt_when_missing(self, tmp_path: Path) -> None:
        result = load_graph(tmp_path / ".frob" / "cache.db")
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

    def test_touch_without_edit_is_not_stale(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        """T-0245: a `touch` that moves mtime without changing content must
        not report CacheStale -- load_graph's stat-first check falls back to
        a full content hash on any stat mismatch, and a hash match there
        must still count as fresh."""
        import os
        import time

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok

        target = tmp_path / "src" / "a.py"
        st = target.stat()
        time.sleep(0.01)
        os.utime(target, ns=(st.st_atime_ns + 1_000_000, st.st_mtime_ns + 1_000_000))

        result = load_graph(cache)
        assert result.is_ok

    def test_load_graph_success_returns_snapshot(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        # The happy path: an unmodified cache loads back to an Ok snapshot
        # carrying the built symbols (exercises the load_all + Ok tail).
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        result = load_graph(cache)
        assert result.is_ok
        assert "src/a.py::foo" in result.danger_ok.symbols

    def test_load_graph_never_built_root_is_corrupt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        # A cache that opens read-only but has no recorded root (get_root ->
        # None) is CacheCorrupt -- "never been built".
        import frob.graph as graph_mod

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        monkeypatch.setattr(graph_mod._cache, "get_root", lambda conn: None)
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

    def test_load_graph_get_root_query_error_is_corrupt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        # Corrupt bytes can surface as a query-time DatabaseError inside
        # get_root (not at connect) -- still CacheCorrupt, connection closed.
        import sqlite3

        import frob.graph as graph_mod

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok

        def _boom(conn: object) -> str:
            raise sqlite3.DatabaseError("simulated query-time corruption")

        monkeypatch.setattr(graph_mod._cache, "get_root", _boom)
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

    def test_load_graph_connect_readonly_failure_is_corrupt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        # If the read-only connection itself cannot be opened (locked, ACL,
        # OS error), that is CacheCorrupt -- the connect-time except branch,
        # distinct from a query-time get_root failure.
        import frob.graph as graph_mod

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok

        def _fail(_c: Path) -> object:
            raise OSError("simulated read-only open failure")

        monkeypatch.setattr(graph_mod._cache, "connect_readonly", _fail)
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

    def test_cache_stale_after_new_file_added(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        # G1 (T-0402): a file added since the last build has no cache row
        # to hash-compare against, so the old `_first_stale_cached_file`
        # loop (which only iterates rows already IN `files`) could never
        # see it -- `load_graph` returned `Ok` on a snapshot silently
        # missing the new file's obligations. Reverting the
        # `_first_added_file` check in `load_graph` makes this assert
        # `is_ok` instead.
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        _write(tmp_path, "src/b.py", "def bar() -> None:\n    pass\n")
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheStale

    def test_cache_stale_after_new_doc_added(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        # Same as above (G1) but for a newly-added doc file under docs/,
        # the other file class `load_graph` must catch as an addition.
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        _write(tmp_path, "docs/new.md", "# New\n")
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheStale

    def test_non_utf8_doc_file_is_skipped_not_crashed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::build_graph
        # G2 (T-0402): UnicodeDecodeError subclasses ValueError, not
        # OSError, so `_process_doc_file`'s `except OSError` never caught
        # it -- one non-UTF-8 .md file crashed the whole `build_graph` call
        # (and everything layered on its `Result` contract, uncaught).
        # Reverting the `(OSError, UnicodeDecodeError)` catch makes this
        # raise `UnicodeDecodeError` instead of returning `Ok`.
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "bad.md").write_bytes(b"\xff\xfeheading\n")
        cache = tmp_path / ".frob" / "cache.db"
        result = build_graph(tmp_path, cache)
        assert result.is_ok
        assert "src/a.py::foo" in result.danger_ok.symbols

    # frob:invariant INV-003
    # invariant spec: [INV-003](invariants/INV-003.md)
    def test_deleted_cache_is_rebuildable_from_source(self, tmp_path: Path) -> None:
        """Deleting `.frob/cache.db` entirely is equivalent to a fresh build."""
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        cache.unlink()
        rebuilt = build_graph(tmp_path, cache)
        assert rebuilt.is_ok
        assert "src/a.py::foo" in rebuilt.danger_ok.symbols


# frob:ticket T-0141
class TestCorruptCacheRecovery:
    # frob:ticket T-0141
    # frob:tests src/frob/graph/cache.py::connect
    def test_garbage_cache_file_is_recreated(self, tmp_path):
        """T-0019 / INV-003: a cache.db that is not sqlite at all must not
        crash build_graph -- the derived cache is deleted and rebuilt.

        T-0141: also seeds orphaned `-wal`/`-shm` sidecars next to the
        garbage file and asserts `_recreate` cleans those up too, not just
        the main db file -- otherwise every corrupt-cache recovery leaks
        two more files that nothing else ever removes."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "m.py").write_text("def f():\n    return 1\n")
        cache = root / ".frob" / "cache.db"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"this is not a sqlite database at all")
        wal = cache.with_name(cache.name + "-wal")
        shm = cache.with_name(cache.name + "-shm")
        wal.write_bytes(b"stale wal")
        shm.write_bytes(b"stale shm")

        result = build_graph(root, cache)
        assert result.is_ok, result.err
        assert any("m.py" in ref for ref in result.danger_ok.symbols)
        assert not wal.exists()
        assert not shm.exists()

    # frob:ticket T-0141
    # frob:tests src/frob/graph/cache.py::connect
    def test_truncated_sqlite_header_is_recreated(self, tmp_path):
        """T-0141: a real sqlite file truncated mid-header (valid magic
        prefix, no page data) must recover the same way as pure garbage."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "m.py").write_text("def f():\n    return 1\n")
        cache = root / ".frob" / "cache.db"
        cache.parent.mkdir(parents=True)
        conn = sqlite3.connect(str(cache))
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()
        # Truncate to just the sqlite magic header -- no page 1 body, no
        # btree data at all.
        header = cache.read_bytes()[:16]
        cache.write_bytes(header)

        result = build_graph(root, cache)
        assert result.is_ok, result.err
        assert any("m.py" in ref for ref in result.danger_ok.symbols)

    # frob:ticket T-0141
    # frob:tests src/frob/graph/cache.py::connect
    def test_ddl_failure_after_connect_probe_passes_is_recovered(self, tmp_path):
        """T-0141: on py3.12, a db can look readable to connect()'s own
        probes (SELECT 1 never touches a table's btree page) and only fail
        once _apply_schema's DROP TABLE actually reads the damaged page.
        Reproduced deterministically here by corrupting the `meta` table's
        page in-place while leaving the sqlite header (page 1) intact, so
        `SELECT 1` succeeds but any DDL touching `meta` raises
        DatabaseError -- this must still recover, not crash."""
        cache = tmp_path / "cache.db"
        conn = sqlite3.connect(str(cache))
        conn.execute("PRAGMA page_size=4096")
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('schema_version', '99')")
        rootpage = conn.execute(
            "SELECT rootpage FROM sqlite_master WHERE name = 'meta'"
        ).fetchone()[0]
        conn.commit()
        conn.close()

        page_size = 4096
        data = bytearray(cache.read_bytes())
        start = (rootpage - 1) * page_size
        for i in range(start, start + page_size):
            data[i] = 0xFF
        cache.write_bytes(bytes(data))

        # SELECT 1 must still succeed -- confirms this exercises the
        # DDL-failure path in _apply_schema, not the earlier probe.
        probe = sqlite3.connect(str(cache))
        probe.execute("SELECT 1")
        probe.close()

        conn = graph_cache.connect(cache)
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
        finally:
            conn.close()
        assert row is not None and row[0] == str(graph_cache._SCHEMA_VERSION)


class TestDuplicateSymrefs:
    # frob:tests src/frob/graph/__init__.py::build_graph
    def test_overload_and_property_setter_do_not_crash(self, tmp_path):
        """T-0024: @overload chains and property/setter pairs legally repeat
        a qualname in one file; last definition wins, never a crash."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "m.py").write_text(
            "from typing import overload\n\n"
            "@overload\n"
            "def f(x: int) -> int: ...\n"
            "@overload\n"
            "def f(x: str) -> str: ...\n"
            "def f(x):\n"
            "    return x\n\n"
            "class C:\n"
            "    @property\n"
            "    def v(self):\n"
            "        return self._v\n"
            "    @v.setter\n"
            "    def v(self, value):\n"
            "        self._v = value\n",
            encoding="utf-8",
        )
        result = build_graph(root, root / ".frob" / "cache.db")
        assert result.is_ok, result.err
        snap = result.danger_ok
        assert "src/m.py::f" in snap.symbols
        assert "src/m.py::C.v" in snap.symbols


class TestCacheModule:
    """Direct exercise of frob.graph.cache's row-level read/write primitives
    (build_graph/load_graph exercise them transitively, but each function
    gets its own assertion here per docs/modules/graph.md's Cache section)."""

    def test_set_root_and_get_root_roundtrip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/cache.py::set_root
        # frob:tests src/frob/graph/cache.py::get_root
        from frob.graph import cache as _cache

        conn = _cache.connect(tmp_path / ".frob" / "cache.db")
        try:
            assert _cache.get_root(conn) is None
            _cache.set_root(conn, "/repo/root")
            conn.commit()
            assert _cache.get_root(conn) == "/repo/root"
        finally:
            conn.close()

    def test_store_and_load_file_data_roundtrip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/cache.py::store_file_data
        # frob:tests src/frob/graph/cache.py::load_file_data
        # frob:tests src/frob/graph/cache.py::get_file_hash
        # frob:tests src/frob/graph/cache.py::load_all
        from frob.graph import cache as _cache
        from frob.graph._models import Digests, Edge, EdgeKind, SymbolId, SymbolRecord
        from frob.lang import SymbolKind

        conn = _cache.connect(tmp_path / ".frob" / "cache.db")
        try:
            _cache.set_root(conn, str(tmp_path))
            record = SymbolRecord(
                id=SymbolId(path="src/a.py", qualname="foo"),
                kind=SymbolKind.FUNCTION,
                public=True,
                digests=Digests(sig="s", body="b", doc="d"),
                span=(1, 3),
            )
            edge = Edge(
                src="src/a.py::foo",
                kind=EdgeKind.TICKET,
                target="T-0001",
                origin="src/a.py:1",
            )
            assert _cache.get_file_hash(conn, "src/a.py") is None
            _cache.store_file_data(
                conn,
                file_path="src/a.py",
                content_hash="deadbeef",
                symbols=(record,),
                edges=(edge,),
                malformed=(),
            )
            conn.commit()

            assert _cache.get_file_hash(conn, "src/a.py") == "deadbeef"

            symbols, edges, malformed = _cache.load_file_data(conn, "src/a.py")
            assert symbols == (record,)
            assert edges == (edge,)
            assert malformed == ()

            snapshot = _cache.load_all(conn)
            assert snapshot.root == str(tmp_path)
            assert "src/a.py::foo" in snapshot.symbols
            assert snapshot.file_hashes["src/a.py"] == "deadbeef"
        finally:
            conn.close()

    def test_get_file_meta_and_touch_file_stat(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/cache.py::get_file_meta
        # frob:tests src/frob/graph/cache.py::touch_file_stat
        """T-0245: get_file_meta returns the stored (content_hash, mtime_ns,
        size) stat pair, and touch_file_stat can refresh just the stat
        (a `touch` with no real edit) without disturbing the content hash or
        the symbols/edges/malformed rows already stored for the file."""
        from frob.graph import cache as _cache

        conn = _cache.connect(tmp_path / ".frob" / "cache.db")
        try:
            assert _cache.get_file_meta(conn, "src/a.py") is None
            _cache.store_file_data(
                conn,
                file_path="src/a.py",
                content_hash="deadbeef",
                mtime_ns=100,
                size=42,
                symbols=(),
                edges=(),
                malformed=(),
            )
            conn.commit()
            assert _cache.get_file_meta(conn, "src/a.py") == ("deadbeef", 100, 42)

            _cache.touch_file_stat(conn, "src/a.py", mtime_ns=200, size=42)
            conn.commit()
            assert _cache.get_file_meta(conn, "src/a.py") == ("deadbeef", 200, 42)
            # content hash is untouched by a stat-only refresh
            assert _cache.get_file_hash(conn, "src/a.py") == "deadbeef"
        finally:
            conn.close()

    # frob:ticket T-0279
    def test_tests_edge_direction_agrees_fresh_parse_vs_cache_roundtrip(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # frob:tests src/frob/graph/cache.py::store_file_data
        # frob:tests src/frob/graph/cache.py::load_file_data
        """T-0279: a `frob:tests` directive's `src`/`target` endpoints must
        mean the same thing whether read from a fresh `dsl.parse_directives`
        call or read back from `cache.py`'s store/load round-trip -- a
        direction disagreement between the two would silently flip which
        side is the test and which is the source (T-0137's either-direction
        convention depends on both paths agreeing).

        Writes ONE source file with a `frob:tests` directive placed above
        the SOURCE symbol (this repo's `_conform.py`/`_generate.py`
        convention: `src`=source, `target`=test), parses it fresh, then
        stores that exact edge through `cache.store_file_data` and reads it
        back via `cache.load_file_data` -- the src/target pair must come
        back byte-identical, proving the cache is a pure passthrough with
        no direction transform in either direction.
        """
        root = tmp_path / "repo"
        path = _write(
            root,
            "src/pkg/mod.py",
            '"""Module."""\n\n\n'
            "# frob:tests tests/test_mod.py::TestWidget.test_helper "
            'kind="unit"\n'
            "def helper(x: int) -> int:\n"
            '    """Helper."""\n'
            "    return x + 1\n",
        )
        parsed = parse_file(path).danger_ok
        fresh_edges, malformed = parse_directives(parsed)
        assert malformed == ()
        tests_edges = [e for e in fresh_edges if e.kind.value == "tests"]
        assert len(tests_edges) == 1
        fresh_edge = tests_edges[0]
        # Source-side convention: src is the source symbol, target names
        # the covering test.
        assert fresh_edge.src == f"{parsed.path}::helper"
        assert fresh_edge.target == "tests/test_mod.py::TestWidget.test_helper"

        conn = graph_cache.connect(tmp_path / ".frob" / "cache.db")
        try:
            graph_cache.store_file_data(
                conn,
                file_path=parsed.path,
                content_hash="deadbeef",
                symbols=(),
                edges=(fresh_edge,),
                malformed=(),
            )
            conn.commit()
            _symbols, cached_edges, _malformed = graph_cache.load_file_data(
                conn, parsed.path
            )
        finally:
            conn.close()
        assert len(cached_edges) == 1
        cached_edge = cached_edges[0]
        # Cache round-trip must not swap or otherwise transform src/target
        # -- the direction a fresh parse produces is the direction the
        # cache must serve back, always.
        assert cached_edge.src == fresh_edge.src
        assert cached_edge.target == fresh_edge.target

    # frob:ticket T-0279
    def test_schema_version_mismatch_wipes_derived_rows(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/cache.py::connect
        """T-0279: a cache.db written under an OLDER `_SCHEMA_VERSION` (e.g.
        one predating a src/target semantic fix in dsl.py/gates.py, the
        T-0279 scenario) must never be served as-is -- `connect` must wipe
        every derived row and force a full reparse on the next build,
        exactly as it already does for a genuine table-shape change."""
        from frob.graph import cache as _cache
        from frob.graph._models import Digests, SymbolId, SymbolRecord
        from frob.lang import SymbolKind

        cache_path = tmp_path / ".frob" / "cache.db"
        conn = _cache.connect(cache_path)
        record = SymbolRecord(
            id=SymbolId(path="src/a.py", qualname="foo"),
            kind=SymbolKind.FUNCTION,
            public=True,
            digests=Digests(sig="s", body="b", doc="d"),
            span=(1, 3),
        )
        _cache.store_file_data(
            conn,
            file_path="src/a.py",
            content_hash="deadbeef",
            symbols=(record,),
            edges=(),
            malformed=(),
        )
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', '0') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )
        conn.commit()
        conn.close()

        reopened = _cache.connect(cache_path)
        try:
            assert _cache.get_file_hash(reopened, "src/a.py") is None
            symbols, edges, malformed = _cache.load_file_data(reopened, "src/a.py")
            assert symbols == ()
            assert edges == ()
            assert malformed == ()
        finally:
            reopened.close()

    # frob:ticket T-0232
    def test_connect_readonly_rejects_writes_no_lock_contention(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/cache.py::connect_readonly
        """`connect_readonly` (T-0232) must (1) reject writes outright and
        (2) succeed immediately against a db another connection is mid-write
        on -- the two properties that make it safe for `load_graph` to use
        without contending for sqlite's single writer slot."""
        import time

        from frob.graph import cache as _cache

        cache_path = tmp_path / ".frob" / "cache.db"
        _cache.connect(cache_path).close()  # initialize schema once

        ro_conn = _cache.connect_readonly(cache_path)
        try:
            with pytest.raises(sqlite3.OperationalError):
                ro_conn.execute("INSERT INTO meta (key, value) VALUES ('x', 'y')")

            writer = _cache.connect(cache_path)
            writer.execute("INSERT INTO meta (key, value) VALUES ('a', 'held')")
            try:
                start = time.monotonic()
                row = ro_conn.execute(
                    "SELECT value FROM meta WHERE key = 'schema_version'"
                ).fetchone()
                elapsed = time.monotonic() - start
            finally:
                writer.rollback()
                writer.close()
            assert row is not None
            assert elapsed < 5.0
        finally:
            ro_conn.close()


class TestConcurrentCache:
    # frob:ticket T-0029
    def test_concurrent_connections_do_not_raise_disk_io(self, tmp_path):
        # frob:ticket T-0029
        # frob:tests src/frob/graph/cache.py::connect
        """T-0029: two connections writing the same cache.db must serialize on
        WAL + the busy timeout, not raise `sqlite3.OperationalError: disk I/O
        error` (the hard crash a second `frob graph build` process hit).

        This pins the connection-lock fix specifically. Full race-free
        concurrent build_graph on one cache (overlapping schema rebuilds and
        per-file commits) is broader work tracked in T-0029's body -- it wants
        a build lockfile, not just a busy timeout."""
        from concurrent.futures import ThreadPoolExecutor

        from frob.graph import cache as _cache

        cache_path = tmp_path / ".frob" / "cache.db"
        _cache.connect(cache_path).close()  # initialize schema once

        def writer(n: int) -> bool:
            conn = _cache.connect(cache_path)
            try:
                for i in range(20):
                    _cache.set_root(conn, f"root-{n}-{i}")
                    conn.commit()
                return True
            finally:
                conn.close()

        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(writer, n) for n in range(4)]
            assert all(f.result() for f in futures)

    # frob:ticket T-0232
    def test_connect_on_current_schema_does_not_block_on_a_held_write_lock(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/cache.py::connect
        """T-0232: `connect()` on an already-initialized, current-schema db
        must not itself take a write lock -- `_apply_schema` used to run
        `CREATE TABLE IF NOT EXISTS` unconditionally on every connect, and
        sqlite always treats DDL as a write regardless of whether it
        changes anything. That meant every read-only caller (e.g.
        `load_graph`, or a concurrent gate job) queued behind any other
        process's write transaction on this same db, even though it had no
        actual data to write. Pin the fix: a second connection to a db
        already at the current schema version must return promptly while a
        different connection is mid-write (holds an uncommitted insert),
        instead of blocking for anywhere near the 30s busy timeout."""
        import time
        from concurrent.futures import ThreadPoolExecutor

        from frob.graph import cache as _cache

        cache_path = tmp_path / ".frob" / "cache.db"
        _cache.connect(cache_path).close()  # initialize schema once, up front

        writer_conn = _cache.connect(cache_path)
        writer_conn.execute(
            "INSERT INTO meta (key, value) VALUES ('probe', 'held')"
        )  # uncommitted: holds sqlite's write lock until commit/rollback

        def reader() -> float:
            start = time.monotonic()
            conn = _cache.connect(cache_path)
            conn.close()
            return time.monotonic() - start

        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                elapsed = ex.submit(reader).result(timeout=25)
        finally:
            writer_conn.rollback()
            writer_conn.close()

        assert elapsed < 5.0, (
            f"connect() took {elapsed:.2f}s against a current-schema db with "
            "an unrelated write in progress -- it should not need the write "
            "lock at all"
        )


def test_graph_build_lock_drift_integration(tmp_path: Path) -> None:
    # frob:tests src/frob/graph kind="integration"
    # Exercises the graph pipeline end to end: build_graph parses + digests a
    # source file into the sqlite cache, acknowledge writes a lock, and drift
    # (with the lock module) reports staleness once the source digest moves.
    from frob.graph.lock import acknowledge, drift, load_lock, write_lock

    cache = tmp_path / ".frob" / "cache.db"
    _write(tmp_path, "widget.py", _BASE_PY)
    snapshot = build_graph(tmp_path, cache).danger_ok
    ref = "widget.py::Widget.render"
    assert ref in snapshot.symbols

    lock = load_lock(tmp_path / "frob.lock").danger_ok
    acked = acknowledge(lock, snapshot, [ref]).danger_ok
    assert write_lock(acked, tmp_path / "frob.lock").is_ok
    assert drift(acked, snapshot).stale == ()

    # change the render signature; drift must now flag the acked ref (sig
    # facet) as stale
    _write(
        tmp_path,
        "widget.py",
        _BASE_PY.replace(
            "def render(self, value: int) -> str:",
            "def render(self, value: int, extra: int = 0) -> str:",
        ),
    )
    cache.unlink()
    snapshot2 = build_graph(tmp_path, cache).danger_ok
    report = drift(acked, snapshot2)
    assert any(item.entry.ref == ref for item in report.stale)


class TestGeneratedSource:
    """`frob.graph._generated.is_generated_source` (T-0234)."""

    def test_is_generated_source_detects_repo_convention_header(
        self, tmp_path: Path
    ) -> None:
        from frob.graph._generated import is_generated_source

        _write(
            tmp_path,
            "src/a.py",
            "# generated by: frob exports src/a\ndef helper(x):\n    return x\n",
        )
        assert is_generated_source(tmp_path, "src/a.py") is True

    def test_is_generated_source_detects_do_not_edit_and_at_markers(
        self, tmp_path: Path
    ) -> None:
        from frob.graph._generated import is_generated_source

        _write(
            tmp_path,
            "src/b.ts",
            "// Code generated by protoc-gen-go. DO NOT EDIT.\nexport const x = 1;\n",
        )
        _write(tmp_path, "src/c.ts", "// @generated\nexport const y = 1;\n")
        assert is_generated_source(tmp_path, "src/b.ts") is True
        assert is_generated_source(tmp_path, "src/c.ts") is True

    def test_is_generated_source_false_for_hand_authored_file(
        self, tmp_path: Path
    ) -> None:
        from frob.graph._generated import is_generated_source

        _write(tmp_path, "src/d.py", '"""A hand-written module."""\n\nx = 1\n')
        assert is_generated_source(tmp_path, "src/d.py") is False

    def test_is_generated_source_false_for_missing_file(self, tmp_path: Path) -> None:
        from frob.graph._generated import is_generated_source

        assert is_generated_source(tmp_path, "src/does_not_exist.py") is False
