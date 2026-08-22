"""Shared scanner-core primitives for `frob.vet._capability`'s per-language
capability scan (T-1420 LARGE001 split, portion 5, verbatim relocation --
see the T-1459 design ticket for the full seam analysis).

Holds the pieces every per-language binding-resolution module (python/
typescript/rust/c/kotlin) depends on and none of them own individually:
registry-derived pattern compilation (`_compile_patterns`/`_PATTERNS`,
`_compiled_capability_patterns`), comment/docstring/non-executable byte-
span computation, the needle-matching primitives, and the embedded-code
(python string literal hosting JS/HTML) detection family. Every name here
is re-exported unchanged through `frob.vet._capability`'s own module
namespace so this split is invisible to any external caller -- moved
verbatim, no behavior change.
"""

# frob:waive LARGE001 reason="T-1651-grade: this module's own docstring documents it \
# as T-1420's shared-primitives split -- pattern compilation, comment/docstring byte- \
# span computation, needle-matching, and embedded-code detection that EVERY per- \
# language binding module (python/typescript/rust/c/kotlin) depends on and none owns \
# individually. This is the single shared substrate by design; splitting it would \
# either duplicate these primitives across the language modules or introduce a fresh \
# import cycle between two halves of what is one scanner core."

# frob:ticket T-1420
# frob:ticket T-1210
# frob:ticket T-1223
from __future__ import annotations

import bisect
import hashlib
import re
import threading
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from tree_sitter import Query, QueryCursor

from frob.lang import COMMENT_TYPES, node_text, raw_tree
from frob.logging import get_logger

from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation

_log = get_logger(__name__)

# extension -> language bucket used to pick a pattern table. T-0158 adds
# C/C++ (previously scanned honestly-empty) as a first-class bucket.
_EXT_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",  # same substring vocabulary; no dedicated JS grammar entry
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".rs": "rust",
    ".c": "c-cpp",
    ".h": "c-cpp",
    ".cc": "c-cpp",
    ".cpp": "c-cpp",
    ".cxx": "c-cpp",
    ".hpp": "c-cpp",
    ".hh": "c-cpp",
    ".kt": "kotlin",
    ".kts": "kotlin",
}


def _compile_patterns() -> dict[str, dict[str, tuple[str, ...]]]:
    """Build the language -> capability -> needle-tuple table FROM the
    single-source `DANGEROUS_OPERATIONS` registry (T-0158) -- this table is
    now a derived cache, never hand-maintained data. An entry with no
    `needles` (e.g. python `compile()`, handled by `_has_bare_compile_call`
    below) contributes no needle but still counts toward the registry's
    per-(kind, language) `operation_count`."""
    table: dict[str, dict[str, list[str]]] = {}
    for entry in DANGEROUS_OPERATIONS:
        by_kind = table.setdefault(entry.language, {})
        by_kind.setdefault(entry.capability_kind, [])
        by_kind[entry.capability_kind].extend(entry.needles)
    return {
        language: {kind: tuple(needles) for kind, needles in by_kind.items()}
        for language, by_kind in table.items()
    }


# capability -> substrings that, if present anywhere in the file's source
# text, mark the capability observed. Deliberately coarse (recall over
# precision): a false positive here just means an extra declaration line in
# [vet.allow]; a false negative is a missed attack. COMPILED from
# `_capability_registry.DANGEROUS_OPERATIONS` (T-0158) -- edit the registry,
# not this table.
_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = _compile_patterns()


ByteSpan = tuple[int, int]


# frob:ticket T-1223
#: Process-lifetime memo of compiled `(comment-type) @c` alternation Queries,
#: keyed by `language_label` (T-1223: the interim zero-Rust half of the
#: report's Rust-migration candidate #1 -- replace the Python-recursion span
#: walk with a tree-sitter Query captured in C). A `Query` is bound to the
#: `tree_sitter.Language` instance it was compiled against, but two
#: `Language` instances for the SAME grammar/ABI are interchangeable for
#: `QueryCursor.captures` purposes (verified: compiling against one file's
#: `tree.language` and running the cursor over an unrelated file's tree of
#: the same grammar returns identical results) -- so the first tree seen for
#: a given `language_label` compiles the Query once, and every later file of
#: that language reuses it. Not keyed by `id(tree.language)`: `frob.lang`
#: does not itself cache `Language` objects across `_parse` calls, so a
#: per-instance cache would never hit past the first file.
_comment_query_cache: dict[str, QueryCursor] = {}
_comment_query_cache_lock = threading.Lock()


def _comment_query_for(tree, language_label: str, comment_types: frozenset[str]):  # noqa: ANN001, ANN201
    """The cached `QueryCursor` for `language_label`'s comment-node
    alternation, compiling a new one against `tree.language` on first use
    (T-1223). `comment_types` (already looked up by the caller) becomes a
    `(type_a) @c\\n(type_b) @c ...` query source -- one capture per comment
    node type this grammar has (rust has two, most grammars have one)."""
    with _comment_query_cache_lock:
        cached = _comment_query_cache.get(language_label)
        if cached is not None:
            return cached
    query_src = "\n".join(f"({node_type}) @c" for node_type in sorted(comment_types))
    cursor = QueryCursor(Query(tree.language, query_src))
    with _comment_query_cache_lock:
        _comment_query_cache.setdefault(language_label, cursor)
        return _comment_query_cache[language_label]


def _comment_byte_spans_from_tree(tree, language_label: str) -> list[ByteSpan]:  # noqa: ANN001
    """Byte-range spans of every tree-sitter COMMENT node in an already-
    parsed `tree` (T-1210 split out of `_non_executable_byte_spans` so a
    single per-file parse can feed both the comment and docstring walks
    without re-invoking `raw_tree`; T-1223: the walk itself now runs as a
    tree-sitter Query capture in C instead of a per-node Python recursion --
    measured ~3x faster over this repo's own `src/**/*.py` + `frob-core/
    **/*.rs` files, 0 mismatches against the prior walk's output). Returns
    `[]` when `frob.lang` has no comment vocabulary registered for
    `language_label` at all."""
    comment_types = COMMENT_TYPES.get(language_label)
    if not comment_types:
        return []

    cursor = _comment_query_for(tree, language_label, comment_types)
    captures = cursor.captures(tree.root_node)
    return [(node.start_byte, node.end_byte) for node in captures.get("c", [])]


