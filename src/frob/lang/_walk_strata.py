"""Strata symbol walker (docs/modules/lang.md extraction table, docs/strata/surface.md).

`.strata` design files have no tree-sitter grammar (`tree-sitter-strata`
does not exist -- docs/strata/roadmap.md phase 4 / T-0077's Done report).
strata-core's own parser (the Rust crate under `strata-core/`, exposed to
Python as `strata_core.parse_source`) already knows the real grammar and
is the sole source of truth for *which* top-level constructs a `.strata`
file declares -- reusing it here means this walker never has to
re-implement string/comment-aware tokenizing to decide "is this `{` real
code or inside a quoted predicate". What `parse_source` does *not* return
is line spans (docs/strata/kernel.md's kernel facts are span-free by
design), so this module pairs the parser's declared-id list with a
regex-driven line scan that locates each id's header line and, for
brace-delimited constructs, its matching close -- giving every construct a
concrete `RawSymbol` span without hand-rolling a second strata parser.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/lang/_walk_strata.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import importlib
import json
import re
from types import ModuleType

try:
    strata_core: ModuleType | None = importlib.import_module("strata_core")
except ImportError:  # pragma: no cover - environment-dependent
    # The native parser is a maturin-built extension present in dev venvs
    # but not in standalone tool installs; .strata parsing degrades to a
    # per-file Err instead of crashing every frob invocation (T-0133).
    strata_core = None
from typani import Err, Ok
from typani.result import Result

from frob.lang._common import (
    _collapse_ws,
    _find_enclosing_symbol,
    _find_following_symbol,
    _strip_comment_delims,
)
from frob.lang._models import RawComment, RawSymbol, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

# Every top-level decl keyword strata-core's parser accepts
# (strata-core/src/parse.rs's top-level dispatch table), mapped onto the
# five graph-generic `SymbolKind` buckets every other grammar collapses
# into. There is no natural fit for "infrastructure node" or "claim" in a
# vocabulary built for functions/classes/consts/types, so the mapping is a
# best-effort analogy: containers/infra -> CLASS, edges/contracts ->
# FUNCTION, invocable behaviors -> METHOD, static facts -> CONST,
# relationships -> TYPE.
_KEYWORD_KIND: dict[str, SymbolKind] = {
    "module": SymbolKind.CLASS,
    "node": SymbolKind.CLASS,
    "store": SymbolKind.CLASS,
    "queue": SymbolKind.CLASS,
    "cache": SymbolKind.CLASS,
    "cdn": SymbolKind.CLASS,
    "balancer": SymbolKind.CLASS,
    "boundary": SymbolKind.FUNCTION,
    "flow": SymbolKind.FUNCTION,
    "assert": SymbolKind.CONST,
    "assume": SymbolKind.CONST,
    "refine": SymbolKind.TYPE,
    "policy": SymbolKind.TYPE,
    "operation": SymbolKind.METHOD,
    "scenario": SymbolKind.METHOD,
}

# frob:doc docs/modules/lang.md#error-types
# Sentinel `Err` message `walk_strata` returns when `strata_core` is absent
# (T-0133) -- `frob.lang._parse_strata_file` matches on this exact string to
# distinguish "native parser not installed" (expected in standalone tool
# installs, log at debug) from a real strata syntax rejection (log at
# error). Kept as one constant so the two modules cannot drift apart.
NATIVE_UNAVAILABLE_MESSAGE = (
    "strata_core native extension unavailable; .strata parsing "
    "requires a dev install (make core) -- see T-0133"
)

_HEADER_RE = re.compile(
    r"^(module|node|store|queue|cache|cdn|balancer|boundary|flow"
    r"|assert|assume|refine|policy|operation|scenario)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)


def _code_only(line: str) -> str:
    """`line` with any trailing `// ...` comment stripped (no string-aware lexing)."""
    idx = line.find("//")
    return line if idx < 0 else line[:idx]


def _find_block_end(lines: list[str], start: int) -> int:
    """0-based end-line index for the construct starting at `lines[start]`.

    Brace-delimited constructs (`node x : trusted { ... }`) close when the
    running `{`/`}` count returns to zero; brace-free constructs (a single-
    line `boundary` or `assert`) end on their own start line.
    """
    header_code = _code_only(lines[start])
    if "{" not in header_code:
        # No opening brace on the header line itself -- a brace-free,
        # single-line construct (`boundary ...`, `assert ...`); do not
        # keep scanning forward, or the next construct's own `{` would be
        # mistaken for this one's block open.
        return start
    depth = 0
    for i in range(start, len(lines)):
        code = _code_only(lines[i])
        depth += code.count("{") - code.count("}")
        if depth <= 0:
            return i
    return len(lines) - 1


def _leading_doc_comment(lines: list[str], start: int) -> str:
    """Contiguous `//`-comment block directly above `lines[start]`, collapsed.

    A blank (or non-comment) line breaks the chain, matching the "directly
    above" convention every other grammar's `_leading_doc_comment` uses.
    """
    collected: list[str] = []
    i = start - 1
    while i >= 0 and lines[i].strip().startswith("//"):
        collected.append(_strip_comment_delims(lines[i].strip()))
        i -= 1
    collected.reverse()
    return _collapse_ws(" ".join(collected))


def _extract_symbols(lines: list[str]) -> tuple[RawSymbol, ...]:
    """One `RawSymbol` per matched top-level header line, module-qualified."""
    out: list[RawSymbol] = []
    module_name: str | None = None
    for idx, line in enumerate(lines):
        match = _HEADER_RE.match(line)
        if match is None:
            continue
        keyword, ident = match.group(1), match.group(2)
        end_idx = _find_block_end(lines, idx)
        span = (idx + 1, end_idx + 1)
        qualname = f"{module_name}.{ident}" if module_name else ident
        if keyword == "module":
            module_name = ident
        header_code = _code_only(line).split("{", 1)[0]
        body_code = " ".join(_code_only(text) for text in lines[idx : end_idx + 1])
        out.append(
            RawSymbol(
                qualname=qualname,
                kind=_KEYWORD_KIND[keyword],
                public=True,
                span=span,
                sig_tokens=tuple(header_code.split()),
                body_tokens=tuple(body_code.split()),
                doc_text=_leading_doc_comment(lines, idx),
            )
        )
    return tuple(out)


def _extract_comments(
    lines: list[str], symbols: tuple[RawSymbol, ...]
) -> tuple[RawComment, ...]:
    """One `RawComment` per whole-line `//` comment (trailing comments excluded)."""
    out: list[RawComment] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("//"):
            continue
        span = (idx + 1, idx + 1)
        text = _strip_comment_delims(stripped)
        out.append(
            RawComment(
                text=text,
                span=span,
                enclosing=_find_enclosing_symbol(span, symbols),
                following=_find_following_symbol(span, symbols),
            )
        )
    return tuple(out)


def _declared_count(ok: dict) -> int:
    """Total construct count strata-core's structured output declares.

    Every list-valued top-level key (`nodes`, `flows`, `claims`, ...) is one
    declared construct per entry, plus one for the `module` decl itself --
    used only as `walk_strata`'s regex-vs-real-parser drift check.
    """
    return sum(len(v) for v in ok.values() if isinstance(v, list)) + (
        1 if ok.get("name") else 0
    )


def _reject(err: dict) -> str:
    """Format a strata-core parse-error dict into the `Err` message string."""
    message = err.get("message", "parse error")
    _log.error(
        "strata-core rejected source at line=%s col=%s: %s",
        err.get("line"),
        err.get("col"),
        message,
    )
    return f"{message} (line {err.get('line')}, col {err.get('col')})"


# frob:doc docs/modules/lang.md#extraction-api
def walk_strata(
    source: str,
) -> Result[tuple[tuple[RawSymbol, ...], tuple[RawComment, ...]], str]:
    """Validate `source` with strata-core, then extract symbols and comments.

    strata-core's parser is the correctness oracle (it rejects anything
    that is not real strata syntax); this walker never runs on text
    strata-core itself would reject -- a parse rejection comes back as
    `Err(message)` rather than a raised exception, matching the typani
    Result-at-the-boundary convention every other `frob.lang` entry point
    follows. The declared-id count from strata-core's structured output
    (`_declared_count`) is logged against the regex-derived symbol count as
    a cheap drift check between the two -- a persistent mismatch would mean
    the header regex has fallen out of sync with the real grammar
    (strata-core/src/parse.rs's top-level keyword table).
    """
    if strata_core is None:
        return Err(NATIVE_UNAVAILABLE_MESSAGE)
    parsed = json.loads(strata_core.parse_source(source))
    if "err" in parsed:
        return Err(_reject(parsed["err"]))

    lines = source.splitlines()
    symbols = _extract_symbols(lines)
    comments = _extract_comments(lines, symbols)
    _check_declared_count_drift(symbols, parsed["ok"])
    _log.debug("strata walk: %d symbols, %d comments", len(symbols), len(comments))
    return Ok((symbols, comments))


def _check_declared_count_drift(
    symbols: tuple[RawSymbol, ...], parsed_ok: dict
) -> None:
    """Log a warning if the regex-derived symbol count disagrees with
    strata-core's declared-id count (a cheap drift check, see walk_strata)."""
    declared = _declared_count(parsed_ok)
    if len(symbols) != declared:
        _log.warning(
            "strata header-regex symbol count (%d) != strata-core declared count (%d)",
            len(symbols),
            declared,
        )
