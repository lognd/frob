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

# frob:waive INV006 preset="split-carried-prose"
# frob:ticket T-1420
from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

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


def _comment_byte_spans(path: Path) -> tuple[ByteSpan, ...]:
    """Byte-range spans of every tree-sitter COMMENT node in `path` (T-0209).

    Backs the comment-exclusion filter every needle match below is checked
    against: a needle occurrence fully inside one of these spans is prose
    describing an operation, not the operation itself. Returns an empty
    tuple (never filters anything -- degrades to the pre-T-0209 unfiltered
    scan for that file) when `frob.lang` has no grammar for `path`'s
    extension at all, or when the file fails to parse; comment-span
    filtering is a precision layer on top of the substring scan, never a
    prerequisite for it."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    comment_types = COMMENT_TYPES.get(language_label)
    if not comment_types:
        return ()

    spans: list[ByteSpan] = []

    def walk(node) -> None:  # noqa: ANN001 -- tree_sitter.Node, avoided at type level here
        if node.type in comment_types:
            spans.append((node.start_byte, node.end_byte))
            return
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return tuple(spans)


def _fully_in_any_span(start: int, end: int, spans: tuple[ByteSpan, ...]) -> bool:
    """True if the byte range `[start, end)` is fully covered by one span in
    `spans` (T-0209: the comment-containment test every needle hit passes
    through before it counts as an observation)."""
    return any(
        span_start <= start and end <= span_end for span_start, span_end in spans
    )


#: python container node types whose body can open with a docstring
#: (T-0769) -- mirrors `frob.lang._walk_python`'s identical vocabulary
#: (module root, function/method, class), kept as a small local duplicate
#: rather than importing that module's private helper: this module already
#: uses `frob.lang`'s PUBLIC `raw_tree`/`node_text` entry points only, and
#: the "what counts as a docstring" rule is three lines of tree shape, not
#: worth a cross-module private dependency for.
_PY_DOCSTRING_CONTAINER_TYPES = ("function_definition", "class_definition")


def _py_leading_docstring_node(container):  # noqa: ANN001, ANN201 -- tree_sitter.Node
    """The leading-statement `string` node opening `container`'s body, if
    any (T-0769) -- `container` is either the module root itself or a
    function/class node whose own `body` field holds the statement block.
    Returns `None` when the first statement is not a bare/expression-
    wrapped string literal, i.e. there is no docstring here at all."""
    body = (
        container
        if container.type == "module"
        else container.child_by_field_name("body")
    )
    if body is None or body.named_child_count == 0:
        return None
    first = body.named_children[0]
    if first.type == "expression_statement":
        if first.named_child_count == 0 or first.named_children[0].type != "string":
            return None
        return first.named_children[0]
    if first.type == "string":
        return first
    return None


def _docstring_byte_spans(path: Path) -> tuple[ByteSpan, ...]:
    """Byte-range spans of every module/class/function-head docstring
    STRING node in `path` (T-0769) -- python only, the only language this
    module extracts a docstring concept for. A docstring is a non-
    executable string constant; needle prose written there (fork/subprocess
    hazard documentation, e.g.) must not count as an observed capability
    any more than the same prose in a `#` comment would (see module
    docstring T-0769 entry for the false-positive this closes). Returns an
    empty tuple for a non-python file, an unparseable file, or one
    `frob.lang` has no grammar for -- same degrade-gracefully posture as
    `_comment_byte_spans`."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "python":
        return ()

    spans: list[ByteSpan] = []

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if is_top or node.type in _PY_DOCSTRING_CONTAINER_TYPES:
            doc = _py_leading_docstring_node(node)
            if doc is not None:
                spans.append((doc.start_byte, doc.end_byte))
        for child in node.children:
            walk(child, False)

    walk(tree.root_node, True)
    return tuple(spans)


def _non_executable_byte_spans(path: Path) -> tuple[ByteSpan, ...]:
    """Every byte span in `path` that is prose, not executable code (T-0769):
    tree-sitter comment spans (T-0209) unioned with python docstring spans
    (T-0769 above). Every raw-text needle-scan call site in this module
    that used to exclude comment spans alone now excludes this union
    instead -- a needle hit fully inside either kind of span is
    documentation describing an operation, never the operation itself."""
    return _comment_byte_spans(path) + _docstring_byte_spans(path)


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


# language -> capability -> extra callable(text, comment_spans) -> bool,
# applied ON TOP of the plain substring needles above for needles that need
# one bit more context than "does this substring appear anywhere" (T-0151:
# `compile(` as a bare builtin call vs. `re.compile(`/`x.compile(` method
# access; T-0209: `comment_spans` lets the check apply the same
# comment-exclusion the plain needles get).
_SpecialCheck = Callable[[bytes, tuple[ByteSpan, ...]], bool]
_SPECIAL_CHECKS: dict[str, dict[str, tuple[_SpecialCheck, ...]]] = {
    "python": {"eval": (_has_bare_compile_call,)},
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
    """Whether one `DANGEROUS_OPERATIONS` entry's needle(s) (or bare-compile
    special check) hit in `raw` outside `comment_spans`. T-0882: a needle in
    `_BARE_CALL_NEEDLES` (`eval(`/`exec(`) requires a bare-builtin-call
    boundary here too, the same rule `_matched_capabilities` applies -- an
    entry citing `eval(`/`exec(` must not fire on an identifier that merely
    ends with that text (`_mutation_for_eval(`)."""
    if entry.needles:
        return any(
            (
                _needle_hits_as_bare_call(raw, needle.encode("utf-8"), comment_spans)
                if needle.encode("utf-8") in _BARE_CALL_NEEDLES
                else _needle_hits_outside_comments(
                    raw, needle.encode("utf-8"), comment_spans
                )
            )
            for needle in entry.needles
        )
    if entry.language == "python" and entry.function_or_pattern.startswith("compile("):
        return _has_bare_compile_call(raw, comment_spans)
    return False