#: Sentinel second element for the `bisect` probe key in `_fully_in_any_span`
#: below -- larger than any real byte offset this module ever sees, so
#: `(start, _SPAN_PROBE_INF)` sorts after every real `(start, real_end)`
#: pair sharing the same start byte (T-1210).
_SPAN_PROBE_INF = 1 << 62


def _fully_in_any_span(start: int, end: int, spans: tuple[ByteSpan, ...]) -> bool:
    """True if the byte range `[start, end)` is fully covered by one span in
    `spans` (T-0209: the comment-containment test every needle hit passes
    through before it counts as an observation).

    T-1210: `spans` is now always produced by `_non_executable_byte_spans`,
    sorted by start byte and internally disjoint (a comment node and a
    docstring `string` node can never overlap in the same parse tree), so
    containment reduces to one `bisect` lookup rather than a linear `any()`
    scan over every span for every candidate (report candidate #5: 7.8M
    genexpr steps in `sys` alone measured pre-fix). Probing with `(start,
    _SPAN_PROBE_INF)` finds the insertion point one PAST every span whose
    own start is `<= start` in a single lookup, without materializing a
    parallel starts array per call -- `bisect` compares `ByteSpan` 2-tuples
    lexicographically, so this needs no custom key function. A caller that
    (unusually) passes an unsorted/overlapping `spans` tuple of its own
    would get a wrong answer here; every call site in this module goes
    through `_non_executable_byte_spans`, which guarantees the
    precondition."""
    if not spans:
        return False
    idx = bisect.bisect_right(spans, (start, _SPAN_PROBE_INF)) - 1
    if idx < 0:
        return False
    span_start, span_end = spans[idx]
    return span_start <= start and end <= span_end


# frob:ticket T-1223
#: The python docstring Query source (T-1223): every module/class/function
#: body whose FIRST named child is a bare `string` node, or an
#: `expression_statement` wrapping one -- mirrors the exact shape
#: `_py_leading_docstring_node` (pre-T-1223) tested node-by-node in Python.
#: NOTE: `expression_statement` is a tree-sitter-python SUPERTYPE, not a
#: concrete node kind -- it also matches concrete nodes like `assignment`
#: (verified: `(expression_statement (string) @doc)` alone spuriously
#: captured an enum member's VALUE string, e.g. `NotADirectory = "..."`,
#: because `assignment` conforms to the `expression_statement` supertype
#: and its own `string` child satisfies the inner pattern). `_PY_DOC_CAPTURE
#: _FILTER` below is the required post-filter closing that gap: a capture
#: only counts as a real docstring if its immediate parent's own `.type` is
#: literally `"module"`, `"block"` (the bare-string case), or
#: `"expression_statement"` (the wrapped case) -- never `"assignment"` or
#: any other expression_statement-conforming concrete kind.
_PY_DOCSTRING_QUERY_SRC = """
(module . (string) @doc)
(module . (expression_statement (string) @doc))
(function_definition body: (block . (string) @doc))
(function_definition body: (block . (expression_statement (string) @doc)))
(class_definition body: (block . (string) @doc))
(class_definition body: (block . (expression_statement (string) @doc)))
"""

#: Concrete parent `.type` values that make a `_PY_DOCSTRING_QUERY_SRC`
#: capture a REAL docstring rather than a supertype false-positive (see that
#: constant's docstring) -- `"module"`/`"block"` cover the bare-string
#: anchor patterns, `"expression_statement"` covers the wrapped ones.
_PY_DOC_CAPTURE_FILTER = frozenset({"module", "block", "expression_statement"})

_docstring_query_cache: QueryCursor | None = None
_docstring_query_cache_lock = threading.Lock()


def _docstring_query_for(tree):  # noqa: ANN001, ANN201
    """The cached `QueryCursor` for `_PY_DOCSTRING_QUERY_SRC`, compiled
    against `tree.language` on first use (T-1223) -- one process-lifetime
    Query shared by every python file's docstring-span extraction, same
    caching shape as `_comment_query_for`."""
    global _docstring_query_cache
    with _docstring_query_cache_lock:
        if _docstring_query_cache is None:
            _docstring_query_cache = QueryCursor(
                Query(tree.language, _PY_DOCSTRING_QUERY_SRC)
            )
        return _docstring_query_cache


def _docstring_byte_spans_from_tree(tree, language_label: str) -> list[ByteSpan]:  # noqa: ANN001
    """Byte-range spans of every module/class/function-head docstring
    STRING node in an already-parsed `tree` (T-0769; T-1210 split out of
    `_non_executable_byte_spans` for the shared-parse fix; T-1223: the walk
    itself now runs as a tree-sitter Query capture in C instead of a
    per-node Python recursion -- see `_comment_byte_spans_from_tree`'s
    docstring for the measured speedup and `_PY_DOCSTRING_QUERY_SRC`'s for
    the supertype false-positive this needed a post-filter for) -- python
    only, the only language this module extracts a docstring concept for. A
    docstring is a non-executable string constant; needle prose written
    there (fork/subprocess hazard documentation, e.g.) must not count as an
    observed capability any more than the same prose in a `#` comment would
    (see module docstring T-0769 entry for the false-positive this closes).
    Returns `[]` for any non-python `language_label`."""
    if language_label != "python":
        return []

    cursor = _docstring_query_for(tree)
    captures = cursor.captures(tree.root_node)
    return [
        (node.start_byte, node.end_byte)
        for node in captures.get("doc", [])
        if node.parent is None or node.parent.type in _PY_DOC_CAPTURE_FILTER
    ]


