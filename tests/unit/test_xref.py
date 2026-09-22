import pytest

from frob.xref import XrefError, xref


@pytest.fixture
def py_file(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    return p


@pytest.fixture
def cpp_file(tmp_path, cpp_sample):
    p = tmp_path / "sample.cpp"
    p.write_bytes(cpp_sample)
    return p


@pytest.fixture
def py_dir(tmp_path, py_sample):
    """Two Python files: one defines helper, one calls it."""
    (tmp_path / "defn.py").write_bytes(py_sample)
    (tmp_path / "caller.py").write_text(
        "from defn import helper\n\nresult = helper(42)\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Python xref
# ---------------------------------------------------------------------------


def test_py_finds_definition(py_file):
    result = xref("helper", py_file)
    assert result.is_ok
    xr = result.danger_ok
    assert xr.definition is not None
    assert "sample.py" in xr.definition.file


def test_py_definition_correct_line(py_file, py_sample):
    xr = xref("helper", py_file).danger_ok
    src_lines = py_sample.decode().splitlines()
    assert xr.definition is not None
    assert src_lines[xr.definition.line - 1].startswith("def helper")


def test_py_finds_class_definition(py_file):
    xr = xref("MyClass", py_file).danger_ok
    assert xr.definition is not None


def test_py_usages_include_calls(py_dir):
    xr = xref("helper", py_dir).danger_ok
    files_with_usage = {u.file for u in xr.usages}
    assert any("caller.py" in f for f in files_with_usage)


def test_py_usage_context_is_line_text(py_dir):
    xr = xref("helper", py_dir).danger_ok
    caller_usages = [u for u in xr.usages if "caller.py" in u.file]
    assert any("helper" in u.context for u in caller_usages)


def test_py_missing_symbol_no_definition(py_file):
    xr = xref("nonexistent_symbol_xyz", py_file).danger_ok
    assert xr.definition is None
    assert xr.usages == []


# ---------------------------------------------------------------------------
# C++ xref
# ---------------------------------------------------------------------------


def test_cpp_finds_definition(cpp_file):
    xr = xref("helper", cpp_file).danger_ok
    assert xr.definition is not None


def test_cpp_finds_class(cpp_file):
    xr = xref("Engine", cpp_file).danger_ok
    assert xr.definition is not None or len(xr.usages) > 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_no_files_found(tmp_path):
    result = xref("foo", tmp_path)
    assert result.is_err
    assert result.danger_err == XrefError.NoFilesFound


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


# frob:tests src/frob/xref/__init__.py::XrefResult.as_text
def test_as_text(py_file):
    xr = xref("helper", py_file).danger_ok
    text = xr.as_text()
    assert "helper" in text
    assert "defined" in text


def test_as_json(py_file):
    import json

    xr = xref("helper", py_file).danger_ok
    data = json.loads(xr.as_json())
    assert data["symbol"] == "helper"
    assert "definition" in data


def test_as_text_no_definition_no_usages(py_file):
    # frob:tests src/frob/xref/__init__.py::XrefResult.as_text kind="unit"
    # `definition is None` and empty `usages` exercise as_text's
    # "(not found)"/"(none found)" branches, neither of which
    # test_as_text (a found-definition, has-usages case) reaches.
    xr = xref("nonexistent_symbol_xyz", py_file).danger_ok
    text = xr.as_text()
    assert "defined:  (not found)" in text
    assert "used by: (none found)" in text


def test_as_text_cross_file_filters_and_reports_skipped(tmp_path):
    # frob:tests src/frob/xref/__init__.py::XrefResult.as_text kind="unit"
    # `cross_file=True` exercises the same-file-usage filtering branch and
    # the "N same-file usages hidden" skipped-count branch -- both
    # unreached by the default (cross_file=False) rendering path.
    (tmp_path / "defn.py").write_text(
        "def helper(x):\n    return x\n\nresult = helper(1)\n"
    )
    (tmp_path / "caller.py").write_text(
        "from defn import helper\n\nresult = helper(42)\n"
    )
    xr = xref("helper", tmp_path).danger_ok
    default_text = xr.as_text()
    cross_text = xr.as_text(cross_file=True)
    assert "used by:" in default_text
    assert "used by (cross-file):" in cross_text
    # defn.py both defines and calls helper in its own body, so filtering
    # same-file usages should report at least one hidden.
    assert "same-file usages hidden" in cross_text


# ---------------------------------------------------------------------------
# Non-tree-sitter (text-search) files and hidden-path skipping (T-1312)
# ---------------------------------------------------------------------------


def test_text_search_finds_usages_in_strata_file(tmp_path):
    # frob:tests src/frob/xref/__init__.py::xref kind="unit"
    # `.strata` is a known extension but not in `_SOURCE_EXTS`, so it
    # routes through `_search_text` (plain substring scan) instead of
    # `_search_parsed` -- exercising a code path none of the .py/.cpp
    # tests above reach at all. `_search_text` never yields a definition
    # (it has no symbol-kind awareness), only usages.
    f = tmp_path / "spec.strata"
    f.write_text("widget defines the widget contract\nuse widget here\n")
    xr = xref("widget", f).danger_ok
    assert xr.definition is None
    assert {u.line for u in xr.usages} == {1, 2}


# frob:ticket T-3941
def test_definition_and_usage_file_fields_are_posix_style(tmp_path):
    # frob:tests src/frob/xref/__init__.py::xref kind="unit"
    """T-3941 MUST-STAY-TRUE contract: `Definition.file`/`Usage.file` are
    always forward-slash-separated, regardless of platform. This is the
    exact field `profile_boundary_gate` (PROFILE001) compared against
    forward-slash literals (`_SRC_PREFIX`, `_PROFILE_BOUNDARY_ALLOWED_
    FILES`) -- `str(a_relative_WindowsPath)` uses backslashes, which
    made every such comparison silently fail and PROFILE001 return `()`
    unconditionally on Windows. A nested directory is required to prove
    anything here: a single-component relative path has no separator at
    all to get wrong, so `py_file`'s own top-level fixture could not
    have caught this."""
    nested = tmp_path / "pkg" / "sub"
    nested.mkdir(parents=True)
    (nested / "defn.py").write_text("def helper():\n    pass\n")
    (nested / "caller.py").write_text(
        "from defn import helper\n\nresult = helper(42)\n"
    )

    xr = xref("helper", tmp_path).danger_ok

    assert xr.definition is not None
    assert xr.definition.file == "pkg/sub/defn.py"
    assert "\\" not in xr.definition.file
    assert xr.usages, "expected at least one usage across the nested tree"
    for usage in xr.usages:
        assert usage.file.startswith("pkg/sub/")
        assert "\\" not in usage.file


def test_collect_source_files_skips_hidden_directory(tmp_path):
    # frob:tests src/frob/xref/__init__.py::xref kind="unit"
    # A dot-prefixed directory exercises `_collect_source_files`'s
    # `_is_hidden` skip branch -- the file inside it must never surface
    # as a definition or usage even though its extension matches.
    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "secret.py").write_text("def helper():\n    pass\n")
    (tmp_path / "visible.py").write_text("def other():\n    pass\n")
    # An extension xref does not collect at all (`_collect_source_files`'s
    # own "wrong extension -- continue" branch, distinct from the
    # hidden-directory skip this test is otherwise about).
    (tmp_path / "notes.txt").write_text("helper mentioned here\n")
    xr = xref("helper", tmp_path).danger_ok
    assert xr.definition is None
    assert xr.usages == []


# ---------------------------------------------------------------------------
# C# xref (T-3232: frob.xref now routes every frob.lang tree-sitter
# language, csharp included, through the same parsed-symbol resolver
# python and cpp already used -- previously csharp fell through to the
# cruder plain-text fallback since `_SOURCE_EXTS`/`_LANG_EXTS` only knew
# about python/c/cpp/strata.)
# ---------------------------------------------------------------------------


@pytest.fixture
def csharp_file():
    """Static, checked-in fixture (T-3232): a namespaced public class
    (`Frob.Sample.Widget`) whose `Render` method calls its own `Add`
    method -- gives xref a same-file definition-plus-usage pair without
    a hand-authored fixture."""
    from pathlib import Path

    return Path(__file__).parent.parent / "fixtures" / "lang" / "sample.cs"


def test_csharp_finds_definition_and_usage(csharp_file):
    result = xref("Add", csharp_file)
    assert result.is_ok
    xr = result.danger_ok
    assert xr.definition is not None
    assert xr.definition.file.endswith("sample.cs")
    assert xr.usages, "expected the Render() call site to surface as a usage"
    assert any("Add(label)" in u.context for u in xr.usages)


def test_csharp_finds_definition_and_usage_with_explicit_lang(csharp_file):
    # T-3232: `--lang csharp` (frob.xref's `_LANG_EXTS`) previously had no
    # csharp entry at all, so this filtered to zero files.
    result = xref("Add", csharp_file, lang="csharp")
    assert result.is_ok
    xr = result.danger_ok
    assert xr.definition is not None
    assert xr.usages


@pytest.fixture
def csharp_nested_file():
    # frob:ticket T-4519
    """Static fixture (T-4519): a namespaced class with a nested type, a
    property, a const field, and an event -- see the fixture's own
    module comment for why the event is included but not asserted as
    found."""
    from pathlib import Path

    return (
        Path(__file__).parent.parent
        / "fixtures"
        / "lang"
        / "csharp"
        / "nested_property_event.cs"
    )


# frob:waive DUP002 reason="T-4519: property vs nested-type lookups share the \
# xref()-call/assert shape by design -- one exercises SymbolKind.CONST via a \
# property_declaration, the other SymbolKind.CLASS via a nested type; each proves a \
# distinct _DEFINITION_KINDS branch, not a copy-paste"
def test_csharp_finds_property_definition(csharp_nested_file):
    # frob:tests tests/unit/test_xref.py::test_csharp_finds_property_definition
    # frob:ticket T-4519
    # T-4519: `Total` is a `property_declaration`, mapped by
    # `_walk_csharp._cs_property_symbol` onto `SymbolKind.CONST` -- before
    # widening `_DEFINITION_KINDS` (this ticket), CONST-kind symbols were
    # never candidate definitions and this lookup returned None.
    result = xref("Total", csharp_nested_file, lang="csharp")
    assert result.is_ok
    xr = result.danger_ok
    assert xr.definition is not None
    assert xr.definition.file.endswith("nested_property_event.cs")


def test_csharp_finds_const_field_definition(csharp_nested_file):
    # frob:tests tests/unit/test_xref.py::test_csharp_finds_const_field_definition  # noqa: E501
    # frob:ticket T-4519
    # T-4519: `MaxTotal` is a `const`-modified field, also SymbolKind.CONST.
    result = xref("MaxTotal", csharp_nested_file, lang="csharp")
    assert result.is_ok
    assert result.danger_ok.definition is not None


def test_csharp_finds_nested_type_definition(csharp_nested_file):
    # frob:tests tests/unit/test_xref.py::test_csharp_finds_nested_type_definition  # noqa: E501
    # frob:ticket T-4519
    # T-4519: `Inner` is a class nested inside `Container` (qualname
    # `Frob.Sample.Nested.Container.Inner`) -- `_parsed_definition`
    # matches on the bare rightmost name component, so nesting depth
    # (already exercised by namespace qualification in `sample.cs`) does
    # not need a `_DEFINITION_KINDS` change to resolve here.
    result = xref("Inner", csharp_nested_file, lang="csharp")
    assert result.is_ok
    xr = result.danger_ok
    assert xr.definition is not None
    assert xr.definition.file.endswith("nested_property_event.cs")


def test_csharp_event_declaration_is_not_yet_a_symbol(csharp_nested_file):
    # frob:tests tests/unit/test_xref.py::test_csharp_event_declaration_is_not_yet_a_symbol  # noqa: E501
    # frob:ticket T-4519
    # frob:ticket T-4679
    # T-4519: DISCLOSED GAP, not a regression -- `frob.lang._walk_csharp`
    # (owned by T-4507's live edit, out of this ticket's scope:
    # src/frob/xref/__init__.py, src/frob/docs/__init__.py, src/frob/perf/
    # _collectors.py only) has no `event_declaration` case, so `Changed`
    # never becomes a RawSymbol at all and xref cannot find it regardless
    # of `_DEFINITION_KINDS`. This test pins the current (missing)
    # behavior so a future walker change is a deliberate, visible diff
    # here rather than a silent flip. See the filed follow-up ticket for
    # adding an event_declaration case to _walk_csharp.py.
    result = xref("Changed", csharp_nested_file, lang="csharp")
    assert result.is_ok
    assert result.danger_ok.definition is None
