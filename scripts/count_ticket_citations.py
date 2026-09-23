"""Count `T-####` ticket citations in user-facing surfaces (T-5134).

WHY THIS EXISTS. The owner directive of 2026-09-20 removes ticket prose
from everything a user reads (argparse `--help` output, docs/ prose) and
keeps citations only in the ledger, done-reports, commit messages, and
`frob:ticket`/`frob:todo` directive comments. This script is the single
measurement both the removal work and DOC013 (the recurrence-guard lint)
rely on, so "before" and "after" counts in a done-report always come from
the same code path as the gate that keeps the count at zero going forward.

Two scopes:

* `--scope help` -- AST-walks `src/frob/_cli_parsers/**/*.py` for the
  `help=`/`description=`/`epilog=` keyword of any call, plus the one
  known argparse-help-returning helper (`_deprecated_skip_help`), and
  counts `T-####` tokens inside those string literals only -- NOT
  docstrings or `#` comments, which are T-4691's scope (source comment
  narrative), not this ticket's.
* `--scope docs` -- counts `T-####` tokens in `docs/**/*.md` prose lines,
  excluding `docs/audits/`, `docs/design/registry/`, and any line that is
  itself a `frob:` directive example (those cite the DSL grammar, not a
  real ticket).

Usage:
    uv run python scripts/count_ticket_citations.py --scope help
    uv run python scripts/count_ticket_citations.py --scope docs
    uv run python scripts/count_ticket_citations.py --scope docs --list
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

#: The `T-####` shape a real ticket citation takes; deliberately does not
#: match the literal placeholder `T-####` used in docs/ to describe the
#: grammar itself.
TICKET_RE = re.compile(r"\bT-\d{4}\b")

#: argparse keyword arguments whose string value renders straight into
#: `--help` output.
_HELP_KEYWORDS = frozenset({"help", "description", "epilog"})

#: Known helper functions whose *return value* (not their own docstring)
#: is passed as a `help=`/`description=`/`epilog=` argument elsewhere,
#: so a literal inside their body is just as user-facing as an inline
#: kwarg. Extend this set if another such helper is added.
_HELP_RETURNING_HELPERS = frozenset({"_deprecated_skip_help"})

#: docs/ subtrees exempt from the citation count: audit history and the
#: generated rule registry are allowed to name tickets verbatim.
_DOCS_EXEMPT_PREFIXES = ("docs/audits", "docs/design/registry")


def _literal_strings(node: ast.AST) -> list[str]:
    """Return every string constant folded into `node` (str/f-string/`+`)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        out: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                out.append(value.value)
        return out
    if isinstance(node, ast.BinOp):
        return _literal_strings(node.left) + _literal_strings(node.right)
    return []


# frob:doc docs/guides/coordinator-scripts.md#find_help_citations
def find_help_citations(root: Path) -> list[tuple[Path, int, str]]:
    """Return `(file, line, T-####)` for every citation in a help/description/
    epilog string literal (or `_HELP_RETURNING_HELPERS` body) under `root`.
    """
    hits: list[tuple[Path, int, str]] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg in _HELP_KEYWORDS:
                        for literal in _literal_strings(kw.value):
                            for match in TICKET_RE.finditer(literal):
                                hits.append((path, node.lineno, match.group(0)))
            elif (
                isinstance(node, ast.FunctionDef)
                and node.name in _HELP_RETURNING_HELPERS
            ):
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Return) and inner.value is not None:
                        for literal in _literal_strings(inner.value):
                            for match in TICKET_RE.finditer(literal):
                                hits.append((path, inner.lineno, match.group(0)))
    return hits


def _is_directive_line(stripped: str) -> bool:
    """True when `stripped` is documenting the `frob:` directive grammar
    itself (a DSL example), not citing a real ticket in prose.
    """
    return stripped.startswith("<!-- frob:") or stripped.startswith("frob:")


# frob:doc docs/guides/coordinator-scripts.md#find_docs_citations
def find_docs_citations(root: Path) -> list[tuple[Path, int, str]]:
    """Return `(file, line, T-####)` for every prose citation under
    `root` (docs/), excluding `_DOCS_EXEMPT_PREFIXES` and directive
    grammar examples.
    """
    hits: list[tuple[Path, int, str]] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.as_posix()
        if any(rel.startswith(prefix) for prefix in _DOCS_EXEMPT_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _is_directive_line(line.strip()):
                continue
            for match in TICKET_RE.finditer(line):
                hits.append((path, lineno, match.group(0)))
    return hits


# frob:doc docs/guides/coordinator-scripts.md#count_ticket_citations-cli
def main(argv: list[str] | None = None) -> int:
    """CLI entry point: print the citation count for `--scope`, `--list`
    each hit when requested. Exit code is always 0 (measurement, not a
    gate) -- DOC013 is the enforcement half.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("help", "docs"), required=True)
    parser.add_argument(
        "--list", action="store_true", help="print each citation, not just the count"
    )
    args = parser.parse_args(argv)

    if args.scope == "help":
        hits = find_help_citations(Path("src/frob/_cli_parsers"))
    else:
        hits = find_docs_citations(Path("docs"))

    logger.info("scope=%s count=%d", args.scope, len(hits))
    if args.list:
        for path, lineno, token in hits:
            logger.info("%s:%d: %s", path, lineno, token)
    print(len(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