#: Process-lifetime memo for `_non_executable_byte_spans`, keyed on
#: `(str(path), sha256(source).hexdigest())` -- the same content-hash-keyed
#: shape as `frob.lang`'s own `_parse_cache` (T-0414), never mtime/size, so
#: a content change always misses and a byte-identical revisit always hits
#: regardless of which caller (gate, path) asks first (T-1210). Before this,
#: `sys`+`opaque` each independently re-walked the SAME file's comment and
#: docstring node trees once per public entry point that touches it
#: (`scan_file_capabilities`, `_scan_file_operations`, `_scan_file_
#: fingerprints`, `_opaque_indirection_findings`, `non_executable_line_
#: numbers` -- five call sites in `_capability.py` alone, each independently
#: recomputing the same spans for the same file within one `frob check`
#: run). Guarded by a lock for the same reason `_parse_cache` is: gate
#: stages run concurrently in a `ThreadPoolExecutor`.
_span_cache_lock = threading.Lock()
_span_cache: dict[tuple[str, str], tuple[ByteSpan, ...]] = {}


def _non_executable_byte_spans(path: Path) -> tuple[ByteSpan, ...]:
    """Every byte span in `path` that is prose, not executable code (T-0769):
    tree-sitter comment spans (T-0209) unioned with python docstring spans
    (T-0769 above), SORTED by start byte (T-1210 -- `_fully_in_any_span`'s
    bisect containment check requires this). Every raw-text needle-scan
    call site in this module that used to exclude comment spans alone now
    excludes this union instead -- a needle hit fully inside either kind of
    span is documentation describing an operation, never the operation
    itself.

    T-1210: memoized per `(path, content-hash)` in `_span_cache` -- a single
    `raw_tree` parse (itself already `frob.lang`-cached, T-0414) now backs
    ONE comment walk and ONE docstring walk per distinct file content for
    the whole process lifetime, shared across every caller (`sys`'s three
    entry points, `opaque`'s one, `non_executable_line_numbers`) instead of
    each independently re-walking the same tree. Returns `()` (never
    filters anything, same degrade-gracefully posture as before) when
    `path` fails to parse or `frob.lang` has no grammar for its
    extension."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, source, language_label = parsed.danger_ok

    key = (str(path), hashlib.sha256(source).hexdigest())
    with _span_cache_lock:
        cached = _span_cache.get(key)
    if cached is not None:
        return cached

    spans = tuple(
        sorted(
            _comment_byte_spans_from_tree(tree, language_label)
            + _docstring_byte_spans_from_tree(tree, language_label)
        )
    )
    with _span_cache_lock:
        _span_cache[key] = spans
    return spans


#: operator bytes a needle-to-regex conversion treats as "whitespace may
#: surround this" (T-0400 audit finding #3: `shell=True` evaded by
#: `shell = True`, `yaml.load(` evaded by `yaml.load (x)`).
_NEEDLE_WS_OPERATORS = frozenset(b"=(),")


@lru_cache(maxsize=None)
def _needle_to_ws_pattern(needle: bytes) -> re.Pattern[bytes]:
    """Compile `needle` into a regex tolerant of whitespace runs anywhere in
    the needle, plus whitespace surrounding `=`/`(`/`)`/`,` (T-0400: closes
    the whitespace-formatting evasion class for CVE fingerprint needles --
    `subprocess.run(cmd, shell = True)` still matches the `shell=True`
    needle). Cached: called once per (needle, file) pair across a scan."""
    parts: list[bytes] = []
    for byte in needle:
        ch = bytes([byte])
        if ch.isspace():
            parts.append(rb"\s*")
        elif byte in _NEEDLE_WS_OPERATORS:
            parts.append(rb"\s*" + re.escape(ch) + rb"\s*")
        else:
            parts.append(re.escape(ch))
    return re.compile(b"".join(parts))


def _needle_hits_outside_comments_ws(
    haystack: bytes, needle: bytes, comment_spans: tuple[ByteSpan, ...]
) -> bool:
    """Whitespace-tolerant sibling of `_needle_hits_outside_comments`
    (T-0400): matches `needle` via `_needle_to_ws_pattern` instead of a
    literal substring search, so cosmetic re-formatting (added/removed
    spaces around `=`/`(`) cannot silently evade a needle. Same
    comment-span exclusion semantics -- every match is checked, not just
    the first."""
    pattern = _needle_to_ws_pattern(needle)
    for match in pattern.finditer(haystack):
        if not _fully_in_any_span(match.start(), match.end(), comment_spans):
            return True
    return False


def _needle_hits_outside_comments(
    haystack: bytes, needle: bytes, comment_spans: tuple[ByteSpan, ...]
) -> bool:
    """True if `needle` occurs in `haystack` at least once outside every span
    in `comment_spans` (T-0209). Every occurrence is checked, not just the
    first -- a needle can appear once in a comment and again in real code,
    and the comment occurrence must not mask the real one."""
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            return False
        end = idx + len(needle)
        if not _fully_in_any_span(idx, end, comment_spans):
            return True
        start = idx + 1


# frob:ticket T-0882
def _needle_hits_as_bare_call(
    haystack: bytes, needle: bytes, comment_spans: tuple[ByteSpan, ...]
) -> bool:
    """Sibling of `_needle_hits_outside_comments` for a needle that must be a
    BARE builtin call, not merely a substring (T-0882, same class as T-0151's
    `_has_bare_compile_call`): an occurrence only counts when the byte
    immediately before it is neither an identifier character nor `.`. A plain
    substring match on a call-shaped needle like `eval(`/`exec(` fires on any
    identifier that merely ENDS with that text -- e.g. `_mutation_for_eval(`,
    a function NAME, not a real `eval` call site -- and the `.`-exclusion
    additionally keeps a dotted method access (`obj.exec(`) from counting as
    the bare builtin. `_BARE_CALL_NEEDLES` names which needle strings route
    through this stricter check instead of `_needle_hits_outside_comments`."""
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            return False
        end = idx + len(needle)
        prev = haystack[idx - 1 : idx] if idx > 0 else b""
        is_bare = prev != b"." and not _is_identifier_byte(prev)
        if is_bare and not _fully_in_any_span(idx, end, comment_spans):
            return True
        start = idx + 1


# T-0244: embedded-code blind spot. Every needle table above only ever
# scans a file's OWN source-grammar text; a large HTML/JS-shaped STRING
# LITERAL sitting inside a Python module (the malmberg pilot P3 shape -- a
# 5400-line dashboard's markup/script embedded as a python string) is
# structurally invisible to it. The functions below detect such a region
# (a size + HTML/JS-signal heuristic over python tree-sitter `string`
# nodes) and ALWAYS emit the `embedded_code` capability kind for a region
# found, independent of whether the best-effort typescript-needle re-scan
# over the region's own text turns up anything specific -- fail-closed per
# docs/design/structural-linter-adversarial-hardening.md rule 3: the
# region is declared, never silently passed, even when the re-scan is
# empty. Python only for this pass (the ticket's own reported shape);
# extending detection to other host languages embedding HTML/JS strings is
# a documented follow-up, not attempted here.

#: minimum embedded-string byte length before the heuristic even looks at
#: signal tokens (T-0244) -- short strings (an error message, a single CSS
#: class name) are never worth the false-positive cost.
_EMBEDDED_CODE_MIN_LEN = 200

#: HTML/JS signal tokens (T-0244), checked case-insensitively: a candidate
#: STRING node's content must contain at least one before it counts as
#: "looks like embedded HTML/JS". Deliberately coarse (recall over
#: precision, same posture as every needle table above): a false positive
#: costs one `[vet.allow]` declaration line; a false negative hides a real
#: embedded exec surface.
_EMBEDDED_CODE_SIGNALS: tuple[bytes, ...] = (
    b"<script",
    b"<html",
    b"<!doctype",
    b"<body",
    b"<div",
    b"document.",
    b"window.",
    b"addeventlistener",
    b"innerhtml",
)


def _looks_like_embedded_code(text: bytes) -> bool:
    """True if `text` is at least `_EMBEDDED_CODE_MIN_LEN` bytes AND
    contains at least one `_EMBEDDED_CODE_SIGNALS` token, case-
    insensitively (T-0244) -- the size+signal heuristic gating embedded-
    code-region detection."""
    if len(text) < _EMBEDDED_CODE_MIN_LEN:
        return False
    lowered = text.lower()
    return any(signal in lowered for signal in _EMBEDDED_CODE_SIGNALS)


def _string_content_bytes(node) -> bytes:  # noqa: ANN001 -- tree_sitter.Node
    """The literal content bytes of a python `string` node, joined across
    its `string_content` children -- excludes the quote/prefix tokens
    tree-sitter keeps as siblings (T-0244, mirrors `_python_docstring`'s
    identical join in `frob.lang._walk_python`)."""
    return b"".join(
        node_text(child).encode("utf-8")
        for child in node.children
        if child.type == "string_content"
    )


def _embedded_code_regions(path: Path) -> tuple[bytes, ...]:
    """Every python STRING node's content in `path` that looks like
    embedded HTML/JS (T-0244: `_looks_like_embedded_code`) -- the region
    text `_embedded_capabilities`/`_embedded_operations` re-scan below.
    Returns `()` when `path` fails to parse, is not python, or has no
    candidate STRING node -- never raises. A matched string node's own
    children are not walked further (its content is text, not nested
    syntax to re-descend into)."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "python":
        return ()

    regions: list[bytes] = []

    def walk(node) -> None:  # noqa: ANN001
        if node.type == "string":
            content = _string_content_bytes(node)
            if _looks_like_embedded_code(content):
                regions.append(content)
            return
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return tuple(regions)


