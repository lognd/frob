"""Unit tests for `frob.strata._sync_may`'s surviving surface: the shared
`.strata` node/store body brace-depth scanner (`node_body_span`, T-1895).

T-2920: this module used to also carry SYS100's core+extended `may`
grant auto-widening writer (T-1531/T-1545) and this file's own tests for
it -- both deleted together (see `_sync_may.py`'s own T-2920 docstring
for the full rationale: the writer was a rubber-stamp with no teeth,
confirmed dead with zero importers once T-2922 unwired its only caller).
"""

from __future__ import annotations

from frob.strata._sync_may import node_body_span


# frob:ticket T-1895
class TestNodeBodySpan:
    """`node_body_span`'s brace-depth scan (T-1895: the single shared
    home for this scanner -- `frob.strata._shrink` (T-2923) imports it
    instead of keeping its own byte-identical copy)."""

    # frob:ticket T-1895
    def test_flat_body_returns_closing_brace_line(self):
        """A node body with no nested `{`/`}` closes at the first bare
        `}` line after the header."""
        lines = [
            "node Foo : trusted {",
            '    code "foo/**";',
            "}",
        ]
        assert node_body_span(lines, 0) == 2

    # frob:ticket T-1895
    def test_nested_braces_do_not_close_early(self):
        """A nested sub-block's own braces (e.g. `on crash { ... }`) must
        not terminate the scan before the node's own closing brace."""
        lines = [
            "node Foo : trusted {",
            '    code "foo/**";',
            "    on crash {",
            '        notify "team";',
            "    }",
            "}",
        ]
        assert node_body_span(lines, 0) == 5

    # frob:ticket T-1895
    def test_malformed_input_returns_last_line_best_effort(self):
        """No matching close brace at all: falls back to the last line
        index rather than raising."""
        lines = [
            "node Foo : trusted {",
            '    code "foo/**";',
        ]
        assert node_body_span(lines, 0) == 1
