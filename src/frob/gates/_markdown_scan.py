"""Shared markdown code-span stripping for prose-scanning gates (T-1700).

Extracted from `frob.gates._doclink_docanchor` (DOC011's own
`_strip_code_spans`, T-1486) so a second prose-scanning rule never has to
choose between re-deriving the same regex pair (and risking it drifting
out of sync -- this repo has already paid for that class of desync once)
or reaching across `_doclink_docanchor.py`'s private namespace. Any gate
that scans doc/ticket PROSE for a lexical pattern (a ticket id, a link, a
CLI invocation, ...) and must not fire on prose that merely MENTIONS the
pattern inside inline `` `code` `` or a fenced ```` ```block``` ```` --
rather than actually using it -- belongs on this shared helper, not a
private copy.

T-1700's own incident is the reason this module exists: TICK006 (`frob.
gates._tickets_gate`) scanned a Done report's raw prose for a ticket-id
shape near the word "filed" with no code-span awareness at all, and fired
on `` `Filed: T-0104` `` -- a Done report EXPLAINING DOC011's own
code-span exemption, not claiming T-0104 was filed. DOC011 already had
*a* fix; TICK006 needed the same one, not a second, independently-drifting
implementation of it.

**A second, deeper bug found and fixed in the same extraction (T-1700).**
DOC011's original `_INLINE_CODE_RE` only matched SINGLE-backtick-delimited
spans (`` `text` ``) -- but the T-1542 Done report (and this module's own
example above) uses DOUBLE-backtick delimiters (`` `` `text` `` ``, the
standard CommonMark escape a span reaches for the moment its own content
needs a literal backtick, or a writer reaches for out of habit). Against
a single-backtick-only regex, `` `` `Filed: T-0104` `` `` does not match
as ONE span at all -- the engine instead finds tiny, unrelated 3-
character `` ` ` `` fragments at the OUTER edges and leaves "Filed:
T-0104" itself completely unblanked, exposed to whatever scans the
"stripped" text as if it were ordinary prose. This was the actual reason
main stayed red even after TICK006 started reusing DOC011's stripping:
reusing a subtly wrong implementation faithfully reproduces the bug, it
does not fix it. `_INLINE_CODE_RE` below now matches a CommonMark-correct
backtick-RUN span (opens with N backticks, closes with the next run of
exactly N backticks, via a `\1` backreference) instead of assuming N is
always 1.
"""

from __future__ import annotations

import re

#: A fenced code block (```` ```...``` ````), DOTALL so it can span
#: multiple lines -- blanked first so an inline-code-span match never
#: partially eats into (or out of) a fence.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)

#: An inline `` `code` `` span, CommonMark-correct on the backtick-RUN
#: length: opens with a run of N backticks (`` (`+) ``, captured as group
#: 1) and closes with the NEXT run of exactly N backticks (`` \1 ``,
#: matched via backreference, never a shorter or longer run) -- the T-1700
#: fix for the two-backtick-delimited-span bug this module's own docstring
#: describes (a single-backtick-only version of this regex silently fails
#: to match `` `` `text` `` `` as one span at all). Content allows AT MOST
#: ONE embedded newline (a genuine line-wrapped span, e.g.
#: `` `frob quality \n bind` `` is still one token) but never two
#: consecutive newlines (a blank line -- a real paragraph break, meaning
#: the opening and closing backtick runs were unrelated stray characters,
#: not one span) -- `(?!\1)` inside the content group also stops a SHORTER
#: internal backtick run from being consumed as if it could close the
#: span early. Non-greedy (`+?`) so two separate spans on the same line
#: are matched as two, not merged into one spanning the prose between
#: them.
_INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1)[^\n]|\n(?!\n))+?\1")


def _blank_non_newlines(match: re.Match[str]) -> str:
    """Replace `match` with spaces, keeping any embedded newlines intact
    (so line numbers computed against the blanked text stay correct)."""
    return "".join(c if c == "\n" else " " for c in match.group(0))


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse.test_id_inside_fenced_code_block_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_code_spanned_filed_claim_does_not_fire  # noqa: E501
def strip_code_spans(text: str) -> str:
    """Blank out fenced code blocks and inline `` `code` `` spans so a
    prose scanner never mistakes a code EXAMPLE (a literal ticket id, a
    CLI invocation, a symbol reference shown for illustration) for a real
    claim about it -- newline count (and therefore line numbers) is
    preserved, so callers computing `line` against the original text stay
    correct against the blanked one too.

    A blank line (two consecutive newlines, a genuine paragraph break)
    inside what looks like an inline span is deliberately NOT treated as
    part of it (`_INLINE_CODE_RE`'s own comment) -- that is two unrelated
    stray backticks, not one wrapped span; blanking across a paragraph
    break would silently hide real prose on the far side of it."""
    text = _FENCED_CODE_RE.sub(_blank_non_newlines, text)
    return _INLINE_CODE_RE.sub(_blank_non_newlines, text)


__all__ = ["strip_code_spans"]