def _embedded_capabilities(path: Path) -> set[str]:
    """T-0244: capability kinds contributed by embedded HTML/JS string
    literals in `path` -- always includes `embedded_code` for each region
    found (fail-closed declaration, independent of the re-scan below),
    plus whatever the typescript needle table's best-effort re-scan turns
    up over each region's own text (`html_render`/`eval`/`fetch_url`/...
    when the embedded markup/script itself matches a JS/TS registry
    needle). Comment-span filtering does not apply to a region's own text
    (T-0209 spans are computed over `path`'s python grammar, not the
    embedded JS/HTML grammar) -- an embedded needle hit inside what would
    be a JS comment is not excluded, same recall-over-precision posture as
    every other needle table here."""
    regions = _embedded_code_regions(path)
    if not regions:
        return set()
    found: set[str] = {"embedded_code"}
    ts_table = _PATTERNS.get("typescript", {})
    for region in regions:
        found |= _matched_capabilities(region, ts_table, "typescript", ())
    if found - {"embedded_code"}:
        _log.info(
            "vet: %s: embedded-code region capabilities observed: %s",
            path,
            sorted(found),
        )
    else:
        _log.info(
            "vet: %s: embedded-code region found, opaque to needle re-scan "
            "-- declared as embedded_code (fail-closed)",
            path,
        )
    return found


def _embedded_operations(path: Path) -> list[_DangerousOperation]:
    """T-0244 sibling of `_embedded_capabilities` for the richer
    `_scan_file_operations` entry point: every typescript-language
    `DANGEROUS_OPERATIONS` entry whose needle(s) match inside an embedded
    HTML/JS string-literal region of `path`, so an audit finding can still
    cite the library/rationale/safer_alternative for a dangerous operation
    that only exists inside the embedded content. No comment-span
    filtering (same reasoning as `_embedded_capabilities`). Each entry
    appears at most once, in registry order."""
    regions = _embedded_code_regions(path)
    if not regions:
        return []
    matched: list[_DangerousOperation] = []
    seen: set[_DangerousOperation] = set()
    for region in regions:
        for entry in DANGEROUS_OPERATIONS:
            if entry.language != "typescript" or entry in seen:
                continue
            if _operation_entry_matches(entry, region, ()):
                matched.append(entry)
                seen.add(entry)
    return matched


def _is_identifier_byte(byte: bytes) -> bool:
    """True if the single byte `byte` (`b""` at a string boundary) is part of
    an identifier -- alphanumeric or underscore. Shared by `_has_word_
    boundary_napi`'s left/right boundary tests."""
    return bool(byte) and (byte.isalnum() or byte == b"_")


