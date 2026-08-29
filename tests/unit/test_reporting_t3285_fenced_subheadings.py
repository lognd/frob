"""T-3285: `disclosure_shaped_language`'s structural subheading signal
must never treat a line INSIDE a fenced code block (the "### Changed"
section's own fenced `git --stat` output, T-2718's own Tier-A-generated
shape) as a real markdown subheading. Reproduces the reported false
positive directly against the real helper (not a re-implementation)."""

from __future__ import annotations

from frob.tickets._reporting import (
    _subheading_titles_outside_fences,
    compose_done_report,
    disclosure_shaped_language,
)


class TestSubheadingTitlesOutsideFences:
    def test_hash_line_inside_fence_not_a_subheading(self) -> None:
        # frob:tests tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences.test_hash_line_inside_fence_not_a_subheading  # noqa: E501
        section = (
            "### Changed\n```\n"
            " docs/design/foo.md | 2 +-\n"
            "## a stray line from a diff hunk\n"
            "```\n"
        )
        assert _subheading_titles_outside_fences(section) == ["Changed"]

    def test_real_subheading_after_a_fence_still_detected(self) -> None:
        # frob:tests tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences.test_real_subheading_after_a_fence_still_detected  # noqa: E501
        section = "### Changed\n```\nfoo.py | 1 +\n```\n\n### Genuine extra section\nprose\n"
        assert _subheading_titles_outside_fences(section) == [
            "Changed",
            "Genuine extra section",
        ]

    def test_unterminated_trailing_fence_swallows_rest(self) -> None:
        # frob:tests tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences.test_unterminated_trailing_fence_swallows_rest  # noqa: E501
        section = "### Changed\n```\n## not a heading, fence never closes\n"
        assert _subheading_titles_outside_fences(section) == ["Changed"]


class TestDisclosureShapedLanguageFencedChanged:
    def test_stat_line_starting_with_hash_inside_changed_block_not_flagged(
        self,
    ) -> None:
        # frob:tests tests/unit/test_reporting_t3285_fenced_subheadings.py::TestDisclosureShapedLanguageFencedChanged.test_stat_line_starting_with_hash_inside_changed_block_not_flagged  # noqa: E501
        changed_lines = [
            " docs/design/foo.md | 2 +-",
            "## a stray line from a diff hunk quoting a markdown heading",
        ]
        report = compose_done_report(
            "did the thing", changed_lines, ["tests/x.py::test_y"]
        )
        assert disclosure_shaped_language(report) is None

    def test_genuine_subheading_outside_fence_still_flagged(self) -> None:
        # frob:tests tests/unit/test_reporting_t3285_fenced_subheadings.py::TestDisclosureShapedLanguageFencedChanged.test_genuine_subheading_outside_fence_still_flagged  # noqa: E501
        # A subheading title with no phrase-list overlap, so this exercises
        # signal 2 (the structural subheading scan) specifically, not
        # signal 1's phrase match.
        report = compose_done_report(
            "did the thing\n\n### Scope boundary note\nsome real disclosure",
            ["foo.py | 1 +"],
            ["tests/x.py::test_y"],
        )
        phrase = disclosure_shaped_language(report)
        assert phrase is not None
        assert "Scope boundary note" in phrase
