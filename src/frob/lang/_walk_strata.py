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

T-2187: that pairing is now ENFORCED, not just described here -- the
regex line scan (`_KEYWORD_ONLY_RE`/`_locate_declared_items`) only
LOCATES a span for a construct the grammar's own structured output
(`_declared_items`) already said exists; it never decides what exists on
its own, and a construct the locator cannot find fails the whole walk
closed (`walk_strata` returns `Err`) rather than silently returning
however many symbols the regex happened to match.
"""

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
    "resource": SymbolKind.CLASS,
    "boundary": SymbolKind.FUNCTION,
    "flow": SymbolKind.FUNCTION,
    "assert": SymbolKind.CONST,
    "assume": SymbolKind.CONST,
    "refine": SymbolKind.TYPE,
    "policy": SymbolKind.TYPE,
    "operation": SymbolKind.METHOD,
    "scenario": SymbolKind.METHOD,
}

# T-2187: `Module`'s (docs/strata's structured parse result, `frob.strata.
# _ast.Module`) list-valued field name -> the source keyword that
# introduces one entry of that field, for every construct whose id is a
# plain `id: str` (or `target: str` for refine) attribute -- used by
# `_declared_items` to build the grammar's own authoritative symbol list.
# `claims` (assert/assume) and `module` (the file's own name) are handled
# separately since their keyword is not a fixed 1:1 map of the field name.
_FIELD_TO_KEYWORD: tuple[tuple[str, str], ...] = (
    ("nodes", "node"),
    ("flows", "flow"),
    ("boundaries", "boundary"),
    ("stores", "store"),
    ("caches", "cache"),
    ("queues", "queue"),
    ("cdns", "cdn"),
    ("balancers", "balancer"),
    ("policies", "policy"),
    ("operations", "operation"),
    ("scenarios", "scenario"),
    ("resources", "resource"),
)

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

# T-2187: recognizes ONLY the leading keyword token, deliberately with NO
# identifier-capture group. The pre-T-2187 `_HEADER_RE` captured an
# identifier via `[A-Za-z_][A-Za-z0-9_]*` right after the keyword, which
# is wrong for any construct whose grammar-declared `id` is a quoted
# string literal -- `assume "weakness:CWE-78:claude_hooks" noflow ...`
# (real syntax, design/frob.strata) never matched at all, since `"` is
# not in the identifier character class. That silent miss, not a rare
# edge case, was the majority of the T-2187 measured drift (32 of 34
# `assert`/`assume` constructs in design/frob.strata alone). Per T-2187's
# own prohibition ("do NOT fix this by tightening _HEADER_RE"), the fix
# is not a smarter identifier regex -- it is demoting this pattern to a
# pure keyword RECOGNIZER: `_locate_declared_items` below matches the
# REST of the line against each declared item's own exact id text (from
# strata-core's structured parse), whatever shape that text has (bare
# ident or quoted literal), rather than re-deriving an id from the line
# via regex.
_KEYWORD_ONLY_RE = re.compile(
    r"^(module|node|store|queue|cache|cdn|balancer|resource|boundary|flow"
    r"|assert|assume|refine|policy|operation|scenario)\b"
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


# frob:ticket T-2187
def _declared_items(parsed_ok: dict) -> list[tuple[str, str]]:
    """`(keyword, exact_id_text)` for every top-level construct strata-core's
    structured parse declares -- the GRAMMAR's authoritative symbol list
    (T-2187), in place of the pre-T-2187 approach of deriving the symbol
    list from which lines a regex happens to match. `id_text` is each
    construct's own `id`/`target` field VERBATIM (a quoted string stays
    quoted) -- `_locate_declared_items` matches this exact text against
    source lines, so no re-derivation of an identifier shape ever happens
    on the regex side.

    `refine`'s nested `nodes`/`flows` (a `refine X into { node A ... }`
    block) are DELIBERATELY not flattened in here -- they are not
    top-level `Module` symbols (`RefineDecl` holds its own private
    `nodes`/`flows`, per `frob.strata._ast.Module`'s shape) and no
    construct in this repo's own `.strata` corpus uses `refine` today
    (verified: `git grep -c '^refine ' -- '*.strata'` is 0 repo-wide) --
    `_locate_declared_items`'s fail-closed behavior is what covers this
    case if it is ever exercised, rather than an unverified nested-scan
    implementation."""
    items: list[tuple[str, str]] = []
    if parsed_ok.get("name"):
        items.append(("module", parsed_ok["name"]))
    for field, keyword in _FIELD_TO_KEYWORD:
        for entry in parsed_ok.get(field, ()):
            items.append((keyword, entry["id"]))
    for entry in parsed_ok.get("refines", ()):
        items.append(("refine", entry["target"]))
    for entry in parsed_ok.get("claims", ()):
        items.append(("assume" if entry.get("assumed") else "assert", entry["id"]))
    return items


# frob:ticket T-2187
def _locate_declared_items(
    lines: list[str], declared: list[tuple[str, str]]
) -> tuple[tuple[RawSymbol, ...], list[tuple[str, str]]]:
    """Match every entry of `declared` (grammar-authoritative) to its own
    header line in `lines`, building the real `RawSymbol` span/tokens for
    each -- returns `(symbols, unmatched)`, where a non-empty `unmatched`
    means `walk_strata` must fail closed (T-2187): the grammar declared a
    construct this line-locator could not find, which is exactly the
    silent-disagreement shape this ticket exists to close, never a
    partial/best-effort symbol list.

    `remaining` is consumed IN DECLARATION ORDER per keyword (first
    unconsumed declared item of a matched keyword wins) -- sound because
    `strata-core` rejects duplicate top-level ids at parse time (a source
    file that reaches here already has unique `(keyword, id)` pairs
    within each construct family), so first-available-match is
    unambiguous, not merely convenient."""
    remaining = list(declared)
    out: list[RawSymbol] = []
    module_name: str | None = None
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        kw_match = _KEYWORD_ONLY_RE.match(line)
        if kw_match is None:
            idx += 1
            continue
        keyword = kw_match.group(1)
        rest = line[kw_match.end() :].lstrip()
        located_at = next(
            (
                i
                for i, (d_keyword, d_id) in enumerate(remaining)
                if d_keyword == keyword and _rest_starts_with_id(rest, d_id)
            ),
            None,
        )
        if located_at is None:
            # A keyword-shaped line that does not correspond to any
            # remaining declared item. Never fabricated into a symbol --
            # either it is legitimately nested inside an already-located
            # `refine` block's span (skipped below via `end_idx` advance,
            # since a refine's own span already consumed those lines) or
            # it is a genuine mismatch the caller's `unmatched` return
            # would not itself catch (only OMISSIONS are tracked, never
            # extras) -- left for a future ticket if this repo's corpus
            # ever exercises `refine` nesting; see `_declared_items`.
            idx += 1
            continue
        _keyword, ident = remaining.pop(located_at)
        end_idx = _find_block_end(lines, idx)
        span = (idx + 1, end_idx + 1)
        qualname = (
            f"{module_name}.{ident}" if module_name and keyword != "module" else ident
        )
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
        idx = end_idx + 1
    return tuple(out), remaining


def _rest_starts_with_id(rest: str, id_text: str) -> bool:
    """Whether `rest` (the line after its leading keyword) begins with the
    construct `id_text` names, followed by a non-identifier boundary
    (whitespace, `{`, `:`, or end of string).

    `id_text` may be a bare identifier OR the CONTENTS of a quoted string
    literal (T-2187: `assume "weakness:CWE-78:claude_hooks" noflow ...` is
    real syntax) -- strata-core's structured output strips the surrounding
    `"..."` from a string-literal id (measured: `entry["id"]` is
    `weakness:CWE-78:claude_hooks`, no quotes), but the SOURCE line still
    has them, so a bare `rest.startswith(id_text)` never matches a
    string-literal id at all. Try the source's own quoted spelling first
    (a string-literal id can itself contain arbitrary text, so checking
    the quoted form first avoids a false partial-match against an
    embedded substring) and fall back to the bare form for a plain
    identifier id."""
    quoted = f'"{id_text}"'
    if rest.startswith(quoted):
        tail = rest[len(quoted) :]
        return tail == "" or not (tail[0].isalnum() or tail[0] == "_")
    if rest.startswith(id_text):
        tail = rest[len(id_text) :]
        return tail == "" or not (tail[0].isalnum() or tail[0] == "_")
    return False


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
# frob:ticket T-2187
def walk_strata(
    source: str,
) -> Result[tuple[tuple[RawSymbol, ...], tuple[RawComment, ...]], str]:
    """Validate `source` with strata-core, then extract symbols and comments.

    strata-core's parser is the correctness oracle (it rejects anything
    that is not real strata syntax); this walker never runs on text
    strata-core itself would reject -- a parse rejection comes back as
    `Err(message)` rather than a raised exception, matching the typani
    Result-at-the-boundary convention every other `frob.lang` entry point
    follows.

    T-2187: the returned symbols are no longer a line-regex's own guess at
    what exists -- `_declared_items` reads the GRAMMAR's structured
    output (`parsed["ok"]`) for the authoritative `(keyword, id)` list,
    and `_locate_declared_items` only uses the line scan to find each
    declared item's own SPAN (strata-core's kernel facts are span-free by
    design, docs/strata/kernel.md, so a span still has to come from
    somewhere). Any declared construct the locator cannot find a header
    line for is a fail-CLOSED `Err`, never a symbol set silently missing
    it and never the old behavior of logging a mismatch and returning the
    regex's own (possibly wrong) count anyway -- see docs/modules/lang.md
    #extraction-api's strata note for the full rationale and the T-2156
    precedent this mirrors (a resolved/verified fact wins over a
    plausible-looking guess, or the walk refuses outright)."""
    if strata_core is None:
        return Err(NATIVE_UNAVAILABLE_MESSAGE)
    parsed = json.loads(strata_core.parse_source(source))
    if "err" in parsed:
        return Err(_reject(parsed["err"]))

    lines = source.splitlines()
    declared = _declared_items(parsed["ok"])
    symbols, unmatched = _locate_declared_items(lines, declared)
    if unmatched:
        message = (
            f"strata-core declared {len(unmatched)} construct(s) this walker's "
            f"header locator could not find a source line for: "
            f"{[f'{kw} {ident}' for kw, ident in unmatched]} -- refusing rather "
            f"than returning an incomplete symbol set (T-2187)"
        )
        _log.error("strata walk: %s", message)
        return Err(message)
    comments = _extract_comments(lines, symbols)
    _log.debug("strata walk: %d symbols, %d comments", len(symbols), len(comments))
    return Ok((symbols, comments))