def _has_word_boundary_napi(text: bytes, comment_spans: tuple[ByteSpan, ...]) -> bool:
    """True if `napi` appears as its own identifier token (not embedded in a
    longer identifier), outside any comment span (T-0019, graphite adoption:
    the plain substring needle `"napi"` matched inside the ordinary word
    `"openapi"` -- every hit in graphite's `api.generated.ts`/`client.ts` was
    `o-p-e-n-[napi]`, openapi-typescript codegen, zero real node-ffi/ffi-napi
    usage). A hit only counts when neither the preceding nor the following
    byte is an identifier character, e.g. `require('napi')`, `napi-rs`,
    `ffi_napi` are still caught (non-identifier or absent boundary on both
    sides), but `openapi`/`OpenAPI` never match (preceding byte `e` is
    alphanumeric). Mirrors T-0151's `_has_bare_compile_call` precedent for
    the same "needle is a substring of an unrelated word" false-positive
    class."""
    needle = b"napi"
    idx = 0
    while True:
        idx = text.find(needle, idx)
        if idx == -1:
            return False
        end = idx + len(needle)
        prev = text[idx - 1 : idx] if idx > 0 else b""
        nxt = text[end : end + 1]
        is_boundary = not _is_identifier_byte(prev) and not _is_identifier_byte(nxt)
        if is_boundary and not _fully_in_any_span(idx, end, comment_spans):
            return True
        idx += 1


def _has_bare_compile_call(text: bytes, comment_spans: tuple[ByteSpan, ...]) -> bool:
    """True if `compile(` appears as a bare builtin call, not a dotted method
    access like `re.compile(`/`ast.compile(` (T-0151: the builtin turning a
    code string into a code object is eval-adjacent; `re.compile(` is not,
    and was the entire source of this scanner's cross-file false positives),
    AND that occurrence is not fully inside a comment span (T-0209: same
    comment-exclusion every other needle now gets)."""
    needle = b"compile("
    idx = 0
    while True:
        idx = text.find(needle, idx)
        if idx == -1:
            return False
        end = idx + len(needle)
        prev = text[idx - 1 : idx] if idx > 0 else b""
        is_bare = prev != b"." and not (prev.isalnum() or prev == b"_")
        if is_bare and not _fully_in_any_span(idx, end, comment_spans):
            return True
        idx += len(needle)


# frob:ticket T-2457
def _matching_close_paren(text: bytes, open_idx: int) -> int | None:
    """The byte index of the `)` that closes the `(` at `open_idx`, or
    `None` if the file's syntax is malformed enough that no matching close
    is found before EOF (T-2457). A token-level scan, not a substring
    search: tracks nested `()`/`[]`/`{}` depth and skips over the contents
    of string literals (single/double/triple-quoted, backslash-escaped) so
    a stray paren or comma INSIDE a string/nested-call argument can never
    be mistaken for the call's own closing paren or a top-level argument
    boundary -- exactly the class of mistake a plain substring/regex match
    would make and the standing "parse, don't grep" rule this ticket
    exists to restore."""
    depth = 1
    idx = open_idx
    n = len(text)
    while idx < n:
        ch = text[idx : idx + 1]
        if ch in (b'"', b"'"):
            quote = ch
            # frob:waive PERF003 reason="single triple-quote byte comparison inside an outer while-loop; the nested while-loop below (string-content skip) is unrelated to this == and does not bound-var-match it -- PERF003 has a documented while-loop fallback gap (any == anywhere in body counted, no bound-var check possible for while)"  # noqa: E501
            triple = text[idx : idx + 3] == quote * 3
            qlen = 3 if triple else 1
            idx += qlen
            while idx < n:
                if text[idx : idx + 1] == b"\\":
                    idx += 2
                    continue
                if text[idx : idx + qlen] == quote * qlen:
                    idx += qlen
                    break
                idx += 1
            continue
        if ch in (b"(", b"[", b"{"):
            depth += 1
        elif ch in (b")", b"]", b"}"):
            depth -= 1
            if depth == 0:
                return idx
        idx += 1
    return None


# frob:ticket T-2457
def _top_level_arg_strings(text: bytes, args_start: int, args_end: int) -> list[bytes]:
    """Split one call's raw argument-list bytes (`text[args_start:args_end]`,
    NOT including the enclosing parens) into its top-level comma-separated
    argument substrings (T-2457), skipping over commas nested inside
    `()`/`[]`/`{}` or inside a string literal -- so `open(p, mode="r" if x
    else "w")` splits into exactly two arguments, not three."""
    args: list[bytes] = []
    depth = 0
    start = args_start
    idx = args_start
    n = args_end
    while idx < n:
        ch = text[idx : idx + 1]
        if ch in (b'"', b"'"):
            quote = ch
            # frob:waive PERF003 reason="single triple-quote byte comparison inside an outer while-loop; the nested while-loop below (string-content skip) is unrelated to this == and does not bound-var-match it -- PERF003 has a documented while-loop fallback gap (any == anywhere in body counted, no bound-var check possible for while)"  # noqa: E501
            triple = text[idx : idx + 3] == quote * 3
            qlen = 3 if triple else 1
            idx += qlen
            while idx < n:
                if text[idx : idx + 1] == b"\\":
                    idx += 2
                    continue
                if text[idx : idx + qlen] == quote * qlen:
                    idx += qlen
                    break
                idx += 1
            continue
        if ch in (b"(", b"[", b"{"):
            depth += 1
        elif ch in (b")", b"]", b"}"):
            depth -= 1
        elif ch == b"," and depth == 0:
            args.append(text[start:idx])
            start = idx + 1
        idx += 1
    tail = text[start:n].strip()
    if tail:
        args.append(tail)
    return args


#: Simple string-literal-content matcher: a plain (non-f-string, non-
#: concatenated) single/double/triple quoted literal with only ASCII
#: letters/`+` inside -- exactly the shape a real `open()` mode argument
#: ever legitimately takes ("r", "rb", "w", "a+", ...). Anything else
#: (an f-string, a variable, a ternary, a function call) does not match
#: and is treated as OPAQUE by `_open_call_mode` below.
_MODE_LITERAL_RE = re.compile(rb"""^[a-zA-Z]*\+?[a-zA-Z]*$""")


# frob:ticket T-2457
def _literal_mode_value(arg: bytes) -> bytes | None:
    """The bare content of `arg` if it is a plain quoted string literal
    holding a plausible file-open mode spelling (T-2457), else `None` for
    anything opaque (an f-string, a name, a call, string concatenation).
    `None` is the FAIL-CLOSED case: `_open_call_mode` treats an opaque
    mode expression as a possible write, never silently as a read."""
    arg = arg.strip()
    for quote in (b'"""', b"'''", b'"', b"'"):
        if arg.startswith(quote) and arg.endswith(quote) and len(arg) >= 2 * len(quote):
            inner = arg[len(quote) : len(arg) - len(quote)]
            if _MODE_LITERAL_RE.match(inner):
                return inner
            return None
    return None


