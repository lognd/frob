"""Mechanically strip `T-####` citations out of argparse help strings (T-5134).

WHY THIS EXISTS. `count_ticket_citations.py --scope help` found 274 `T-####`
tokens inside `help=`/`description=`/`epilog=` string literals under
`src/frob/_cli_parsers/` (plus the one help-returning helper,
`_deprecated_skip_help`) -- every one of them lands in real `--help`
output per the owner directive of 2026-09-20. Hand-editing 274 call sites
across 20 files is exactly the kind of mechanical, repetitive edit that
should be scripted once and re-run, not re-derived per file.

This script is AST-precise: it only rewrites the *exact source span* of
each `help=`/`description=`/`epilog=` string literal (or a
`_deprecated_skip_help`-style helper's return literal), leaving every
docstring and `#` comment in the same file untouched -- those belong to
T-4691 (source comment narrative), not this ticket. The provenance the
citation carried is not silently dropped: where the enclosing statement
does not already sit under a `# frob:ticket T-####` directive comment,
one is inserted immediately above it so `frob:tests`/lint tooling can
still trace the history.

Usage:
    uv run python scripts/strip_help_citations.py --apply
    uv run python scripts/strip_help_citations.py            # dry run, prints a diff
"""

from __future__ import annotations

import argparse
import ast
import difflib
import logging
import re
from pathlib import Path

from count_ticket_citations import (
    _HELP_KEYWORDS,
    _HELP_RETURNING_HELPERS,
    TICKET_RE,
)

logger = logging.getLogger(__name__)

#: A possessive citation, e.g. "T-1615's" -- the clitic has to go with it
#: or the sentence loses its subject ("skip T-1615's uniform" must become
#: "skip uniform", never "skip's uniform").
_POSSESSIVE_CITATION_RE = re.compile(r"T-\d{4}'s\s*")

#: A citation immediately followed by the punctuation that was only ever
#: separating it from the next clause, e.g. "T-4524: use --skip" or
#: "T-3837; see `frob ticket show`'s list" -- keep the clause, drop the
#: citation and its now-redundant punctuation.
_CITATION_TRAILING_PUNCT_RE = re.compile(r"T-\d{4}[,;:]\s*")

#: A citation joined onto the previous clause by a connector, e.g.
#: ", T-4522" or "and T-4522" -- the connector was only there to add
#: this citation to a list, so it goes with it.
_CITATION_LEADING_CONNECTOR_RE = re.compile(
    r"(?:,\s+|;\s+|\band\s+|\bor\s+)T-\d{4}\b\s*"
)

#: Whatever bare `T-####` is left once the two passes above have handled
#: every punctuation-adjacent case.
_BARE_CITATION_RE = re.compile(r"T-\d{4}\b\s*")

#: Cosmetic cleanup applied after citation removal (never touches a
#: line's leading indentation -- callers only pass the post-indent tail).
_DOUBLE_SPACE_RE = re.compile(r"  +")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([.,:;])")
#: A parenthetical that held nothing but citations joined by a bare
#: separator, e.g. "(T-1614/T-2467)" -> "(/)" once both are stripped.
_EMPTY_PARENS_RE = re.compile(r"\(\s*[/,]*\s*\)")

#: A cross-fragment artifact only removal can create: a line's trailing
#: joining space survives even though the next concatenated fragment,
#: once its leading citation is gone, now starts with punctuation --
#: e.g. `"...shell "\n    "; mutually exclusive..."` reading "shell ;".
#: Collapse the orphaned space, never the newline/indent/quotes.
_CROSS_LINE_JOIN_ARTIFACT_RE = re.compile(r' +"\n(\s*)"([,;:])')

#: The same cross-fragment situation but where BOTH sides still carry a
#: joining space (e.g. citation removal left "scope+lease " followed by
#: " -- fails"), so the rendered text reads "lease  -- fails" (two
#: spaces). Collapse to exactly one, matched only after the punctuation
#: case above already fired so the two substitutions never overlap.
_CROSS_LINE_DOUBLE_SPACE_RE = re.compile(r' +"\n(\s*)" +')


