"""frob.webapp._a11y_substrate coverage: positive/negative controls per
query shape, across the html/jsx/vue grammar families.

frob:ticket T-5313
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.lang import raw_tree
from frob.webapp._a11y_substrate import (
    A11ySubstrateError,
    elements_missing_attribute,
    elements_with_attribute,
    heading_sequence,
    html_lang,
)

_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "a11y1xx"


def _load(rel_path: str) -> tuple:
    """Parse `rel_path` (relative to the fixture root) via `frob.lang.raw_tree`,
    returning `(root_node, source, language)`."""
    path = _FIXTURE_ROOT / rel_path
    result = raw_tree(path)
    assert result.is_ok, f"raw_tree({path}) failed: {result}"
    tree, source, language = result.danger_ok
    return tree.root_node, source, language


# frob:tests src/frob/webapp/_a11y_substrate.py::elements_with_attribute kind="unit"
# frob:tests src/frob/webapp/_a11y_substrate.py::ElementMatch kind="unit"
def test_elements_with_attribute_html_positive_control():
    """MUST-FIRE: the clean html fixture's <img alt> is found by elements_with_attribute."""
    root, source, language = _load("html_alt/clean.html")
    result = elements_with_attribute(root, language, source, frozenset({"img"}), "alt")
    assert result.is_ok
    matches = result.danger_ok
    assert len(matches) == 1
    assert matches[0].attributes["alt"] == "A sleeping cat"


# frob:tests src/frob/webapp/_a11y_substrate.py::elements_missing_attribute kind="unit"
def test_elements_missing_attribute_html_negative_control():
    """MUST-FIRE: the violation html fixture's <img> (no alt) is found by
    elements_missing_attribute; the clean fixture reports none."""
    root, source, language = _load("html_alt/violation.html")
    result = elements_missing_attribute(
        root, language, source, frozenset({"img"}), "alt"
    )
    assert result.is_ok
    assert len(result.danger_ok) == 1

    clean_root, clean_source, clean_language = _load("html_alt/clean.html")
    clean_result = elements_missing_attribute(
        clean_root, clean_language, clean_source, frozenset({"img"}), "alt"
    )
    assert clean_result.is_ok
    assert clean_result.danger_ok == ()


# frob:tests src/frob/webapp/_a11y_substrate.py::elements_with_attribute kind="unit"
def test_elements_with_attribute_jsx_positive_control():
    """MUST-FIRE: the clean jsx fixture's <input aria-label> is found."""
    root, source, language = _load("jsx_aria_label/clean.jsx")
    result = elements_with_attribute(
        root, language, source, frozenset({"input"}), "aria-label"
    )
    assert result.is_ok
    matches = result.danger_ok
    assert len(matches) == 1
    assert matches[0].attributes["aria-label"] == "Search"


# frob:tests src/frob/webapp/_a11y_substrate.py::elements_missing_attribute kind="unit"
def test_elements_missing_attribute_jsx_negative_control():
    """MUST-FIRE: the violation jsx fixture's <input> (no aria-label) is found."""
    root, source, language = _load("jsx_aria_label/violation.jsx")
    result = elements_missing_attribute(
        root, language, source, frozenset({"input"}), "aria-label"
    )
    assert result.is_ok
    assert len(result.danger_ok) == 1


# frob:tests src/frob/webapp/_a11y_substrate.py::heading_sequence kind="unit"
# frob:tests src/frob/webapp/_a11y_substrate.py::HeadingMatch kind="unit"
def test_heading_sequence_vue_positive_control():
    """MUST-FIRE: the clean vue fixture's h1/h2/h3 sequence is unbroken."""
    root, source, language = _load("vue_headings/clean.vue")
    result = heading_sequence(root, language, source)
    assert result.is_ok
    levels = [h.level for h in result.danger_ok]
    assert levels == [1, 2, 3]


# frob:tests src/frob/webapp/_a11y_substrate.py::heading_sequence kind="unit"
def test_heading_sequence_vue_negative_control_skips_a_level():
    """MUST-FIRE: the violation vue fixture skips h2 (h1 -> h3 directly)."""
    root, source, language = _load("vue_headings/violation.vue")
    result = heading_sequence(root, language, source)
    assert result.is_ok
    levels = [h.level for h in result.danger_ok]
    assert levels == [1, 3]


# frob:tests src/frob/webapp/_a11y_substrate.py::html_lang kind="unit"
def test_html_lang_positive_control():
    """MUST-FIRE: the clean html fixture's <html lang="en"> is reported."""
    root, source, language = _load("html_lang/clean.html")
    result = html_lang(root, language, source)
    assert result.is_ok
    assert result.danger_ok == "en"


# frob:tests src/frob/webapp/_a11y_substrate.py::html_lang kind="unit"
def test_html_lang_negative_control_missing_attribute():
    """MUST-FIRE: the violation html fixture's bare <html> (no lang) reports None."""
    root, source, language = _load("html_lang/violation.html")
    result = html_lang(root, language, source)
    assert result.is_ok
    assert result.danger_ok is None


# frob:tests src/frob/webapp/_a11y_substrate.py::elements_with_attribute kind="unit"
# frob:tests src/frob/webapp/_a11y_substrate.py::A11ySubstrateError kind="unit"
def test_elements_with_attribute_unsupported_language_errors():
    """An unrecognized language returns A11ySubstrateError.UnsupportedLanguage,
    not a crash -- fallible-op contract for a language this substrate never walks."""
    root, source, _language = _load("html_alt/clean.html")
    result = elements_with_attribute(root, "python", source, frozenset({"img"}), "alt")
    assert result.is_err
    assert result.danger_err is A11ySubstrateError.UnsupportedLanguage


@pytest.mark.parametrize(
    "func,args",
    [
        (elements_with_attribute, (frozenset({"img"}), "alt")),
        (elements_missing_attribute, (frozenset({"img"}), "alt")),
    ],
)
# frob:tests src/frob/webapp/_a11y_substrate.py::elements_with_attribute kind="unit"
# frob:tests src/frob/webapp/_a11y_substrate.py::elements_missing_attribute kind="unit"
def test_attribute_queries_unsupported_language_errors(func, args):
    """Both attribute-query helpers share the same unsupported-language error path."""
    root, source, _language = _load("html_alt/clean.html")
    result = func(root, "python", source, *args)
    assert result.is_err
    assert result.danger_err is A11ySubstrateError.UnsupportedLanguage
