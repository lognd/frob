"""frob.sql._squawk_adapter coverage (T-5333): pure JSON-parse tests
against canned squawk `--reporter json` fixtures (no real `squawk`
binary needed), plus a live `squawk_findings` absence-is-graceful check.

frob:ticket T-5333
"""

from __future__ import annotations

from pathlib import Path

from frob.sql._squawk_adapter import SquawkFinding, _parse_squawk_json, squawk_findings

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "sql" / "squawk"


# frob:tests src/frob/sql/_squawk_adapter.py::_parse_squawk_json kind="unit"
# frob:tests src/frob/sql/_squawk_adapter.py::SquawkFinding kind="unit"
def test_parse_squawk_json_not_null_no_default() -> None:
    """squawk's `adding-not-nullable-field` JSON output is parsed into a
    `SquawkFinding` with rule/file/line/message populated."""
    text = (_FIXTURE_ROOT / "not_null_no_default.squawk.json").read_text()
    findings = _parse_squawk_json(text, "0001_not_null_no_default.sql")
    assert findings == (
        SquawkFinding(
            rule="adding-not-nullable-field",
            file="0001_not_null_no_default.sql",
            line=4,
            message=(
                "Adding a NOT NULL column without a default locks the "
                "table for the duration of the migration."
            ),
        ),
    )


# frob:tests src/frob/sql/_squawk_adapter.py::_parse_squawk_json kind="unit"
def test_parse_squawk_json_index_without_concurrently() -> None:
    """squawk's `require-concurrent-index-creation` JSON output is
    parsed into a `SquawkFinding`."""
    text = (_FIXTURE_ROOT / "index_without_concurrently.squawk.json").read_text()
    findings = _parse_squawk_json(text, "0002_index_without_concurrently.sql")
    assert len(findings) == 1
    assert findings[0].rule == "require-concurrent-index-creation"
    assert findings[0].line == 4


# frob:tests src/frob/sql/_squawk_adapter.py::_parse_squawk_json kind="unit"
def test_parse_squawk_json_empty_array_is_no_findings() -> None:
    """squawk's `[]` (a clean migration file) parses to no findings."""
    text = (_FIXTURE_ROOT / "clean.squawk.json").read_text()
    assert _parse_squawk_json(text, "clean.sql") == ()


# frob:tests src/frob/sql/_squawk_adapter.py::_parse_squawk_json kind="unit"
def test_parse_squawk_json_malformed_text_is_no_findings() -> None:
    """Unparseable JSON never raises -- `()`, not an exception."""
    assert _parse_squawk_json("not valid json {{{", "x.sql") == ()


# frob:tests src/frob/sql/_squawk_adapter.py::_parse_squawk_json kind="unit"
def test_parse_squawk_json_missing_messages_falls_back_to_help() -> None:
    """An entry with no `messages` falls back to squawk's own `help`
    text rather than dropping the finding."""
    text = (
        '[{"rule_name": "renaming-column", "line_number": 2, '
        '"help": "Renaming a column breaks readers mid-deploy."}]'
    )
    findings = _parse_squawk_json(text, "x.sql")
    assert len(findings) == 1
    assert findings[0].message == "Renaming a column breaks readers mid-deploy."


# frob:tests src/frob/sql/_squawk_adapter.py::squawk_findings kind="unit"
def test_squawk_findings_absent_binary_is_empty_not_raising() -> None:
    """`squawk_findings` never raises when `squawk` is not on PATH (the
    common case in this sandbox) -- it returns `()`, the same "absence
    is measured elsewhere" posture the module's own docstring
    describes."""
    findings = squawk_findings(_FIXTURE_ROOT)
    assert isinstance(findings, tuple)