class _OpenCallMode:
    """The three outcomes `_open_call_mode` classifies one `open(...)`/
    `Path.open(...)` call site into (T-2457): `READ` (mode is absent, or a
    literal containing neither `w`/`a`/`x`/`+`), `WRITE` (mode is a
    literal containing any of `w`/`a`/`x`/`+`), or `OPAQUE` (a mode
    argument is present but is not a plain string literal -- classified as
    WRITE by every caller here, fail-closed: a security detector's false
    negative is worse than its false positive, per this ticket's own
    acceptance criteria)."""

    READ = "read"
    WRITE = "write"
    OPAQUE = "opaque"


def _open_call_mode(text: bytes, call_end: int) -> str:
    """Classify the `open(`/`.open(` call whose `(` is the byte just
    before `call_end` (T-2457): reads the argument list, finds the mode
    argument (second positional, or a `mode=` keyword), and returns one of
    `_OpenCallMode`'s three outcomes. No mode argument at all means
    Python's own default (`"r"`), i.e. READ. A malformed/unterminated
    call (`_matching_close_paren` finds no match) is classified OPAQUE,
    fail-closed for the same reason an opaque mode expression is."""
    close = _matching_close_paren(text, call_end)
    if close is None:
        return _OpenCallMode.OPAQUE
    args = _top_level_arg_strings(text, call_end, close)
    mode_arg: bytes | None = None
    positional_idx = 0
    for arg in args:
        stripped = arg.strip()
        if stripped.startswith(b"mode") and re.match(rb"^mode\s*=", stripped):
            mode_arg = stripped.split(b"=", 1)[1]
            break
        if b"=" in stripped and re.match(rb"^[A-Za-z_]\w*\s*=", stripped):
            # a DIFFERENT keyword argument (e.g. buffering=, encoding=) --
            # does not count as a positional slot.
            continue
        if positional_idx == 1:
            mode_arg = stripped
            break
        positional_idx += 1
    if mode_arg is None:
        return _OpenCallMode.READ
    literal = _literal_mode_value(mode_arg)
    if literal is None:
        return _OpenCallMode.OPAQUE
    if any(c in literal for c in (b"w", b"a", b"x", b"+")):
        return _OpenCallMode.WRITE
    return _OpenCallMode.READ


# frob:ticket T-2457
def _open_call_sites(text: bytes, comment_spans: tuple[ByteSpan, ...]) -> list[str]:
    """Every `open(`/`.open(` call site's `_OpenCallMode` classification in
    `text`, outside `comment_spans` (T-2457) -- one entry per occurrence of
    the literal `open(` substring (both the bare builtin and a `Path.
    open(...)`/`some_stream.open(...)` method call: both take the same
    read/write mode argument shape, and the false-positive report this
    ticket fixes was itself a `Path.open("rb")` call), so a caller can ask
    "was ANY site a write" / "was ANY site a read" without re-scanning."""
    needle = b"open("
    modes: list[str] = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx == -1:
            break
        call_end = idx + len(needle)
        if not _fully_in_any_span(idx, call_end, comment_spans):
            modes.append(_open_call_mode(text, call_end))
        start = idx + 1
    return modes


# frob:ticket T-2457
def _has_write_mode_open_call(text: bytes, comment_spans: tuple[ByteSpan, ...]) -> bool:
    """True if any `open(`/`.open(` call site in `text` is write-mode or
    mode-opaque (T-2457's `fs-write` special check, registered in
    `_SPECIAL_CHECKS` below) -- the mode-aware replacement for the old bare
    `"open("` needle, which fired on every `open()` call regardless of
    mode."""
    return any(
        mode in (_OpenCallMode.WRITE, _OpenCallMode.OPAQUE)
        for mode in _open_call_sites(text, comment_spans)
    )


# frob:ticket T-2457
def _has_read_mode_open_call(text: bytes, comment_spans: tuple[ByteSpan, ...]) -> bool:
    """True if any `open(`/`.open(` call site in `text` is read-mode
    (T-2457's `fs-read` special check, registered in `_SPECIAL_CHECKS`
    below) -- a call with no mode argument (Python's own `"r"` default) or
    an explicit non-write literal mode counts; a mode-opaque call does
    NOT count here (it already counts toward `fs-write`, fail-closed --
    this function only asserts genuine, provable read-only access)."""
    return any(
        mode == _OpenCallMode.READ for mode in _open_call_sites(text, comment_spans)
    )


# language -> capability -> extra callable(text, comment_spans) -> bool,
# applied ON TOP of the plain substring needles above for needles that need
# one bit more context than "does this substring appear anywhere" (T-0151:
# `compile(` as a bare builtin call vs. `re.compile(`/`x.compile(` method
# access; T-0209: `comment_spans` lets the check apply the same
# comment-exclusion the plain needles get).
_SpecialCheck = Callable[[bytes, tuple[ByteSpan, ...]], bool]
_SPECIAL_CHECKS: dict[str, dict[str, tuple[_SpecialCheck, ...]]] = {
    "python": {
        "eval": (_has_bare_compile_call,),
        # T-2457: mode-aware open()/`.open()` classification replaces the
        # old bare "open(" needle (which fired for fs-write regardless of
        # read/write mode -- see module docstring / this ticket for the
        # false-positive this fixed).
        "fs-write": (_has_write_mode_open_call,),
        "fs-read": (_has_read_mode_open_call,),
    },
    # T-0019: "napi" needs identifier-boundary matching so it does not fire
    # inside the unrelated word "openapi" -- see _has_word_boundary_napi.
    "typescript": {"ffi": (_has_word_boundary_napi,)},
}

