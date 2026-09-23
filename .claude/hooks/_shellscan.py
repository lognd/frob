"""Shared shell-command scanning primitives for the PreToolUse hooks.

CANONICAL COPY (git-tracked). Materialised into `~/.claude/hooks/` by
`sync-claude-config.py`; never hand-edit the copy.

Every hook that decides something from a Bash command string faces the same
two problems, and both have already produced real false positives here:

1. COMMAND POSITION. A tool name is only a command when it appears where a
   command can appear -- line start, or after a shell connector. Without
   that anchor, `git commit -m "... make targets ..."` reads as a `make`
   invocation.
2. QUOTED TEXT IS PROSE, NOT PROGRAM. Everything a command SAYS -- commit
   messages, echo strings, heredoc bodies -- is data. Only what it RUNS is a
   command. `frob-timeout-guard` blocked a command purely because the text
   `uv run frob test` appeared inside a quoted rule description.

Both hooks needed identical logic, so it lives here once. Two copies of a
scanning rule is a desync waiting to happen -- this repo has paid for that
in `_doclink_docanchor`'s code-span stripping already.

IMPORTANT ASYMMETRY. Strip quotes to decide WHETHER A COMMAND RUNS, but read
the RAW string to decide WHAT ITS ARGUMENTS ARE. Stripping deletes the
arguments, and an argument is often the whole reason a command is fine:
`pytest "tests/x.py::test_y"` is properly scoped, but strip the quotes and
it looks like a bare `pytest`. That exact interaction blocked a correctly
scoped test run minutes after quote-stripping was introduced.
"""

import re

#: Command position: line start, after a shell connector, or after `uv run`
#: (optionally `timeout N`-wrapped).
#:
#: `(` is deliberately NOT a connector. It matched prose parentheticals --
#: "(make targets, ...)" inside a commit message -- and blocked a commit on
#: the first real use. A subshell is rare; an English sentence in a quoted
#: string is constant.
# frob:doc docs/guides/claude-hooks.md#_shellscanpy
POS = r"(?:^|[;&|]\s*|\buv +run +)(?:timeout +\d+ +)?"

#: Quoted spans and heredoc bodies.
_QUOTED = re.compile(
    r"'[^']*'"  # single-quoted span
    r"|\"(?:[^\"\\]|\\.)*\""  # double-quoted span (backslash-aware)
    r"|<<-?\s*'?(\w+)'?.*?^\1\b",  # heredoc body, incl. quoted delimiter
    re.S | re.M,
)


# frob:doc docs/guides/claude-hooks.md#_shellscanpy
# frob:tests tests/test_hook_pgrep_self_match_guard.py kind="integration"
def quoted_spans(command: str) -> list[tuple[int, int]]:
    """`(start, end)` of every quoted span and heredoc body in `command`,
    for rules that must keep a quoted ARGUMENT visible (the literal a
    `pgrep -f` is given) while still ignoring text the command merely
    carries: a match whose start lies inside one of these spans is prose,
    not a command."""
    return [(m.start(), m.end()) for m in _QUOTED.finditer(command)]


# frob:doc docs/guides/claude-hooks.md#_shellscanpy
# frob:tests tests/test_hook_frob_suggest.py kind="integration"
def strip_quoted(command: str) -> str:
    """`command` with quoted spans and heredoc bodies blanked to a space.

    Match rules against the RESULT so a rule fires only on what the shell
    would actually execute, never on text the command merely carries."""
    return _QUOTED.sub(" ", command)


#: Segment boundaries: `;`, `&&`, `||`, a pipe, or a newline -- the same
#: connectors `POS` treats as command-position anchors (its `[;&|]` class),
#: minus a bare single `&` (background-job separator). A bare `&` is
#: deliberately NOT split on: it is indistinguishable by regex from the
#: `&` inside a redirect like `2>&1`, which is common in exactly the
#: commands this module scans (T-2031's own `frob check` piped through a
#: filter, `2>&1` redirect included) and must never be mistaken for a
#: segment break.
_SEGMENT_BREAK = re.compile(r"&&|\|\||\n|[;|]")


# frob:doc docs/guides/claude-hooks.md#_shellscanpy
def segment_spans(command: str) -> list[tuple[int, int]]:
    """`(start, end)` character spans of `command`'s shell segments, split
    on its own top-level `;`, `&&`, `||`, `|` and newline separators --
    ones that sit outside quoted spans and heredoc bodies, so a separator
    character that is only prose inside a quoted argument never splits
    anything. The connector characters THEMSELVES fall in the gaps
    between spans and are never part of a span.

    T-3851: this is the ONE place that decides where one shell command
    ends and the next begins. A per-segment decision (an acknowledgement
    prefix, a rule that must not cross an unrelated command) that
    reimplements this split instead of calling it is exactly the
    desync this module's docstring already warns about. Spans, not
    strings, are the primitive: a caller that needs to blank or edit one
    segment while leaving the original connectors intact (T-3851's ack
    scan does exactly this) can only do that from positions, since
    rejoining plain substrings would have to guess back at whatever
    connector used to sit between them."""
    protected = [m.span() for m in _QUOTED.finditer(command)]

    def _in_protected(pos: int) -> bool:
        return any(start <= pos < end for start, end in protected)

    spans: list[tuple[int, int]] = []
    prev = 0
    for match in _SEGMENT_BREAK.finditer(command):
        if _in_protected(match.start()):
            continue
        spans.append((prev, match.start()))
        prev = match.end()
    spans.append((prev, len(command)))
    return spans


# frob:doc docs/guides/claude-hooks.md#_shellscanpy
# frob:waive WIRE001 reason="called by .claude/hooks/frob-suggest.py::_handle_bash in \
# this same diff (from _shellscan import strip_and_blank_prefixed_segments as \
# _strip_and_blank, after this package's usual sys.path.insert hack) -- WIRE001's \
# call-graph resolver does not trace calls through that dynamic import pattern, a \
# blind spot never exercised before since POS/strip_quoted (the same package's \
# pre-existing cross-file symbols) are never NEW in a diff and so never checked" \
# follow_up="T-4574"
def strip_and_blank_prefixed_segments(
    command: str, prefix: re.Pattern[str]
) -> tuple[str, str]:
    """`(stripped, blanked)` views of `command`, edited in place at
    `segment_spans`' boundaries so every original connector stays put --
    only a span's own content is ever touched. A segment "carries" the
    prefix when `prefix` matches its own quote-stripped, left-anchored
    text (so a segment merely MENTIONING it inside a quoted argument
    never counts):

    - `stripped` drops a leading `prefix` match from any carrying
      segment, keeping the rest of its content -- the text a caller
      matches its own rules against, so the prefix never itself changes
      what a rule sees.
    - `blanked` additionally spaces out the REST of a carrying segment's
      content (positions, and so any command-position anchor a caller's
      rules use, stay stable). Matching a rule against `blanked` answers
      "does it still fire once every carrying segment is removed?" -- if
      not, the prefix covered the whole hit; if it still fires, some
      OTHER segment caused it (T-3851: this is how a per-command
      acknowledgement is scoped to agree with a whole-string trigger
      scan, rather than only ever matching position zero)."""
    stripped = list(command)
    blanked = list(command)
    for start, end in segment_spans(command):
        segment = command[start:end]
        match = prefix.match(strip_quoted(segment))
        if match is None:
            continue
        prefix_end = start + match.end()
        for i in range(start, prefix_end):
            stripped[i] = ""
            blanked[i] = ""
        for i in range(prefix_end, end):
            blanked[i] = " "
    return "".join(stripped), "".join(blanked)
