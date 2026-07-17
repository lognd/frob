"""
Unit tests for frob.dup.find_duplicates.

The frob.dup module may not exist yet; these tests are written against its
expected public API and will be collected/skipped appropriately.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"

try:
    from frob.dup import find_duplicates

    HAS_DUP = True
except ImportError:
    HAS_DUP = False

pytestmark = pytest.mark.skipif(not HAS_DUP, reason="frob.dup not available")


# ---------------------------------------------------------------------------
# basic duplicate detection
# ---------------------------------------------------------------------------


class TestFindDuplicates:
    def test_dup_python_finds_one_group(self):
        # frob:tests src/frob/dup/_legacy.py::find_duplicates kind="unit"
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        assert len(result.groups) == 1

    def test_dup_python_total_clones_counts_all_fragments(self):
        # frob:tests src/frob/dup/_legacy.py::DupResult.total_clones kind="unit"
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        assert result.total_clones == sum(len(g.fragments) for g in result.groups)

    def test_dup_python_group_has_two_fragments(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        assert len(result.groups[0].fragments) == 2

    def test_dup_python_fragment_names(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        symbols = {f.symbol for f in result.groups[0].fragments}
        assert "process_items" in symbols
        assert "handle_entries" in symbols

    def test_simple_python_finds_no_groups(self):
        result = find_duplicates(FIXTURES / "simple_python" / "src")
        assert len(result.groups) == 0

    def test_gamma_not_in_dup_group(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        all_symbols = {f.symbol for g in result.groups for f in g.fragments}
        assert "format_report" not in all_symbols


# ---------------------------------------------------------------------------
# min_lines threshold
# ---------------------------------------------------------------------------


class TestMinLinesThreshold:
    def test_high_threshold_excludes_duplicates(self):
        # With a very high min_lines, the duplicate pair should not be flagged
        result = find_duplicates(FIXTURES / "dup_python" / "src", min_lines=100)
        assert len(result.groups) == 0

    def test_low_threshold_includes_duplicates(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src", min_lines=3)
        assert len(result.groups) >= 1

    def test_default_threshold_finds_dup_python(self):
        # The duplicate functions are 8+ lines so default threshold should flag them
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        assert len(result.groups) >= 1


# ---------------------------------------------------------------------------
# output format
# ---------------------------------------------------------------------------


class TestDupResultFormat:
    def test_as_text_returns_string(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        text = result.as_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_as_text_mentions_a_function(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        text = result.as_text()
        assert (
            "process_items" in text
            or "handle_entries" in text
            or "group" in text.lower()
        )

    def test_as_json_is_valid_json(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        data = json.loads(result.as_json())
        assert isinstance(data, dict)

    def test_as_json_has_groups_key(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        data = json.loads(result.as_json())
        assert "groups" in data

    def test_as_json_group_count_matches(self):
        result = find_duplicates(FIXTURES / "dup_python" / "src")
        data = json.loads(result.as_json())
        assert len(data["groups"]) == len(result.groups)

    def test_as_text_clean_project(self):
        result = find_duplicates(FIXTURES / "simple_python" / "src")
        text = result.as_text()
        assert isinstance(text, str)
        # Clean project text should indicate no duplicates
        assert "0" in text or "no duplicate" in text.lower()


# ---------------------------------------------------------------------------
# interface-level integration
# ---------------------------------------------------------------------------


def test_dup_end_to_end_scan_then_render():
    # frob:tests src/frob/dup kind="integration"
    # Drive the legacy dup boundary end to end: scan a real fixture tree,
    # group the clones, and round-trip the result through both renderers.
    result = find_duplicates(FIXTURES / "dup_python" / "src")
    assert result.groups
    assert result.total_clones == sum(len(g.fragments) for g in result.groups)
    data = json.loads(result.as_json())
    assert len(data["groups"]) == len(result.groups)
    assert isinstance(result.as_text(), str)