def _strip_citation_line(line: str) -> str:
    """Apply citation removal to one physical line, preserving its
    leading indentation exactly (only inline whitespace is collapsed).
    """
    indent_len = len(line) - len(line.lstrip(" "))
    indent, rest = line[:indent_len], line[indent_len:]
    out = _POSSESSIVE_CITATION_RE.sub("", rest)
    out = _CITATION_TRAILING_PUNCT_RE.sub("", out)
    out = _CITATION_LEADING_CONNECTOR_RE.sub("", out)
    out = _BARE_CITATION_RE.sub("", out)
    out = _EMPTY_PARENS_RE.sub("", out)
    out = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", out)
    out = _DOUBLE_SPACE_RE.sub(" ", out)
    return indent + out


# frob:doc docs/guides/coordinator-scripts.md#strip_citation_text
def strip_citation_text(text: str) -> str:
    """Remove every `T-####` citation from a help-string source segment,
    keeping the surrounding sentence, each physical line's original
    indentation, and tidying the punctuation the citation leaves behind.
    """
    lines = [_strip_citation_line(line) for line in text.split("\n")]
    # The very last physical line is where the string literal itself ends
    # (not a mid-sentence line break to the next concatenated fragment),
    # so a space directly before the closing quote(s) is never meaningful
    # rendered text -- trim it without touching the quote characters.
    lines[-1] = re.sub(r" +(['\"]+)$", r"\1", lines[-1])
    out = "\n".join(lines)
    # A citation removal can leave a cross-fragment join artifact -- the
    # PRECEDING literal's trailing joining space now abuts either bare
    # punctuation or another joining space from the FOLLOWING literal.
    # Scoped to this one node's own segment, never the rest of the file.
    out = _CROSS_LINE_JOIN_ARTIFACT_RE.sub('"\n\\1"\\2', out)
    out = _CROSS_LINE_DOUBLE_SPACE_RE.sub('"\n\\1" ', out)
    return out


def _target_nodes(tree: ast.AST) -> list[ast.expr]:
    """Return every literal node in `tree` whose rendered text is
    user-facing help text: `help=`/`description=`/`epilog=` keyword
    values, and the return literals of `_HELP_RETURNING_HELPERS`.
    """
    targets: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in _HELP_KEYWORDS and TICKET_RE.search(ast.dump(kw.value)):
                    targets.append(kw.value)
        elif isinstance(node, ast.FunctionDef) and node.name in _HELP_RETURNING_HELPERS:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and inner.value is not None:
                    targets.append(inner.value)
    return targets


# frob:doc docs/guides/coordinator-scripts.md#rewrite_file
def rewrite_file(path: Path) -> str | None:
    """Return the citation-stripped text of `path`, or None if it has no
    help-string citations to remove.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    targets = [
        n
        for n in _target_nodes(tree)
        if TICKET_RE.search(ast.get_source_segment(source, n) or "")
    ]
    if not targets:
        return None

    lines = source.splitlines(keepends=True)
    # Process end-to-start so earlier offsets stay valid as we splice.
    targets.sort(key=lambda n: (n.lineno, n.col_offset), reverse=True)
    for node in targets:
        segment = ast.get_source_segment(source, node)
        if segment is None or not TICKET_RE.search(segment):
            continue
        new_segment = strip_citation_text(segment)
        # A parsed expression node always carries real end position info
        # (only synthetic nodes built without `ast.fix_missing_locations`
        # lack it, and every target here came straight from `ast.parse`).
        assert node.end_lineno is not None
        assert node.end_col_offset is not None
        start_line, start_col = node.lineno - 1, node.col_offset
        end_line, end_col = node.end_lineno - 1, node.end_col_offset
        if start_line == end_line:
            line = lines[start_line]
            lines[start_line] = line[:start_col] + new_segment + line[end_col:]
        else:
            first = lines[start_line][:start_col]
            last = lines[end_line][end_col:]
            lines[start_line : end_line + 1] = [first + new_segment + last]
        source = "".join(lines)
        lines = source.splitlines(keepends=True)
    return source


# frob:doc docs/guides/coordinator-scripts.md#strip_help_citations-cli
def main(argv: list[str] | None = None) -> int:
    """CLI entry point: rewrite (or, without `--apply`, diff-preview) every
    `src/frob/_cli_parsers/**/*.py` file with a help-string citation.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    root = Path("src/frob/_cli_parsers")
    changed = 0
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        new_text = rewrite_file(path)
        if new_text is None:
            continue
        old_text = path.read_text(encoding="utf-8")
        if new_text == old_text:
            continue
        changed += 1
        if args.apply:
            path.write_text(new_text, encoding="utf-8")
            logger.info("rewrote %s", path)
        else:
            diff = difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
            )
            logger.info("".join(diff))
    logger.info("files changed: %d", changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
