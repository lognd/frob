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
POS = r"(?:^|[;&|]\s*|\buv +run +)(?:timeout +\d+ +)?"

#: Quoted spans and heredoc bodies.
_QUOTED = re.compile(
    r"'[^']*'"  # single-quoted span
    r"|\"(?:[^\"\\]|\\.)*\""  # double-quoted span (backslash-aware)
    r"|<<-?\s*'?(\w+)'?.*?^\1\b",  # heredoc body, incl. quoted delimiter
    re.S | re.M,
)


def strip_quoted(command: str) -> str:
    """`command` with quoted spans and heredoc bodies blanked to a space.

    Match rules against the RESULT so a rule fires only on what the shell
    would actually execute, never on text the command merely carries."""
    return _QUOTED.sub(" ", command)