#: Registry needle strings (as UTF-8 bytes) that `_matched_capabilities`
#: routes through `_needle_hits_as_bare_call` instead of plain-substring
#: `_needle_hits_outside_comments` (T-0882). `eval(`/`exec(` are call-shaped
#: builtin needles -- unlike a dotted needle such as `ImageMath.eval(` or
#: `page.evaluate(` (also filed under the `eval` capability kind but never a
#: bare-identifier suffix hazard), a plain substring match on these two
#: fires on any identifier merely ENDING in that text (`_mutation_for_eval(`,
#: a function NAME). Keeping this as a needle-level opt-out here (rather
#: than editing the registry's needle tuple) leaves the registry's needle
#: text unchanged for `_scan_file_operations`'s verbatim citation.
# frob:ticket T-0882
_BARE_CALL_NEEDLES: frozenset[bytes] = frozenset({b"eval(", b"exec("})


_capability_pattern_cache: dict[int, tuple[tuple[str, re.Pattern[str]], ...]] = {}


def _compiled_capability_patterns(
    table: dict[str, tuple[str, ...]],
) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """One compiled alternation-of-needles regex per capability in `table`,
    cached by `id(table)` in `_capability_pattern_cache` (T-0829: `table` is
    always one of the fixed module-level `_PATTERNS[language]` dicts, never
    mutated or replaced after import, so the same object recurs on every
    call and compiling once amortizes across the whole scan; a plain dict
    keyed by identity is used instead of `functools.lru_cache` because
    `table` itself is an unhashable `dict` and cannot be an `lru_cache`
    argument). A capability with no needles is dropped -- `any(... for
    needle in ())` on the old per-needle loop was always `False`, so
    omitting it here changes nothing observable."""
    cached = _capability_pattern_cache.get(id(table))
    if cached is not None:
        return cached
    compiled = tuple(
        (capability, re.compile("|".join(re.escape(needle) for needle in needles)))
        for capability, needles in table.items()
        if needles
    )
    _capability_pattern_cache[id(table)] = compiled
    return compiled


def _matched_capabilities(
    text: bytes,
    table: dict[str, tuple[str, ...]],
    language: str,
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability tokens whose needle set appears anywhere in `text` outside
    a comment span (T-0209), plus any `_SPECIAL_CHECKS` hit for that
    language/capability (T-0151). A needle listed in `_BARE_CALL_NEEDLES`
    (T-0882: `eval(`/`exec(`) additionally requires a bare-builtin-call
    boundary, not just substring presence -- see `_needle_hits_as_bare_call`."""
    found: set[str] = set()
    for capability, needles in table.items():
        for needle in needles:
            needle_bytes = needle.encode("utf-8")
            hit = (
                _needle_hits_as_bare_call(text, needle_bytes, comment_spans)
                if needle_bytes in _BARE_CALL_NEEDLES
                else _needle_hits_outside_comments(text, needle_bytes, comment_spans)
            )
            if hit:
                found.add(capability)
                break
    for capability, checks in _SPECIAL_CHECKS.get(language, {}).items():
        # frob:waive PERF008 reason="check is the loop-bound variable itself (a \
        # DIFFERENT callable from _SPECIAL_CHECKS on every iteration of the inner \
        # for check in checks) -- this is dynamic dispatch to distinct functions \
        # sharing the same (text, comment_spans) args, not a repeated call to one \
        # fixed callable. PERF008's resolver treats the bare name 'check' as if it \
        # named one specific function; a resolver ambiguity, not a real redundant \
        # call to hoist. Tracked as a resolver precision follow-up \
        # (T-1041's Done report)"  # noqa: E501
        if any(check(text, comment_spans) for check in checks):
            found.add(capability)
    return found


# frob:ticket T-0882
# frob:ticket T-1433
def _operation_entry_matches(
    entry: _DangerousOperation, raw: bytes, comment_spans: tuple[ByteSpan, ...]
) -> bool:
    """Whether one `DANGEROUS_OPERATIONS` entry's needle(s) (or a special
    per-entry check) hit in `raw` outside `comment_spans`. T-0882: a needle
    in `_BARE_CALL_NEEDLES` (`eval(`/`exec(`) requires a bare-builtin-call
    boundary here too, the same rule `_matched_capabilities` applies -- an
    entry citing `eval(`/`exec(` must not fire on an identifier that merely
    ends with that text (`_mutation_for_eval(`).

    T-2457: needle hits and the special checks are OR'd, not mutually
    exclusive on "entry has needles" -- the `open()` (read-mode) entry
    keeps its own `"json.load("` needle AND is asked about mode-aware
    `open()`/`.open()` reads, so this per-entry path (`_scan_file_
    operations`, named-entry reporting) attributes a bare `open(p, "rb")`
    read to the SAME registry row `scan_file_capabilities`'s kind-only
    path reports it under, instead of going silent just because that row
    also happens to have a real needle of its own."""
    if entry.needles and any(
        (
            _needle_hits_as_bare_call(raw, needle.encode("utf-8"), comment_spans)
            if needle.encode("utf-8") in _BARE_CALL_NEEDLES
            else _needle_hits_outside_comments(
                raw, needle.encode("utf-8"), comment_spans
            )
        )
        for needle in entry.needles
    ):
        return True
    if entry.language == "python" and entry.function_or_pattern.startswith("compile("):
        return _has_bare_compile_call(raw, comment_spans)
    # T-2457: both `open()` entries (fs-write "write/append mode", fs-read
    # "read mode") are asked about mode-aware open()/`.open()` classifi-
    # cation regardless of their own needles, keeping this per-entry path
    # consistent with the kind-only `scan_file_capabilities` path's
    # `_SPECIAL_CHECKS` wiring on the same file.
    if entry.language == "python" and entry.function_or_pattern.startswith("open("):
        if entry.capability_kind == "fs-write":
            return _has_write_mode_open_call(raw, comment_spans)
        if entry.capability_kind == "fs-read":
            return _has_read_mode_open_call(raw, comment_spans)
    return False


# frob:ticket T-2507
_SEGMENT_SEP_RE = re.compile(r"::|\.")


# frob:ticket T-2507
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_family_prefix_still_re\
# aches_sibling_family
def _dotted_segments(target: str) -> list[str]:
    """Split a resolved identity or registry needle into its dotted
    segments (T-2507) -- `"::"` (rust/c++ path separator, e.g.
    `"std::process::Command::new"`) and `"."` (every other language this
    registry resolves: python/typescript/kotlin/c dotted-attribute form)
    are BOTH segment separators here, so `_needle_matches_resolved`'s
    boundary comparison works identically regardless of which resolver
    produced the string -- neither separator can appear inside a bare
    identifier segment in any of these languages, so this split is
    unambiguous."""
    return _SEGMENT_SEP_RE.split(target)


# frob:ticket T-2507
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_module_prefix_matches_\
# with_and_without_trailing_dot
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_call_target_matches_wi\
# th_and_without_trailing_paren
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_bare_identifier_matche\
# s_with_and_without_trailing_paren
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_family_prefix_still_re\
# aches_sibling_family
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_no_false_positive_on_m\
# odule_name_substring
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_no_false_positive_on_c\
# all_target_substring
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_no_false_positive_on_b\
# are_identifier_substring
# frob:tests \
# tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary.test_module_prefix_does_not\
# _match_unrelated_leading_segment
def _needle_matches_resolved(needle: str, resolved: str) -> bool:
    """True if `needle` (a registry needle string -- a bare identifier
    like `"Popen"`, a dotted module prefix like `"subprocess."`, a fully-
    dotted call target like `"os.system("`, or a dotted family prefix like
    `"os.exec"` meant to match the whole `os.exec*` sibling group) matches
    the RESOLVED dotted target `resolved` (e.g. `"subprocess.run"`) at
    DOTTED-SEGMENT boundaries, never by raw substring containment (T-2507:
    the prior `needle in resolved or needle in f"{resolved}("` form was
    wrong at boundaries in both directions -- needle `"net"` substring-hit
    resolved `"netrc"`/`"network_helper"`, and needle `"os.system("`
    could substring-hit an unrelated `"myos.system"`).

    The registry's own trailing punctuation on a needle is now REDUNDANT
    for every needle this registry actually declares (droppable without
    losing a single intended match -- the falsifiable proof this fix is
    real, not cosmetic) precisely because segment comparison already
    enforces the boundary the punctuation used to approximate by hand:

    - a trailing `"("` (a call target, e.g. `"os.system("`): stripped,
      then treated identically to the no-marker form below.
    - a trailing `"."` (a module prefix, e.g. `"subprocess."`): stripped,
      then treated as a single bare segment (module prefixes this
      registry declares are always one segment).
    - a bare SINGLE segment (e.g. `"Popen"`, `"subprocess"`, `"net"`):
      matches when it equals ANY of `resolved`'s dotted segments exactly
      (`"subprocess"` matches `"subprocess.run"` at position 0,
      `"Popen"` matches `"subprocess.Popen"` at position 1; `"net"` does
      NOT match `"netrc"` -- `"netrc"` is one whole segment, not equal
      to `"net"`).
    - a bare MULTI-segment needle (e.g. `"os.exec"`, meant to reach the
      whole `os.exec*` family -- `os.execv`, `os.execve`, ...): searched
      at every contiguous start offset in `resolved`'s segments; every
      segment but the last must equal exactly, and only the FINAL
      segment is a genuine prefix match (`"exec"` prefixes `"execv"`) --
      the one deliberately-loose rule this registry actually relies on,
      bounded to the last segment and still exact on every earlier one,
      never a blanket substring."""
    if needle.endswith("("):
        needle = needle[:-1]
    elif needle.endswith("."):
        needle = needle[:-1]
    needle_parts = _dotted_segments(needle)
    resolved_parts = _dotted_segments(resolved)
    needle_len, resolved_len = len(needle_parts), len(resolved_parts)
    if needle_len > resolved_len:
        return False
    if needle_len == 1:
        return needle_parts[0] in resolved_parts
    for start in range(resolved_len - needle_len + 1):
        window = resolved_parts[start : start + needle_len]
        if window[:-1] == needle_parts[:-1] and window[-1].startswith(needle_parts[-1]):
            return True
    return False


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0169
#: Every language bucket `_EXT_LANGUAGE` maps at least one extension to --
#: i.e. every language a capability-scan CALLER (self-conformance's
#: `_selfconform.py::_sorted_capability_files`, `vet`'s dependency scan)
#: actually reaches via `language_for`/`scan_file_capabilities`. Exists so
#: a drift-lock test can assert this set equals
#: `_capability_registry.LANGUAGES` (the registry's claimed-supported set)
#: without either side hand-duplicating the other's language list -- a new
#: registry language with no `_EXT_LANGUAGE` extension entry (or vice
#: versa) fails that test loudly instead of silently going unscanned
#: (T-0169: this exact class of gap is what let TS/JS self-conformance
#: scanning go dark in the logand.app pilot).
#:
#: T-2358: moved here (from `_capability.py`) alongside `language_for` --
#: `_capability_core.py` already defines `_EXT_LANGUAGE` both symbols are
#: derived from, so this was the natural home once `_capability_scan.py`
#: needed `language_for` back (see `language_for`'s own T-2358 note).
SCANNED_LANGUAGES: frozenset[str] = frozenset(_EXT_LANGUAGE.values())


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-2358
# frob:tests tests/test_vet.py::TestCapabilityScan.test_language_for_known_and_unknown_extensions kind="unit"  # noqa: E501
def language_for(path: Path) -> str | None:
    """The pattern-table bucket for `path`'s extension (T-0158: C/C++ is now
    a first-class `"c-cpp"` bucket, not `None`), or `None` for an extension
    with no registry-backed language at all.

    T-2358: moved here from `_capability.py` -- `_capability_scan.py`
    needed this back via a function-local deferred import (5 call sites,
    all commented "T-1420: avoid a circular import"), which created a
    genuine `_capability.py <-> _capability_scan.py` import cycle the
    deferred imports only hid from a naive top-level-only scanner, not
    from this repo's own function-body-aware `frob cycle` detector.
    `_capability_core.py` already owns `_EXT_LANGUAGE` and is imported by
    BOTH modules with no reverse edge, so this is the shared-helper split
    the cycle gate's own guidance recommends, not a second attempt to
    hide the same coupling. `_capability.py` re-imports and re-exports
    this name unchanged for every external caller."""
    return _EXT_LANGUAGE.get(path.suffix.lower())
