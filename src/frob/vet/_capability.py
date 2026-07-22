"""Tree-sitter-backed capability scan over a dependency's local source
(docs/modules/vet.md "Capability taxonomy" + "Mechanics").

Detection is a per-language token/substring scan over `frob.lang`-parsed
source (Python/JS-TS/Rust/C-C++ -- T-0158 adds C/C++ as a first-class
scanned language, retiring the old blanket "honestly-empty" exemption; see
`frob.vet._capability_registry` for the per-(kind, language) matrix that
now makes this claim checkable). T-0170 adds a `kotlin` bucket (`.kt`/
`.kts`, net/exec/client_storage), registry-compiled like every other
language -- see `_capability_registry.DANGEROUS_OPERATIONS`/`LANGUAGES`
for the kotlin rows and `CAPABILITY_MATRIX_EXCUSES` for its honestly-
unpatterned cells (eval, fs/fs-write/fs-read, env, ffi, install-hook,
html_render, sql, fetch_url, deserialize). A missing/unreadable file never
crashes
the scan; it degrades to an empty capability set plus a
`source-unavailable`-shaped note (docs/modules/vet.md "Honest limits").

T-0158: `_PATTERNS` below is no longer hand-maintained needle tuples --
it is COMPILED from `frob.vet._capability_registry.DANGEROUS_OPERATIONS`,
the single-source structured dangerous-operations registry (one entry per
{language, library, function_or_pattern, capability_kind, cwe_links,
rationale, safer_alternative, severity}). `scan_file_capabilities` keeps
returning a bare `frozenset[str]` of capability kinds (its existing
public contract); `_scan_file_operations` is the new richer entry point
that names WHICH registry entries fired, so an audit finding can cite
the library/function/rationale/safer_alternative instead of a bare kind
label.

T-0151: a bare `"compile("` substring needle used to sit in the Python
`eval` pattern table. It was meant to catch the `compile()` builtin used
to turn a code string into a code object for later `eval`/`exec` -- a
genuine eval-adjacent primitive. Because the match was plain substring
search, it fired on every `re.compile(`/`ast.compile(`-style dotted call
too (confirmed: every non-self hit across cli/graphlang/gates/core was
`re.compile(`, zero bare builtin `compile(` calls anywhere in this repo).
The needle is now a dot-exclusion check (`_has_bare_compile_call`): it
only counts as "eval" when `compile(` is NOT preceded by `.` or an
identifier character, i.e. it is the bare builtin, not a method access.
This keeps the "recall over precision" token-scan philosophy (still no
AST/call-graph analysis) while removing the one needle that was wrong by
construction rather than merely coarse.

Self-match note (T-0151, part b): `_PATTERNS` below stores needles as
Python string literals, so scanning this file's OWN text can still match
needles that appear only as table data (e.g. `"cmdclass"`, `"os.environ"`)
-- and the same class of false positive can hit ANY file that happens to
mention one of these substrings in a comment, docstring, or unrelated
string literal (confirmed hitting `_threat.py` prose before it was
reworded). Distinguishing "used as a call" from "appears as data" cheaply
would require tokenizing/parsing the file, which the module's docstring
above deliberately avoids -- see docs/modules/vet.md "Honest limits" for
this accepted false-positive class, now documented rather than silently
eaten. As a narrow, cheap mitigation for the worst instance of this class,
`_scan_directory_capabilities` excludes this module's own file from
directory-level aggregation (it is the one file guaranteed to contain
every needle as literal data); `scan_file_capabilities` called directly
on this file is unaffected and still shows the documented false positive.

T-0209: pilot P2 (aprog-public) hit a sharper instance of the same self-
match class -- a needle (`requests.get`) appearing only inside a `#`
COMMENT describing forbidden network calls, in a file whose actual code
never makes one. A substring scan cannot tell "this text is prose" from
"this text is code" on its own, so every needle hit is now checked
against `frob.lang`'s tree-sitter COMMENT node spans (`raw_tree` +
`COMMENT_TYPES`) for the same file; a hit fully contained inside a
comment span is dropped as documentation, not an observation. STRING
literals are deliberately NOT filtered the same way: a needle inside a
string can be a genuine exec vector in some languages/capabilities (an
`eval`-shaped payload assembled as a string literal, a JS
`Function("...")` body) and pure prose in others, and telling those apart
needs per-registry-entry judgment this cheap substring scanner does not
have. Leaving string hits unfiltered keeps the "recall over precision"
posture (a false positive costs an extra `[vet.allow]` line; a false
negative on a real string-embedded payload is a missed attack) and keeps
the locked self-scan false positive
(`test_capability_module_self_scan_documented_false_positive`, which
fires on `"cmdclass"`/`"os.environ"` appearing only in this module's own
DOCSTRING -- a string node, not a comment node) unchanged. Comment-span
filtering only applies to languages `frob.lang` can parse; an unparseable
file (or an extension `frob.lang` has no grammar for at all, e.g. the
`.js`/`.jsx`/`.mjs`/`.cjs` extensions this module's own `typescript`
bucket accepts) degrades to the pre-T-0209 unfiltered scan for that one
file rather than erroring.

T-0244: the embedded-code blind spot. A large HTML/JS-shaped STRING
LITERAL sitting inside a python module (a whole dashboard's markup/script
assembled as a python string, invisible to every needle table above since
each only scans a file's OWN source-grammar text) is detected via a size +
HTML/JS-signal heuristic over python `string` tree-sitter nodes
(`_embedded_code_regions`). Every region found ALWAYS contributes the
`embedded_code` capability kind -- fail-closed per docs/design/structural-
linter-adversarial-hardening.md rule 3: the region is declared even when
the best-effort typescript-needle re-scan of its own text
(`_embedded_capabilities`/`_embedded_operations`) turns up nothing
specific. Python host files only for this pass; the ticket's own reported
shape.
"""

# frob:ticket T-0151
# frob:ticket T-0158
# frob:ticket T-0244
from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from frob.excludes import iter_files
from frob.lang import COMMENT_TYPES, node_text, parse_file, raw_tree
from frob.logging import get_logger

from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation

if TYPE_CHECKING:
    from frob.strata import CveFingerprint

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
        # frob:waive PERF004 reason="runs once, only for this log line"
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

# T-0328: import/binding-aware resolution for Python, the priority language
# (highest coverage). The plain substring scan above is EVADED by ordinary
# aliasing/from-import Python -- `import subprocess as sp; sp.run(x)` never
# contains the literal text "subprocess.run(" the needle table looks for,
# and `from os import system as e; e(x)` contains neither "os.system(" nor
# "eval(", so the scanner observes NOTHING even though the code genuinely
# execs. This block builds a per-file IMPORT/BINDING TABLE from the same
# tree-sitter parse `_comment_byte_spans` already uses, resolves each
# call/attribute site's leftmost name through it (reconstructing the
# fully-qualified target, e.g. `sp.run` -> `subprocess.run`), and re-checks
# the SAME needle tables against the RESOLVED identity string instead of
# raw source text -- no new registry field, no new needle vocabulary, just
# a second pass over a synthesized "what this call/attribute actually
# refers to" string. Every resolved match is still confirmed against
# `comment_spans` before counting (T-0209 posture unchanged).
#
# Scope-awareness (mandatory to avoid FALSE POSITIVES): a LOCAL binding --
# a function/method parameter, an assignment target, a `for`/`with ... as`
# target, or a nested `def`/`class` name -- SHADOWS an import of the same
# name in every enclosing scope from the site up to module level. `def
# g(system): system(x)` (param) and `class Job: def run(self): ...` then
# `Job().run()` (method access on an unrelated object) must NOT resolve to
# `os.system`/a dangerous `run`, because the leftmost name in each case
# either resolves to a local binding (shadowed) or to an expression this
# resolver deliberately does not chase further (a `call` node, e.g.
# `Job()`, is not a resolvable "object" for attribute-chain purposes, so
# `Job().run` never reaches the import table at all).
#
# Known limitations, documented rather than silently eaten (mirrors this
# module's existing "Honest limits" posture): `from X import *` adds no
# binding (a star-imported name is untraceable without also modeling X's
# own exports); a function-scoped `import` is folded into the SAME
# file-wide binding table as a module-level one (a narrow, safe-direction
# over-approximation -- it can only ADD a resolution, never suppress a
# real one); a relative import's dotted text (`from . import x`) is kept
# as literal text (`"..x"`-shaped), which will not coincidentally collide
# with any real registry needle in practice. TS/C-C++ are OUT of scope for
# this pass -- C/C++'s `#include` is coarse-only by design (module
# docstring), and TS's binding table is noted as follow-up work, not
# attempted here. Rust gets its own binding-aware pass, T-0378 below.
_PY_SCOPE_TYPES = ("function_definition", "class_definition", "module")


#: sentinel `bound` position meaning "shadows from the very start of the
#: scope, regardless of call-site position" -- used for function/lambda
#: PARAMETERS (always in scope for the whole body) and nested `def`/`class`
#: names (mirrors Rust's `_RUST_ALWAYS_SHADOWS`, T-0378 round 2). Only
#: assignment-style targets get a REAL position (T-0468, see
#: `_collect_target_names`).
_PY_ALWAYS_SHADOWS = -1


def _record_py_binding(bound: dict[str, int], name: str, position: int) -> None:
    """Record that `name` starts shadowing an enclosing import binding at
    byte `position` within its scope, keeping the EARLIEST position on
    repeat bindings of the same name (a name rebound twice still shadows
    from its first occurrence onward, never un-shadows) -- the position-
    aware T-0468 fix's core bookkeeping primitive, mirrors Rust's
    `_record_rust_binding`."""
    existing = bound.get(name)
    bound[name] = position if existing is None else min(existing, position)


def _collect_target_names(node, position: int, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add every name an assignment-style TARGET pattern binds to `bound` AT
    `position` (T-0468: the enclosing assignment/`as`-pattern/walrus node's
    own `start_byte`, so a call site textually BEFORE this binding is not
    wrongly treated as already shadowed -- Python assignment does not
    hoist), recursing through tuple/list patterns and `as`-pattern wrappers
    but never through `attribute`/`subscript` targets (`obj.attr = x` /
    `obj[i] = x` mutate an existing object; they bind no new name)."""
    node_type = node.type
    if node_type == "identifier":
        _record_py_binding(bound, node_text(node), position)
        return
    if node_type in ("attribute", "subscript"):
        return
    for child in node.children:
        _collect_target_names(child, position, bound)


def _collect_param_name(node, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add one `parameters`-node child's bound name to `bound` at
    `_PY_ALWAYS_SHADOWS` (a plain `identifier`, or the name identifier
    inside `typed_parameter`/`default_parameter`/`typed_default_parameter`/
    `*args`/`**kwargs` patterns); punctuation/type-annotation/default-value
    children are skipped by construction (only the node's OWN direct
    `identifier` child is taken, never one nested inside a `type`
    subtree). A parameter is in scope for the WHOLE function body, so it
    shadows regardless of call-site position -- mirrors Rust's
    `_collect_rust_param_name`."""
    node_type = node.type
    if node_type == "identifier":
        _record_py_binding(bound, node_text(node), _PY_ALWAYS_SHADOWS)
        return
    if node_type in (
        "typed_parameter",
        "default_parameter",
        "typed_default_parameter",
        "list_splat_pattern",
        "dictionary_splat_pattern",
    ):
        for child in node.children:
            if child.type == "identifier":
                _record_py_binding(bound, node_text(child), _PY_ALWAYS_SHADOWS)
                return


def _scope_bind_step(node, is_top: bool, bound: dict[str, int]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_py_scope_bound_names`'s walk: add whatever
    name(s) `node` binds directly to `bound` (with `_PY_ALWAYS_SHADOWS` for
    params/nested-def-class names, or the binding node's own `start_byte`
    for an assignment/`as`-pattern/walrus target, T-0468), and report
    whether the walk should recurse into `node`'s children (False at a
    nested scope boundary -- only its OWN name binds in the parent scope,
    never its body; True otherwise)."""
    node_type = node.type
    if not is_top and node_type in ("function_definition", "class_definition"):
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            _record_py_binding(bound, node_text(name_node), _PY_ALWAYS_SHADOWS)
        return False
    if not is_top and node_type == "lambda":
        return False
    if node_type in ("parameters", "lambda_parameters"):
        for child in node.children:
            _collect_param_name(child, bound)
        return False
    if node_type in ("assignment", "augmented_assignment", "for_statement"):
        left = node.child_by_field_name("left")
        if left is not None:
            _collect_target_names(left, node.start_byte, bound)
    elif node_type == "as_pattern_target":
        _collect_target_names(node, node.start_byte, bound)
    elif node_type == "named_expression":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            _record_py_binding(bound, node_text(name_node), node.start_byte)
    return True


def _py_scope_bound_names(scope_node) -> dict[str, int]:  # noqa: ANN001
    """Every name bound DIRECTLY within `scope_node` (a `function_
    definition`/`class_definition`/`module` node), mapped to the byte
    position from which it starts shadowing an enclosing import binding --
    parameters and nested `def`/`class` names at `_PY_ALWAYS_SHADOWS`,
    assignment/`for`/`with ... as`/walrus targets at their own binding
    node's `start_byte` -- WITHOUT recursing into a nested scope's own
    body. This is the per-scope shadow table every call/attribute site is
    checked against before ever consulting the import binding table
    (T-0328: mandatory scope-awareness so a local `run`/`system`/etc.
    never resolves to an imported dangerous symbol of the same name).
    T-0468: POSITION-aware (mirrors Rust's `_rust_scope_bound_names`,
    T-0378 round 2) so a call site textually BEFORE a same-named rebind is
    correctly NOT treated as shadowed -- Python assignment does not hoist;
    a use before the rebind refers to whatever the name resolved to
    beforehand (here, the import-bound alias), same as the real Python
    name-resolution rule this scanner approximates."""
    bound: dict[str, int] = {}

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _scope_bind_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _bind_import_statement(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_statement` node's contribution to `_py_import_table`
    (T-0328): `import X` -> `{X: X}` (bare `import a.b` binds only the top
    package name `a`, matching real Python semantics), `import X as Y` ->
    `{Y: X}`."""
    for name_node in node.children_by_field_name("name"):
        if name_node.type == "dotted_name":
            full = node_text(name_node)
            first = full.split(".", 1)[0]
            table.setdefault(first, first)
        elif name_node.type == "aliased_import":
            dotted = name_node.child_by_field_name("name")
            alias = name_node.child_by_field_name("alias")
            if dotted is not None and alias is not None:
                table[node_text(alias)] = node_text(dotted)


def _bind_import_from_statement(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_from_statement` node's contribution to `_py_import_table`
    (T-0328): `from X import Z` -> `{Z: X.Z}`, `from X import Z as W` ->
    `{W: X.Z}`. `from X import *` adds NO binding (documented limitation,
    module docstring above)."""
    module_field = node.child_by_field_name("module_name")
    module_text = node_text(module_field) if module_field is not None else ""
    for name_node in node.children_by_field_name("name"):
        if name_node.type == "dotted_name":
            imported = node_text(name_node)
            table[imported] = f"{module_text}.{imported}" if module_text else imported
        elif name_node.type == "aliased_import":
            dotted = name_node.child_by_field_name("name")
            alias = name_node.child_by_field_name("alias")
            if dotted is not None and alias is not None:
                imported = node_text(dotted)
                target = f"{module_text}.{imported}" if module_text else imported
                table[node_text(alias)] = target
        # wildcard_import ("from X import *"): no binding added -- a
        # star-imported name is untraceable without also modeling X's own
        # export surface (documented limitation).


def _py_import_table(module_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide local-name -> resolved-dotted-target binding table
    (T-0328), built from `_bind_import_statement`/`_bind_import_from_
    statement`. Walks the WHOLE tree (not just top-level statements) so a
    function-scoped import still contributes a binding -- a safe-direction
    over-approximation, see module docstring."""
    table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "import_statement":
            _bind_import_statement(node, table)
        elif node.type == "import_from_statement":
            _bind_import_from_statement(node, table)
        for child in node.children:
            visit(child)

    visit(module_node)
    return table


def _shadowing_scope(name: str, site, scope_cache: dict[int, dict[str, int]]):  # noqa: ANN001, ANN201
    """The nearest LOCAL scope node enclosing `site` (site's own function ->
    class -> ... -> module, per `_py_scope_bound_names`, cached per scope
    node in `scope_cache`) that binds `name` directly AT OR BEFORE `site`'s
    own `start_byte`, or `None` if no enclosing scope binds it before this
    position -- the T-0328 shadow check every resolution goes through
    before consulting the import table. T-0337: returns the SCOPE NODE
    itself (rather than a bare bool) so a caller can look up whether that
    exact binding is a known dangerous local alias.

    T-0468 (soundness fix, mirrors T-0378 round 2's Rust fix): this used to
    be ORDER-INSENSITIVE -- it treated a name as shadowed anywhere in the
    enclosing scope, so a capability call occurring textually BEFORE a
    same-name rebind (`import os as o; o.system('ls'); o = None`) was
    silently missed (a real dangerous call un-flagged). Now POSITION-aware:
    a rebind recorded at a LATER byte position than `site` does NOT shadow
    this particular call site (it hasn't taken effect yet), so resolution
    correctly falls through to the import table instead of silently
    dropping a capability call that textually precedes its same-named
    local rebind. Parameters and nested `def`/`class` names still shadow
    unconditionally (`_PY_ALWAYS_SHADOWS`), since they are in scope for the
    whole enclosing body regardless of call-site position."""
    cur = site.parent
    while cur is not None:
        if cur.type in _PY_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = _py_scope_bound_names(cur)
                scope_cache[key] = cached
            position = cached.get(name)
            if position is not None and site.start_byte >= position:
                return cur
            if cur.type == "module":
                break
        cur = cur.parent
    return None


def _is_shadowed(name: str, site, scope_cache: dict[int, dict[str, int]]) -> bool:  # noqa: ANN001
    """True if `name` is bound by a local scope enclosing `site` AT OR
    BEFORE `site`'s position (T-0468 position-aware shadow check) -- thin
    bool wrapper over `_shadowing_scope` kept for call sites that only need
    the yes/no answer."""
    return _shadowing_scope(name, site, scope_cache) is not None


def _resolve_py_expr(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """Resolve one expression node (a bare `identifier` or an `attribute`
    chain) to its fully-qualified import-bound target, or `None` if it is
    locally shadowed (by a binding with no known dangerous resolution) or
    not a resolvable chain at all (T-0328). Any other expression (a `call`,
    subscript, literal, ...) is not a resolvable "object" for attribute-
    chain purposes -- e.g. `Job()` in `Job().run()` deliberately stops
    resolution here, so `.run` never reaches the import table (the T-0328
    no-false-positive case).

    T-0337: when `node` is an identifier LOCALLY shadowed by an enclosing
    scope, this no longer gives up unconditionally -- it consults
    `alias_table` (built by `_build_py_alias_table`, keyed by `scope.id`)
    for a resolved dangerous target THAT SPECIFIC BINDING scope recorded
    for the name. A parameter or a name bound only to a benign value has no
    alias_table entry, so resolution still correctly returns `None` there
    (the T-0328 no-false-positive/shadow guarantee is unchanged); a name
    locally rebound to an import-table entry, a dangerous attribute chain,
    or another already-aliased dangerous name DOES have an entry and
    resolves through it -- this is the local-rebinding copy-propagation
    fix."""
    if node.type == "identifier":
        return _resolve_py_identifier(node, import_table, scope_cache, alias_table)
    if node.type == "attribute":
        # frob:invariant terminates reason="mutually recurses with _resolve_py_attribute, which only calls back here with node.child_by_field_name('object'), a proper descendant of node in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
        return _resolve_py_attribute(node, import_table, scope_cache, alias_table)
    return None


# frob:ticket T-0361
def _resolve_py_identifier(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None,
) -> str | None:  # noqa: ANN001
    """Resolve a bare `identifier` node to its import-bound target, consulting
    `alias_table` for locally-shadowed names (T-0337); split out of
    `_resolve_py_expr`'s identifier branch (T-0361)."""
    name = node_text(node)
    scope = _shadowing_scope(name, node, scope_cache)
    if scope is not None:
        if alias_table is None:
            return None
        return alias_table.get(scope.id, {}).get(name)
    return import_table.get(name)


# frob:ticket T-0361
def _resolve_py_attribute(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None,
) -> str | None:  # noqa: ANN001
    """Resolve an `attribute` chain node by recursively resolving its
    `object` child through `_resolve_py_expr` and appending the attribute
    name; split out of `_resolve_py_expr`'s attribute branch (T-0361)."""
    obj = node.child_by_field_name("object")
    attr = node.child_by_field_name("attribute")
    if obj is None or attr is None:
        return None
    # frob:invariant terminates reason="obj is node's own 'object' field child, a proper descendant of node in the finite tree-sitter parse tree; mutually recurses with _resolve_py_expr, which only descends into the 'attribute' branch by calling back here" measure="node's subtree depth strictly decreases"  # noqa: E501
    resolved_obj = _resolve_py_expr(obj, import_table, scope_cache, alias_table)
    if resolved_obj is None:
        return None
    return f"{resolved_obj}.{node_text(attr)}"


def _enclosing_py_scope(node):  # noqa: ANN001, ANN201
    """The nearest `_PY_SCOPE_TYPES` ancestor of `node` (its own function ->
    class -> ... -> module), or `None` if `node` is itself the module root
    with no scope ancestor -- used by `_build_py_alias_table` to find which
    scope an assignment's target name binds into."""
    cur = node.parent
    while cur is not None:
        if cur.type in _PY_SCOPE_TYPES:
            return cur
        cur = cur.parent
    return None


def _build_py_alias_table(
    module_node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
) -> dict[int, dict[str, str]]:
    """Scope-local copy-propagation table (T-0337): `id(scope_node) ->
    {name: resolved_dangerous_target}` for every plain-identifier
    assignment target whose RHS resolves (via `_resolve_py_expr`, which
    itself consults this same table as it is built) to an import-table
    entry, a dangerous attribute chain, or another local name already known
    to alias one -- covering single rebinds (`xyz = run`), attribute
    rebinds (`e = os.system`), and transitive chains (`a = run; b = a`) in
    one pass, since the tree walk visits assignments in source (document)
    order so an earlier alias is already recorded by the time a later
    statement copies it. Cycle-safe by construction: only NEW bindings ever
    get looked up, and `_resolve_py_expr`'s shadow check means a name can
    only alias a resolution recorded in an enclosing/self scope that has
    already been walked, never itself circularly.

    Sound for may-analysis by design, not flow-sensitive: once a name is
    recorded as aliasing a dangerous target within a scope, a LATER benign
    reassignment of that same name in the same scope does not clear the
    entry -- `dict.setdefault` keeps the first (dangerous) resolution, so a
    call through the name anywhere in the scope is still flagged. This is
    the documented over-approximation choice (T-0337): a name that was EVER
    bound to a dangerous target in a scope may still be dangerous at any
    call site of that name in that scope."""
    alias_table: dict[int, dict[str, str]] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "assignment":
            _record_py_alias(node, import_table, scope_cache, alias_table)
        for child in node.children:
            visit(child)

    visit(module_node)
    return alias_table


# frob:ticket T-0361
def _record_py_alias(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
) -> None:  # noqa: ANN001
    """If `node` (an `assignment`) binds a plain identifier to a resolvable
    RHS, record it in `alias_table` (first resolution wins, per the
    over-approximation policy documented on `_build_py_alias_table`); split
    out of that function's tree-walk visitor (T-0361)."""
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    if left is None or right is None or left.type != "identifier":
        return
    resolved = _resolve_py_expr(right, import_table, scope_cache, alias_table)
    if resolved is None:
        return
    scope = _enclosing_py_scope(node)
    if scope is None:
        return
    scope_aliases = alias_table.setdefault(scope.id, {})
    scope_aliases.setdefault(node_text(left), resolved)


def _collect_py_candidates(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    candidates: list[tuple[str, int, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every call/attribute site that resolves through
    `import_table` (T-0328) or, when locally shadowed, through
    `alias_table`'s scope-local copy-propagation (T-0337)."""
    if node.type == "call":
        func = node.child_by_field_name("function")
        if func is not None and func.type in ("identifier", "attribute"):
            resolved = _resolve_py_expr(func, import_table, scope_cache, alias_table)
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    elif node.type == "attribute":
        resolved = _resolve_py_expr(node, import_table, scope_cache, alias_table)
        if resolved is not None:
            candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_py_candidates(
            child, import_table, scope_cache, candidates, alias_table
        )


def _python_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_dotted_target, start_byte, end_byte)` this file's
    call/attribute sites resolve to through its import binding table,
    enclosing-scope shadow check, and scope-local alias copy-propagation
    (T-0328, extended by T-0337 for local rebinding of a dangerous name).
    Empty for a non-Python file, an unparseable file, or one `frob.lang`
    has no grammar for -- degrades to the pre-existing lexical-only scan,
    never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "python":
        return ()

    import_table = _py_import_table(tree.root_node)
    scope_cache: dict[int, dict[str, int]] = {}
    alias_table = _build_py_alias_table(tree.root_node, import_table, scope_cache)
    candidates: list[tuple[str, int, int]] = []
    _collect_py_candidates(
        tree.root_node, import_table, scope_cache, candidates, alias_table
    )
    return tuple(candidates)


def _needle_matches_resolved(needle: str, resolved: str) -> bool:
    """True if `needle` (a registry needle string, e.g. `"subprocess."`,
    `"os.system("`, or a bare `"Popen("`) occurs in the RESOLVED dotted
    target `resolved` (e.g. `"subprocess.run"`), checking both the bare
    resolved string and a synthesized call form (`resolved + "("`) so a
    needle written with a trailing call-paren (`"os.system("`) still
    matches a resolved identity that has none of its own (T-0328: this is
    the resolved-identity sibling of the raw-text `_needle_hits_outside_
    comments` substring check above)."""
    return needle in resolved or needle in f"{resolved}("


def _python_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via import/binding-aware resolution only
    (T-0328) -- the union of every registry needle that matches a resolved
    call/attribute target, for sites outside a comment span. Merged into
    `scan_file_capabilities`'s lexical result; adds recall (aliased/from-
    import evasions) without touching the existing raw-text path at all."""
    found: set[str] = set()
    for resolved, start, end in _python_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


def _python_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` python entries observed via import/binding-
    aware resolution only (T-0328) -- `_scan_file_operations`'s resolver-
    backed sibling to `_python_binding_capabilities`. An entry with no
    `needles` (bare-builtin `compile()`) is never resolver-matched here;
    it stays exclusively on the existing `_has_bare_compile_call` special
    check, since there is no import alias for a builtin to resolve."""
    candidates = _python_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "python" or not entry.needles:
            continue
        for resolved, start, end in candidates:
            if _fully_in_any_span(start, end, comment_spans):
                continue
            if any(
                _needle_matches_resolved(needle, resolved) for needle in entry.needles
            ):
                matched.append(entry)
                break
    return tuple(matched)


# T-0377: import/binding-aware resolution for TypeScript/JS, mirroring the
# T-0328/T-0337 Python discipline above -- same shape (import/require/alias
# table + scope-shadowing over the same tree-sitter parse), different
# grammar. Before this, TS/JS capability scanning was pure lexical needle-
# matching over raw text, so any renamed/destructured/namespaced import to a
# dangerous module evaded it entirely: `import {run as r} from
# 'child_process'; r(cmd)` never contains the literal text "child_process"
# or "exec("/"run(" the needle table looks for at the call site; neither
# does `const {exec} = require('child_process'); exec(cmd)` or `import cp =
# require('child_process'); cp.exec(cmd)`.
#
# Import/require forms resolved into the binding table (`_ts_import_table`):
#   import {run as r} from 'child_process'   -> {"r": "child_process.run"}
#   import * as cp from 'child_process'      -> {"cp": "child_process"}
#   import dflt from 'child_process'         -> {"dflt": "child_process"}
#   import cp = require('child_process')     -> {"cp": "child_process"}
#   const {exec} = require('child_process')  -> {"exec": "child_process.exec"}
#   const cp = require('child_process')      -> {"cp": "child_process"}
#
# Scope-awareness (mandatory to avoid FALSE POSITIVES, mirrors T-0328): a
# function/method PARAMETER, or a local `const`/`let`/`var` binding, of the
# same name as an imported binding SHADOWS it in every enclosing scope from
# the site up to the module (`program`) root -- `function g(run){ run(x); }`
# must not resolve `run` to a dangerous import. A property access on an
# unrelated object (`class Job { run(){} }` then `new Job().run()`) never
# even reaches the import table: the object side of that member expression
# is a `new_expression`/`call_expression`, not a resolvable identifier/
# member chain, so resolution stops there by construction -- same posture
# as `Job().run()` in the Python resolver.
#
# T-0377 REVIEWER ROUND 2 (two live evasion classes the round-1 pass above
# missed -- both ORDINARY JS/TS idioms, not obfuscation, confirmed against
# axios/"net" to isolate the resolver from the pre-existing lexical layer):
#
#   1. COMPUTED/BRACKET MEMBER ACCESS: `require('axios')['get'](url)` and
#      `const ax = require('axios'); ax['get'](url)` evaded round 1 --
#      `_resolve_ts_expr`/`_collect_ts_candidates` only ever inspected
#      `identifier`/`member_expression` nodes, never `subscript_expression`.
#      Fixed: `_resolve_ts_subscript` resolves `obj['fn']` the same as
#      `obj.fn` whenever the subscript is STATICALLY resolvable -- a
#      string literal, or (round 3) a NO-INTERPOLATION TEMPLATE LITERAL
#      (`` ax[`get`](url) `` -- template literals are an everyday idiom
#      many lint configs PREFER over quotes, not an obfuscation trick, and
#      `` `get` `` carries identical static text to `'get'`). A genuinely
#      COMPUTED subscript -- a non-literal key OR an INTERPOLATED template
#      literal (`ax[dynamicKey](url)`, `` ax[`${dynamicKey}`](url) ``) --
#      still resolves to `None`: the property name is a runtime value this
#      static resolver cannot evaluate. This is an intentional, tested,
#      documented gap (`test_computed_subscript_not_detected`,
#      `test_interpolated_template_subscript_not_detected`), not a silent
#      one -- filed as follow-up T-draft-e7c8b53c (dynamic-key resolution
#      is a fundamentally different problem: it needs either taint-style
#      "any string-keyed access on a dangerous object is worth flagging"
#      heuristics, or giving up precision entirely for that one case).
#   2. DYNAMIC `import()`: `import('axios').then(ax => ax.get(url))` and
#      `const ax = await import('axios'); ax.get(url)` evaded round 1 --
#      `_ts_import_table`'s walk only ever dispatched on `import_statement`/
#      `variable_declarator`, never an `import(...)` CALL expression (the
#      dynamic form is syntactically a call, not a statement). Fixed:
#      `_bind_ts_dynamic_import_then` binds a `.then(cb)` callback's first
#      parameter to the imported module; `_ts_module_call_target` (shared
#      with the `require()` path via `_unwrap_ts_await`) resolves an
#      `await`-ed dynamic import assignment the same way `require()`
#      already was. Both are STANDARD ways to consume a dynamic import
#      (the standard way to conditionally load a module in TS/JS at all,
#      and a natural place to hide a dangerous one) -- both now resolve
#      identically to a namespace `import * as`.
#
# T-0432 (computed/non-literal bracket-subscript resolution, light
# dataflow): a COMPUTED subscript that is a bare identifier or a single-
# substitution template literal (`ax[key](url)`, `` ax[`${key}`](url) ``)
# now resolves when `key` is bound to exactly ONE string literal anywhere
# in the file (`_ts_local_string_bindings`/`_ts_bound_subscript_text`) --
# closes the trivial `const key = 'exec'; ax[key](url)` indirection the
# T-0377 audit flagged as accepted-but-checkable. Deliberately NOT real
# reaching-definitions dataflow: a name reassigned to two DIFFERENT
# literal values anywhere in the file (including a plain `key = 'x'`
# reassignment, not just a second declarator) is excluded from the table
# entirely (stays unresolved, never guesses which value is live at the
# subscript site); a name assigned a non-literal value (a function call, a
# concatenation, a member-access key) is excluded the same way; a template
# literal with MORE than one substitution or any surrounding literal text
# still resolves to `None`. Considered and REJECTED: a fail-open heuristic
# ("any bracket access on an object resolved to a known-dangerous import
# is worth flagging regardless of subscript shape") -- the false-positive
# cost against ordinary dynamic-dispatch idioms (a lookup table, a plugin
# registry) was judged too high without a concrete finding to weigh it
# against; the light single-literal-binding dataflow above is the
# genuinely-closed subset, everything else stays an honest, tested
# limitation (`test_non_literal_bound_subscript_not_detected`,
# `test_multi_substitution_template_subscript_not_detected`,
# `test_reassigned_const_string_subscript_not_detected`).
#
# Known limitations, documented rather than silently eaten (mirrors this
# module's "Honest limits" posture): no scope-local alias copy-propagation
# (the T-0337 Python enhancement) -- a name shadowed by a local binding is
# simply unresolved past that point here, never chased through a further
# local reassignment; `export {x as y}` / re-export forms add no binding
# (not import sites); a function-scoped `const`/`require` is folded into the
# same file-wide binding table as a module-level one when it is a plain
# `require()` destructure (a narrow, safe-direction over-approximation, same
# as Python's function-scoped `import`); a COMPUTED bracket subscript --
# a NON-LITERAL key OR an INTERPOLATED template literal (a static, no-
# interpolation template literal DOES resolve, round 3 above) -- resolves
# only through the T-0432 single-literal-binding case above, else stays
# unresolved (T-draft-e7c8b53c tracks the fully-general case, see above); a
# `.then(cb)` callback's module binding is added to the FILE-WIDE table
# rather than scoped to the callback body (the same over-approximation as
# every other binding here -- can only ADD a resolution, never suppress a
# real one).
# C-C++/Kotlin remain OUT of scope for this pass; Rust gets its own binding-
# aware pass, T-0378 below.
_TS_SCOPE_TYPES = (
    "function_declaration",
    "generator_function_declaration",
    "function_expression",
    "generator_function",
    "arrow_function",
    "method_definition",
    "class_declaration",
    "class_expression",
    "program",
)


def _collect_ts_target_names(node, bound: set[str]) -> None:  # noqa: ANN001
    """Add every name a TS/JS destructuring TARGET pattern binds to `bound`
    (T-0377) -- mirrors `_collect_target_names`'s python job. Recurses
    through `object_pattern`/`array_pattern`/`pair_pattern` (its `value`
    field only, never its `key`) but never through `member_expression`/
    `subscript_expression` targets (`obj.attr = x` mutates an existing
    object; it binds no new name)."""
    node_type = node.type
    if node_type in ("identifier", "shorthand_property_identifier_pattern"):
        bound.add(node_text(node))
        return
    if node_type == "pair_pattern":
        value = node.child_by_field_name("value")
        if value is not None:
            _collect_ts_target_names(value, bound)
        return
    if node_type in ("member_expression", "subscript_expression"):
        return
    for child in node.children:
        _collect_ts_target_names(child, bound)


def _collect_ts_param_name(node, bound: set[str]) -> None:  # noqa: ANN001
    """Add one `formal_parameters`-node child's bound name(s) to `bound`
    (T-0377): a plain `identifier`, or the `pattern` field of a `required_
    parameter`/`optional_parameter` (its sibling `value` field, the default
    expression, is deliberately never walked -- `{b,c:d}=obj` must bind
    `b`/`d`, never the unrelated identifier `obj`)."""
    node_type = node.type
    if node_type == "identifier":
        bound.add(node_text(node))
        return
    if node_type in ("required_parameter", "optional_parameter"):
        pattern = node.child_by_field_name("pattern")
        if pattern is not None:
            _collect_ts_target_names(pattern, bound)


# node types that open a nested TS/JS scope boundary and bind their OWN
# name (if any) into the PARENT scope, never their body -- the "return
# False" cases `_scope_bind_ts_step` dispatches to `_bind_ts_scope_boundary`
# (T-0377).
_TS_NAMED_SCOPE_BOUNDARIES = (
    "function_declaration",
    "generator_function_declaration",
    "function_expression",
    "generator_function",
    "method_definition",
    "class_declaration",
    "class_expression",
)


def _bind_ts_variable_declarator(node, bound: set[str]) -> None:  # noqa: ANN001
    """`variable_declarator` case of `_scope_bind_ts_step` (T-0377): binds
    its target pattern's names UNLESS the declarator is itself an IMPORT
    SITE -- a `require(...)` call (`_bind_ts_require_declarator` records
    that case in the import table instead) OR a dynamic `import(...)` call,
    optionally `await`-ed (`_bind_ts_dynamic_import_declarator`, T-0377
    reviewer round 2) -- a `const x = require('mod')`/`const x = await
    import('mod')` declarator must NOT also be added to this scope's
    bound-names set, or the shadow check would see the import's own target
    name as "locally bound" and treat every such binding as self-shadowing
    its own import (a genuine bug hit while writing this resolver, caught
    by `test_require_bare_detected`/`test_require_destructure_rename_
    detected`; the dynamic-import case is the identical bug in a second
    syntactic guise, caught by `test_await_dynamic_import_detected`)."""
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if name_node is not None and (
        value_node is None or _ts_module_call_target(value_node) is None
    ):
        _collect_ts_target_names(name_node, bound)


def _scope_bind_ts_step(node, is_top: bool, bound: set[str]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_ts_scope_bound_names`'s walk (T-0377): add
    whatever name(s) `node` binds directly to `bound`, and report whether
    the walk should recurse into `node`'s children (False at a nested scope
    boundary -- only its own name binds in the parent scope, never its
    body; True otherwise). Mirrors `_scope_bind_step`'s python job."""
    node_type = node.type
    if not is_top and node_type in _TS_NAMED_SCOPE_BOUNDARIES:
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            bound.add(node_text(name_node))
        return False
    if not is_top and node_type == "arrow_function":
        return False
    if node_type == "formal_parameters":
        for child in node.children:
            _collect_ts_param_name(child, bound)
        return False
    if node_type == "variable_declarator":
        _bind_ts_variable_declarator(node, bound)
    elif node_type == "catch_clause":
        param = node.child_by_field_name("parameter")
        if param is not None:
            _collect_ts_target_names(param, bound)
    elif node_type in ("for_in_statement", "for_statement"):
        for child in node.children:
            if child.type == "identifier":
                bound.add(node_text(child))
    return True


def _ts_scope_bound_names(scope_node) -> set[str]:  # noqa: ANN001
    """Every name bound DIRECTLY within `scope_node` (T-0377) -- parameters,
    `const`/`let`/`var` destructuring targets, `catch`/`for` bindings, and
    nested function/class names -- WITHOUT recursing into a nested scope's
    own body. Mirrors `_py_scope_bound_names`'s python job; the per-scope
    shadow table every call/member-access site is checked against before
    ever consulting the import binding table."""
    bound: set[str] = set()

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _scope_bind_ts_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _shadowing_ts_scope(name: str, site, scope_cache: dict[int, frozenset[str]]):  # noqa: ANN001, ANN201
    """The nearest LOCAL scope node enclosing `site` (site's own function ->
    class -> ... -> program, per `_ts_scope_bound_names`, cached per scope
    node in `scope_cache`) that binds `name` directly, or `None` if no
    enclosing scope binds it at all (T-0377) -- mirrors `_shadowing_scope`'s
    python job."""
    cur = site.parent
    while cur is not None:
        if cur.type in _TS_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = frozenset(_ts_scope_bound_names(cur))
                scope_cache[key] = cached
            if name in cached:
                return cur
            if cur.type == "program":
                break
        cur = cur.parent
    return None


def _is_ts_shadowed(name: str, site, scope_cache: dict[int, frozenset[str]]) -> bool:  # noqa: ANN001
    """True if `name` is bound by a local scope enclosing `site` (T-0377
    shadow check) -- thin bool wrapper over `_shadowing_ts_scope`."""
    return _shadowing_ts_scope(name, site, scope_cache) is not None


def _ts_string_text(string_node) -> str:  # noqa: ANN001
    """The literal text of a TS/JS `string` node, joined across its
    `string_fragment` children (T-0377) -- excludes the quote tokens
    tree-sitter keeps as siblings; mirrors `_string_content_bytes`'s python
    counterpart, text rather than bytes since import module specifiers are
    always used as plain strings here."""
    return "".join(
        node_text(child)
        for child in string_node.children
        if child.type == "string_fragment"
    )


def _ts_require_call_module(node) -> str | None:  # noqa: ANN001
    """If `node` is a `call_expression` calling the bare `require` builtin
    with a single string-literal argument, its module specifier text;
    `None` for any other shape (a non-`require` call, a computed/dynamic
    argument, ...) -- (T-0377) the CommonJS sibling of the ES `import`
    forms `_bind_ts_import_statement` handles."""
    if node.type != "call_expression":
        return None
    func = node.child_by_field_name("function")
    if func is None or func.type != "identifier" or node_text(func) != "require":
        return None
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return None
    string_node = next(
        (child for child in arguments.children if child.type == "string"), None
    )
    if string_node is None:
        return None
    return _ts_string_text(string_node)


def _ts_dynamic_import_module(node) -> str | None:  # noqa: ANN001
    """If `node` is a `call_expression` calling the dynamic `import(...)`
    keyword-form with a single string-literal argument, its module
    specifier text; `None` for any other shape -- (T-0377 reviewer round 2)
    the ES-module-standard sibling of `_ts_require_call_module`: `import(
    'axios')` is the STANDARD way to conditionally load a module at
    runtime, and its `function` field is a bare `import` node (not an
    `identifier`, unlike `require`), so it needs its own recognizer rather
    than reusing `_ts_require_call_module`'s identifier check."""
    if node.type != "call_expression":
        return None
    func = node.child_by_field_name("function")
    if func is None or func.type != "import":
        return None
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return None
    string_node = next(
        (child for child in arguments.children if child.type == "string"), None
    )
    if string_node is None:
        return None
    return _ts_string_text(string_node)


def _unwrap_ts_await(node):  # noqa: ANN001, ANN201
    """`node`'s inner expression if `node` is an `await_expression`
    (`await import('x')` -> the `import('x')` call node), else `node`
    itself unchanged -- (T-0377 reviewer round 2) `await_expression` has no
    named field for its operand in this grammar, so this walks past the
    literal `await` token child."""
    if node.type != "await_expression":
        return node
    for child in node.children:
        if child.type != "await":
            return child
    return node


def _ts_module_call_target(node) -> str | None:  # noqa: ANN001
    """`node` (after unwrapping a leading `await`) resolved as a bare
    `require('x')` or dynamic `import('x')` call to its module specifier
    text, or `None` if it is neither -- (T-0377 reviewer round 2) the
    shared "is this expression itself an import site" check used by both
    the scope-binder (so an import-site declarator does not self-shadow
    its own import, T-0377 round 1's `_bind_ts_variable_declarator` fix)
    and the declarator import-table binder below."""
    unwrapped = _unwrap_ts_await(node)
    return _ts_require_call_module(unwrapped) or _ts_dynamic_import_module(unwrapped)


def _bind_ts_import_clause(node, module: str, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_clause` node's contribution to `_ts_import_table`
    (T-0377): a bare `identifier` child is a DEFAULT import (`import dflt
    from 'x'` -> `{dflt: x}`, module root -- the default export itself is
    not further named); `namespace_import` (`import * as cp from 'x'`) ->
    `{cp: x}`; each `named_imports` -> `import_specifier` (`import {run as
    r} from 'x'` -> `{r: x.run}`, `import {exec} from 'x'` -> `{exec:
    x.exec}` when there is no `alias` field)."""
    for child in node.children:
        if child.type == "identifier":
            table.setdefault(node_text(child), module)
        elif child.type == "namespace_import":
            name_node = next(
                (c for c in child.children if c.type == "identifier"), None
            )
            if name_node is not None:
                table.setdefault(node_text(name_node), module)
        elif child.type == "named_imports":
            for spec in child.children:
                if spec.type != "import_specifier":
                    continue
                name_node = spec.child_by_field_name("name")
                alias_node = spec.child_by_field_name("alias")
                if name_node is None:
                    continue
                imported = node_text(name_node)
                local = node_text(alias_node) if alias_node is not None else imported
                table.setdefault(local, f"{module}.{imported}")


def _bind_ts_import_statement(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_statement` node's contribution to `_ts_import_table`
    (T-0377): dispatches to `_bind_ts_import_clause` for the ES `source`-
    bearing form (`import ... from 'x'`), or handles the TS-only
    `import_require_clause` form directly (`import cp = require('x')` ->
    `{cp: x}`) -- that form has no `source` field of its own; its module
    specifier lives inside the clause's own `require(...)` call."""
    source_node = node.child_by_field_name("source")
    module = _ts_string_text(source_node) if source_node is not None else None
    for child in node.children:
        if child.type == "import_require_clause":
            name_node = next(
                (c for c in child.children if c.type == "identifier"), None
            )
            string_node = next((c for c in child.children if c.type == "string"), None)
            if name_node is not None and string_node is not None:
                table.setdefault(node_text(name_node), _ts_string_text(string_node))
            return
        if child.type == "import_clause" and module is not None:
            _bind_ts_import_clause(child, module, table)


def _bind_ts_require_object_pattern(
    pattern_node, module: str, table: dict[str, str]
) -> None:  # noqa: ANN001
    """The `object_pattern` target branch of `_bind_ts_require_declarator`
    (T-0377): `const {exec} = require('x')` -> `{exec: x.exec}` for each
    `shorthand_property_identifier_pattern` property, `const {exec: e} =
    require('x')` -> `{e: x.exec}` for each renamed `pair_pattern`
    property."""
    for child in pattern_node.children:
        if child.type == "shorthand_property_identifier_pattern":
            imported = node_text(child)
            table.setdefault(imported, f"{module}.{imported}")
        elif child.type == "pair_pattern":
            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")
            if (
                key_node is not None
                and value_node is not None
                and value_node.type == "identifier"
            ):
                table.setdefault(
                    node_text(value_node), f"{module}.{node_text(key_node)}"
                )


def _bind_ts_require_declarator(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `variable_declarator` node's contribution to `_ts_import_table`
    (T-0377, extended by the reviewer-round-2 dynamic-import fix) when its
    `value` (after unwrapping a leading `await`, via `_ts_module_call_
    target`) is a `require(...)` call OR a dynamic `import(...)` call: a
    plain identifier target (`const cp = require('x')`, `const cp = await
    import('x')`) -> `{cp: x}`; an `object_pattern` target dispatches to
    `_bind_ts_require_object_pattern`. A `value` that is neither contributes
    nothing (a plain `const y = 5` is not an import site)."""
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if name_node is None or value_node is None:
        return
    module = _ts_module_call_target(value_node)
    if module is None:
        return
    if name_node.type == "identifier":
        table.setdefault(node_text(name_node), module)
    elif name_node.type == "object_pattern":
        _bind_ts_require_object_pattern(name_node, module, table)


def _ts_dynamic_import_then_param_name(callback) -> str | None:  # noqa: ANN001
    """The bound parameter name of an `arrow_function`/`function_expression`
    `.then(...)` callback (T-0377 reviewer round 2) -- handles both the
    unparenthesized single-arrow-param form (`ax => ...`, field
    `"parameter"`) and the parenthesized `formal_parameters` form (`(ax) =>
    ...`/`function(ax) {...}`, taking the first plain-identifier or
    `required_parameter`/`optional_parameter` pattern). `None` for a
    zero-arg callback or a destructuring param (the module then binds to
    no single name, a documented limitation -- same posture as an
    unresolvable destructure elsewhere in this resolver)."""
    single = callback.child_by_field_name("parameter")
    if single is not None and single.type == "identifier":
        return node_text(single)
    params = callback.child_by_field_name("parameters")
    if params is None:
        return None
    for child in params.children:
        if child.type == "identifier":
            return node_text(child)
        if child.type in ("required_parameter", "optional_parameter"):
            pattern = child.child_by_field_name("pattern")
            if pattern is not None and pattern.type == "identifier":
                return node_text(pattern)
    return None


def _ts_dynamic_import_then_module(node) -> str | None:  # noqa: ANN001
    """If `node` (a `call_expression`'s `function` field) is `import('mod')
    .then` -- a `member_expression` whose `property` is literally `then`
    and whose `object` is a dynamic `import(...)` call -- its module
    specifier text; `None` for any other shape. Split out of
    `_bind_ts_dynamic_import_then` to keep that function under the arch
    length ceiling (T-0377 reviewer round 2)."""
    if node is None or node.type != "member_expression":
        return None
    obj = node.child_by_field_name("object")
    prop = node.child_by_field_name("property")
    if obj is None or prop is None or node_text(prop) != "then":
        return None
    return _ts_dynamic_import_module(obj)


def _ts_dynamic_import_then_callback(node):  # noqa: ANN001, ANN201
    """The first `arrow_function`/`function_expression` argument of a
    `call_expression`'s `arguments` field, or `None` if there is none --
    the callback `.then(cb)` is invoked with (T-0377 reviewer round 2),
    split out of `_bind_ts_dynamic_import_then` to keep it under the arch
    length ceiling."""
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return None
    return next(
        (
            child
            for child in arguments.children
            if child.type in ("arrow_function", "function_expression")
        ),
        None,
    )


def _bind_ts_dynamic_import_then(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `call_expression` node's contribution to `_ts_import_table`
    (T-0377 reviewer round 2) when it is `import('mod').then(cb)`: binds
    `cb`'s first parameter name to `mod` in the table, the `.then(...)`
    sibling of `_bind_ts_require_declarator`'s `await import(...)`
    assignment form -- both are standard ways to consume a dynamic
    `import()`, and both must resolve the same as a namespace import."""
    module = _ts_dynamic_import_then_module(node.child_by_field_name("function"))
    if module is None:
        return
    callback = _ts_dynamic_import_then_callback(node)
    if callback is None:
        return
    param_name = _ts_dynamic_import_then_param_name(callback)
    if param_name is not None:
        table.setdefault(param_name, module)


def _ts_import_table(program_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide local-name -> resolved-dotted-target binding table
    (T-0377, extended by the reviewer-round-2 dynamic-import fix), built
    from `_bind_ts_import_statement` (ES `import`/TS `import X =
    require(...)`), `_bind_ts_require_declarator` (CommonJS `const {..} =
    require(...)`/`const x = await import(...)`), and `_bind_ts_dynamic_
    import_then` (`import(...).then(cb => ...)`). Walks the WHOLE tree (not
    just top-level statements), same function-scoped-import over-
    approximation as the python table."""
    table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "import_statement":
            _bind_ts_import_statement(node, table)
        elif node.type == "variable_declarator":
            _bind_ts_require_declarator(node, table)
        elif node.type == "call_expression":
            _bind_ts_dynamic_import_then(node, table)
        for child in node.children:
            visit(child)

    visit(program_node)
    return table


def _ts_static_template_text(node) -> str | None:  # noqa: ANN001
    """The static text of a `template_string` node with NO interpolation
    (`` `get` ``), or `None` if it contains at least one `template_
    substitution` child (`` `${dynamicKey}` ``/`` `pre${x}post` ``) -- a
    no-interpolation template literal carries IDENTICAL static text to an
    equivalent single/double-quoted string literal and is exactly as
    statically resolvable (T-0377 reviewer round 3: template literals are
    an everyday idiom many lint configs PREFER over quotes, not an
    obfuscation trick -- `ax[`get`](url)` must resolve the same as
    `ax['get'](url)`). An INTERPOLATED template literal stays under the
    genuinely-computed-subscript exclusion (`_resolve_ts_subscript`'s
    `None` branch, documented in the module's Known-limitations block)."""
    if node.type != "template_string":
        return None
    parts: list[str] = []
    for child in node.children:
        if child.type == "template_substitution":
            return None
        if child.type == "string_fragment":
            parts.append(node_text(child))
    return "".join(parts)


def _ts_static_subscript_text(index) -> str | None:  # noqa: ANN001
    """The static text of a subscript `index` node if it is a plain string
    literal OR a no-interpolation template literal (T-0377 reviewer round
    3), or `None` for any other shape (a genuinely computed key) --
    `_resolve_ts_subscript`'s single dispatch point for "is this subscript
    statically resolvable at all"."""
    if index.type == "string":
        return _ts_string_text(index)
    if index.type == "template_string":
        return _ts_static_template_text(index)
    return None


# T-0432: a single-substitution template literal (`` `${key}` ``) whose
# ENTIRE content is that one substitution, no surrounding text -- the
# shape `_ts_single_substitution_identifier` extracts a candidate
# identifier name from, for `_ts_bound_subscript_text`'s local-constant
# lookup to then try resolving.
def _ts_single_substitution_identifier(node) -> str | None:  # noqa: ANN001
    """If `node` is a `template_string` whose ONLY content is one
    `template_substitution` wrapping a bare `identifier` (`` `${key}` ``,
    no other text) -- that identifier's name; `None` for any other shape
    (surrounding text, more than one substitution, or a non-identifier
    substitution expression, e.g. `` `${a}${b}` ``/`` `pre${x}` ``/
    `` `${obj.prop}` ``)."""
    if node.type != "template_string":
        return None
    substitutions = [c for c in node.children if c.type == "template_substitution"]
    fragments = [c for c in node.children if c.type == "string_fragment"]
    if len(substitutions) != 1 or fragments:
        return None
    sub = substitutions[0]
    inner = [c for c in sub.children if c.type not in ("${", "}")]
    if len(inner) != 1 or inner[0].type != "identifier":
        return None
    return node_text(inner[0])


def _ts_bound_subscript_text(index, string_bindings: dict[str, str]) -> str | None:  # noqa: ANN001
    """T-0432: light dataflow closing the TRIVIAL computed-subscript
    indirection the audit found (`const key = 'exec'; ax[key](url)`,
    `` ax[`${key}`](url) ``) -- when `index` is a bare identifier, or a
    template literal whose entire content is one identifier substitution,
    look its name up in `string_bindings` (built by
    `_ts_local_string_bindings`: every name in the file bound to exactly
    ONE, non-conflicting string-literal/no-interpolation-template-literal
    value). Deliberately conservative: a name reassigned to a non-literal
    anywhere, or bound to two different literals, is EXCLUDED from
    `string_bindings` entirely (never guesses which binding is live at the
    subscript site) -- this is dataflow-lite, not real reaching-definitions
    analysis, so it stays silent (returns `None`, same as an unresolved
    computed subscript) on anything past this one shape: a function-call
    result, string concatenation, a member-access key, or a name assigned
    more than one distinct literal value anywhere in the file."""
    if index.type == "identifier":
        return string_bindings.get(node_text(index))
    ident = _ts_single_substitution_identifier(index)
    if ident is not None:
        return string_bindings.get(ident)
    return None


def _resolve_ts_subscript(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
) -> str | None:  # noqa: ANN001
    """`subscript_expression` case of `_resolve_ts_expr` (T-0377 reviewer
    round 2, bracket-access evasion fix; extended round 3 for static
    template-literal subscripts; extended T-0432 for the trivial local-
    constant indirection case): `obj['fn']`/`` obj[`fn`] `` resolves the
    same as `obj.fn` when the subscript is a STRING LITERAL or a NO-
    INTERPOLATION TEMPLATE LITERAL (`require('axios')['get']`,
    `` ax[`get`] ``) -- a plain bracket-access RCE evasion the round-1
    resolver missed entirely (it only ever inspected `identifier`/
    `member_expression` nodes). T-0432 additionally resolves `obj[key]`/
    `` obj[`${key}`] `` when `key` is a local name bound to exactly one
    string literal in the file (`_ts_bound_subscript_text`) -- the trivial
    `const key = 'exec'; ax[key]()` indirection the audit called out. A
    GENUINELY computed subscript -- a function call, string concatenation,
    a member-access key, an interpolated template with surrounding text,
    or a name with no single resolvable literal binding -- still resolves
    to `None`, a documented limitation (module docstring below): giving up
    precision entirely for "any bracket access on a dangerous object is
    worth flagging" was considered and rejected as too high a false-
    positive cost (docs/audits/vet.md T-0432 candidates), so a real
    dangerous call reached only through genuine runtime-computed
    indirection is still NOT caught. Filed as a follow-up (T-draft-
    e7c8b53c) rather than silently accepted."""
    obj = node.child_by_field_name("object")
    index = node.child_by_field_name("index")
    if obj is None or index is None:
        return None
    # frob:invariant terminates reason="obj is node's own 'object' field child, a proper descendant of node in the finite tree-sitter parse tree; mutually recurses with _resolve_ts_expr, which only descends into the subscript/member branches by calling back here" measure="node's subtree depth strictly decreases"  # noqa: E501
    resolved_obj = _resolve_ts_expr(obj, import_table, scope_cache, string_bindings)
    if resolved_obj is None:
        return None
    static_text = _ts_static_subscript_text(index)
    if static_text is None:
        static_text = _ts_bound_subscript_text(index, string_bindings)
    if static_text is None:
        return None
    return f"{resolved_obj}.{static_text}"


def _resolve_ts_member(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
) -> str | None:  # noqa: ANN001
    """`member_expression` case of `_resolve_ts_expr` -- split out to keep
    that function under the arch length ceiling (T-0377 reviewer round
    2)."""
    obj = node.child_by_field_name("object")
    prop = node.child_by_field_name("property")
    if obj is None or prop is None:
        return None
    # frob:invariant terminates reason="obj is node's own 'object' field child, a proper descendant of node in the finite tree-sitter parse tree; mutually recurses with _resolve_ts_expr, which only descends into the subscript/member branches by calling back here" measure="node's subtree depth strictly decreases"  # noqa: E501
    resolved_obj = _resolve_ts_expr(obj, import_table, scope_cache, string_bindings)
    if resolved_obj is None:
        return None
    return f"{resolved_obj}.{node_text(prop)}"


def _resolve_ts_expr(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
) -> str | None:  # noqa: ANN001
    """Resolve one TS/JS expression node (a bare `identifier`, a
    `member_expression`/string-literal-`subscript_expression` chain, or an
    inline `require(...)`/dynamic `import(...)` call) to its fully-
    qualified import-bound target, or `None` if it is locally shadowed,
    unresolved, or not a resolvable chain at all (T-0377, extended by the
    reviewer-round-2 bracket-access/dynamic-import fixes and T-0432's
    local-constant subscript dataflow) -- mirrors `_resolve_py_expr`'s
    python job, without the T-0337 alias-copy-propagation layer (documented
    limitation above). Any other expression (a `new_expression`, a
    non-import ordinary call, ...) is not a resolvable "object" for chain
    purposes -- e.g. `new Job()` in `new Job().run()` stops resolution
    here, so `.run` never reaches the import table (the no-false-positive
    case)."""
    if node.type == "identifier":
        name = node_text(node)
        if _is_ts_shadowed(name, node, scope_cache):
            return None
        return import_table.get(name)
    if node.type == "member_expression":
        # frob:invariant terminates reason="mutually recurses with _resolve_ts_member, which only calls back here with node.child_by_field_name('object'), a proper descendant of node in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
        return _resolve_ts_member(node, import_table, scope_cache, string_bindings)
    if node.type == "subscript_expression":
        # frob:invariant terminates reason="mutually recurses with _resolve_ts_subscript, which only calls back here with node.child_by_field_name('object'), a proper descendant of node in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
        return _resolve_ts_subscript(node, import_table, scope_cache, string_bindings)
    if node.type == "call_expression":
        # T-0377 reviewer round 2: an INLINE `require('x')['fn']`/
        # `import('x')` used directly as the object of a member/subscript
        # chain, never bound to a name at all -- resolves the call itself
        # to its bare module text so the chain above it can keep going.
        return _ts_module_call_target(node)
    return None


def _collect_ts_candidates(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    candidates: list[tuple[str, int, int]],
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every call/member/subscript-access site that
    resolves through `import_table` (T-0377, extended by the reviewer-
    round-2 bracket-access fix and T-0432's local-constant subscript
    dataflow) -- mirrors `_collect_py_candidates`'s python job."""
    if node.type == "call_expression":
        func = node.child_by_field_name("function")
        if func is not None and func.type in (
            "identifier",
            "member_expression",
            "subscript_expression",
        ):
            resolved = _resolve_ts_expr(
                func, import_table, scope_cache, string_bindings
            )
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    elif node.type in ("member_expression", "subscript_expression"):
        resolved = _resolve_ts_expr(node, import_table, scope_cache, string_bindings)
        if resolved is not None:
            candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_ts_candidates(
            child, import_table, scope_cache, string_bindings, candidates
        )


def _ts_local_string_bindings(program_node) -> dict[str, str]:  # noqa: ANN001
    """T-0432: file-wide name -> literal-string-value table for every
    `const`/`let`/`var name = <value>` declarator whose value is a plain
    string literal or a no-interpolation template literal, when `name` has
    EXACTLY ONE such literal value across the whole file. A name assigned a
    non-literal value anywhere (a function call, another variable, string
    concatenation, ...), or assigned two DIFFERENT literal values (reused
    across unrelated scopes/branches), is deliberately EXCLUDED entirely --
    this is a conservative, no-false-claim approximation (never picks a
    "most likely" value), not real reaching-definitions dataflow; it only
    ever ADDS a resolution for the unambiguous single-literal-binding case
    `_ts_bound_subscript_text` needs, never removes or overrides a
    lexical-scan finding."""
    bindings: dict[str, str | None] = {}

    def record(name: str, value_node) -> None:  # noqa: ANN001
        """Fold one `name = value_node` binding site (declarator OR plain
        reassignment) into `bindings`, marking `name` permanently
        ambiguous (`None`) the instant it sees a non-literal value or a
        second, DIFFERENT literal value -- `let key = 'get'; key =
        'post';` must not resolve to either, since a real reassignment
        (T-0432 review: a bare declarator-only scan missed this) means the
        live value at any given subscript site is genuinely ambiguous to
        this file-wide, non-flow-sensitive pass."""
        if name in bindings and bindings[name] is None:
            return
        text = _ts_static_subscript_text(value_node)
        if text is None:
            bindings[name] = None
        elif name not in bindings:
            bindings[name] = text
        elif bindings[name] != text:
            bindings[name] = None

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if (
                name_node is not None
                and name_node.type == "identifier"
                and value_node is not None
            ):
                record(node_text(name_node), value_node)
        elif node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None and left.type == "identifier" and right is not None:
                record(node_text(left), right)
        for child in node.children:
            visit(child)

    visit(program_node)
    return {name: text for name, text in bindings.items() if text is not None}


def _ts_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_dotted_target, start_byte, end_byte)` this TS/JS
    file's call/member-access sites resolve to through its import/require
    binding table, enclosing-scope shadow check, and (T-0432) single-
    literal local-constant subscript table (T-0377). Empty for a
    non-typescript-bucket file, an unparseable file, or one `frob.lang` has
    no grammar for -- degrades to the pre-existing lexical-only scan, never
    raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "typescript":
        return ()

    import_table = _ts_import_table(tree.root_node)
    string_bindings = _ts_local_string_bindings(tree.root_node)
    scope_cache: dict[int, frozenset[str]] = {}
    candidates: list[tuple[str, int, int]] = []
    _collect_ts_candidates(
        tree.root_node, import_table, scope_cache, string_bindings, candidates
    )
    return tuple(candidates)


def _ts_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via TS/JS import/binding-aware resolution
    only (T-0377) -- the union of every registry needle that matches a
    resolved call/member target, for sites outside a comment span. Merged
    into `scan_file_capabilities`'s lexical result; adds recall (aliased/
    destructured/namespaced import evasions) without touching the existing
    raw-text path at all. Mirrors `_python_binding_capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _ts_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


def _ts_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` typescript entries observed via TS/JS import/
    binding-aware resolution only (T-0377) -- `_scan_file_operations`'s
    resolver-backed sibling to `_ts_binding_capabilities`. Mirrors
    `_python_binding_operations`."""
    candidates = _ts_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "typescript" or not entry.needles:
            continue
        for resolved, start, end in candidates:
            if _fully_in_any_span(start, end, comment_spans):
                continue
            if any(
                _needle_matches_resolved(needle, resolved) for needle in entry.needles
            ):
                matched.append(entry)
                break
    return tuple(matched)


# absolute paths of this module and the T-0158 registry it compiles
# `_PATTERNS` from -- both excluded from directory aggregation (T-0151/
# T-0158: `_capability_registry.DANGEROUS_OPERATIONS` stores every needle as
# a literal string, same self-match class as this file's derived `_PATTERNS`
# table, so scanning either against itself trivially "observes" every
# capability regardless of what the code actually does).
_SELF_PATH = Path(__file__).resolve()
_REGISTRY_PATH = (Path(__file__).parent / "_capability_registry.py").resolve()
# T-0153: `frob.strata._cve_fingerprint` stores every `CveFingerprint.needles`
# entry as a literal string too -- same self-match class as `_REGISTRY_PATH`
# above, so its own file is excluded from directory aggregation on the same
# grounds (module docstring's T-0151/T-0158 self-match note).
_FINGERPRINT_CATALOG_PATH = (
    Path(__file__).parent.parent / "strata" / "_cve_fingerprint.py"
).resolve()

# T-0253: `_SELF_PATH`/`_REGISTRY_PATH`/`_FINGERPRINT_CATALOG_PATH` above are
# identity anchors for THIS running package's own files -- correct only when
# the scanned tree and the running package are the SAME checkout (editable
# install: `uv run frob ...`). Under a non-editable global install (`uv tool
# install frob`), the running package's files resolve to a `site-packages`
# copy, so identity comparison against a SCANNED tree that is frob's own
# repo checkout never matches and every pattern-catalog needle self-matches
# again (36 false SYS100s under `frob sys audit` vs. 0 under `uv run frob
# sys audit`).
#
# Round 1 fix (REJECTED on review): matching by bare PATH SUFFIX (the last
# three path components: package dir / subpackage / filename) with no
# further check. That closed the false-positive but opened a real hole:
# `is_self_pattern_path` is reached from `_scan_directory_capabilities`/
# `_scan_directory_fingerprints`, the SAME public entrypoints `frob vet` uses
# to scan a VENDORED/THIRD-PARTY dependency tree. A malicious dependency
# that places a file at a path ending in `frob/vet/_capability.py` (trivial:
# nest it under any vendor path, or name the package `frob` outright) would
# be silently excluded from capability scanning by suffix alone --
# `is_self_pattern_path` cannot tell "we are auditing frob's own checkout"
# from "we are vetting someone else's tree that happens to mimic frob's
# layout" using the scanned PATH alone.
#
# Round 2 fix (this one): the suffix match stays as the within-frob file
# check, but it is only REACHABLE when a separate SCAN-TARGET discriminator,
# `_is_frob_repo_root`, says the tree actually being scanned is frob's own
# repository -- not the running package's install location (round 1's
# mistake), not the scanned FILE's path alone (round 1 REJECT's mistake),
# but the scanned tree's ROOT identity: `root/pyproject.toml` declares
# `name = "frob"` AND the root also has the `frob-core`/`strata-core` Rust
# crate directories this monorepo actually ships. Requiring both the name
# and the crate directories raises the forgery bar well past "name a PyPI
# package frob" -- a typosquat sdist would also need to vendor two dummy
# top-level directories with those exact names purely to fool this check,
# and gains nothing from doing so since `frob vet`'s dependency scan target
# is the DEPENDENCY's own extracted source root, not frob's repo root,
# in every real invocation. Self-conformance (`_selfconform.py`/
# `_effects.py`) always passes frob's own repo root as `root` by
# construction (self-conformance audits ITS OWN tree), so the discriminator
# is a no-op there; `frob vet` scanning a dependency passes that
# dependency's own source root, which is never frob's repo, so the
# discriminator (correctly) refuses the exclusion and the file gets scanned
# like any other.
_SELF_PATTERN_SUFFIXES: tuple[tuple[str, ...], ...] = (
    ("frob", "vet", "_capability.py"),
    ("frob", "vet", "_capability_registry.py"),
    ("frob", "strata", "_cve_fingerprint.py"),
)

#: `[project]`-table `name = "frob"` line, tomllib-free (matches this
#: module's existing "cheap substring/regex over parsing" posture) --
#: see `_is_frob_repo_root`.
_FROB_PROJECT_NAME_RE = re.compile(r'(?m)^\s*name\s*=\s*"frob"\s*$')


@lru_cache(maxsize=32)
def _is_frob_repo_root(root: Path) -> bool:
    """True if `root` (resolved) is frob's OWN repository checkout -- the
    scan-target discriminator `is_self_pattern_path` gates its suffix match
    on (T-0253 REJECT round). Requires ALL of: a `pyproject.toml` at `root`
    declaring `name = "frob"`, plus the `frob-core`/`strata-core` Rust crate
    directories this monorepo actually ships alongside it -- name alone is
    forgeable by a typosquat PyPI package; the crate directories are not
    something a dependency being vetted would have any reason to carry.

    Deliberately checks `root` ITSELF only, never an ancestor: `frob vet`
    locates a Python dependency's source under `<project-root>/.venv/lib/
    */site-packages/<name>` (`frob.vet._source._locate_pypi_source`), so
    when frob vets its OWN dependencies, every dependency's located source
    lives NESTED under frob's own repo root. Walking upward from that
    nested path would climb straight back to frob's own `pyproject.toml`/
    `frob-core`/`strata-core` and wrongly classify every one of frob's own
    third-party dependencies as "self" too -- turning the exclusion into a
    scanner-wide bypass for frob's own dependency tree, a strictly worse
    hole than the one this discriminator exists to close. Every real caller
    (self-conformance's `root`, `frob vet`'s located dependency `source_dir`)
    already passes the exact directory that should be checked; the exact
    directory is what this checks. Cached per resolved root: called once
    per file in a directory walk, and the answer cannot change mid-walk."""
    resolved = root.resolve()
    pyproject = resolved / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if not _FROB_PROJECT_NAME_RE.search(text):
        return False
    return (resolved / "frob-core").is_dir() and (resolved / "strata-core").is_dir()


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
SCANNED_LANGUAGES: frozenset[str] = frozenset(_EXT_LANGUAGE.values())


# frob:doc docs/modules/vet.md#public-api
def language_for(path: Path) -> str | None:
    """The pattern-table bucket for `path`'s extension (T-0158: C/C++ is now
    a first-class `"c-cpp"` bucket, not `None`), or `None` for an extension
    with no registry-backed language at all."""
    return _EXT_LANGUAGE.get(path.suffix.lower())


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="scan_file_capabilities 76.9% branch cover, debt T-0160"
def scan_file_capabilities(path: Path) -> frozenset[str]:
    """Capability tokens observed in one source file's raw text (T-0209:
    needle hits fully inside a tree-sitter comment span are excluded --
    see module docstring)."""
    language = language_for(path)
    if language is None:
        _log.debug("vet: no capability pattern table for %s; treating as opaque", path)
        return frozenset()
    table = _PATTERNS[language]
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.warning("vet: could not read %s for capability scan: %s", path, exc)
        return frozenset()

    comment_spans = _comment_byte_spans(path)
    found = _matched_capabilities(raw, table, language, comment_spans)
    if language == "python":
        # T-0328: import/binding-aware resolution catches aliased/from-
        # import evasions the raw-text needle scan above structurally
        # cannot (`import subprocess as sp; sp.run(x)`), without touching
        # the lexical path's own behavior at all.
        found |= _python_binding_capabilities(path, table, comment_spans)
        # T-0244: embedded HTML/JS string literals are invisible to the
        # lexical/binding passes above (both scan the file's OWN python
        # grammar text); this always adds `embedded_code` (fail-closed
        # declaration) plus any typescript-needle re-scan hits.
        found |= _embedded_capabilities(path)
    elif language == "typescript":
        # T-0377: TS/JS sibling of the T-0328 python binding pass above --
        # catches aliased/destructured/namespaced import evasions
        # (`import {run as r} from 'child_process'; r(x)`, `const {exec} =
        # require('child_process')`) the raw-text needle scan structurally
        # cannot.
        found |= _ts_binding_capabilities(path, table, comment_spans)
    elif language == "rust":
        # T-0378: Rust sibling of the T-0328/T-0377 binding passes above --
        # catches an `as`-aliased `use` import evasion (`use std::process::
        # Command as C; C::new(x)`) the raw-text needle scan structurally
        # cannot.
        found |= _rust_binding_capabilities(path, table, comment_spans)
    elif language == "c-cpp":
        # T-0379: C/C++ sibling of the T-0328/T-0377/T-0378 binding passes
        # above -- catches a macro-renamed dangerous call (`#define SYS
        # system; SYS(x)`) the raw-text needle scan structurally cannot.
        found |= _c_binding_capabilities(path, table, comment_spans)
    if found:
        _log.info("vet: %s: capabilities observed: %s", path, sorted(found))
    return frozenset(found)


def _matched_capabilities(
    text: bytes,
    table: dict[str, tuple[str, ...]],
    language: str,
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability tokens whose needle set appears anywhere in `text` outside
    a comment span (T-0209), plus any `_SPECIAL_CHECKS` hit for that
    language/capability (T-0151)."""
    found: set[str] = set()
    for capability, needles in table.items():
        if any(
            _needle_hits_outside_comments(text, needle.encode("utf-8"), comment_spans)
            for needle in needles
        ):
            found.add(capability)
    for capability, checks in _SPECIAL_CHECKS.get(language, {}).items():
        if any(check(text, comment_spans) for check in checks):
            found.add(capability)
    return found


# frob:ticket T-0158
# frob:waive ARCH001 reason="a linear read/match/extend orchestration pipeline over already-extracted helpers (raw-text match, T-0328 binding match, T-0244 embedded match); each step is a single named call, splitting further would multiply indirection without shrinking real complexity" ceiling="50"  # noqa: E501
def _scan_file_operations(path: Path) -> tuple[_DangerousOperation, ...]:
    """The specific `DANGEROUS_OPERATIONS` registry entries whose needle(s)
    matched in `path`'s raw text outside a comment span (T-0209) -- the
    richer sibling of `scan_file_capabilities` (T-0158 addendum 1) that
    lets a caller name WHICH library/function fired, not just the bare
    capability kind. An entry with no `needles` (bare-builtin `compile()`,
    matched only via `_has_bare_compile_call`) is included when that
    special check hits. Each registry entry appears at most once in the
    result, in registry order -- a dedupe-by-construction that also
    dedupes what a caller reports per (file, entry): the loop below visits
    every `DANGEROUS_OPERATIONS` entry exactly once and appends it at most
    once, so the same entry can never show up twice for the same file."""
    language = language_for(path)
    if language is None:
        return ()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.warning("vet: could not read %s for operation scan: %s", path, exc)
        return ()

    comment_spans = _comment_byte_spans(path)
    matched = [
        entry
        for entry in DANGEROUS_OPERATIONS
        if entry.language == language
        and _operation_entry_matches(entry, raw, comment_spans)
    ]
    if language == "python":
        # T-0328: same import/binding-aware resolution as
        # `scan_file_capabilities`, named-entry-granular so an audit
        # finding can still cite library/rationale/safer_alternative for
        # an aliased/from-import call the raw-text needle scan misses.
        matched.extend(_extra_binding_operations(path, comment_spans, matched))
        # T-0244: DANGEROUS_OPERATIONS entries matched inside an embedded
        # HTML/JS string-literal region, not already present above.
        seen = set(matched)
        for entry in _embedded_operations(path):
            if entry not in seen:
                matched.append(entry)
                seen.add(entry)
    elif language == "typescript":
        # T-0377: same import/binding-aware resolution as
        # `scan_file_capabilities`'s typescript branch, named-entry-
        # granular so an audit finding can still cite library/rationale/
        # safer_alternative for an aliased/destructured/namespaced call the
        # raw-text needle scan misses.
        matched.extend(_extra_ts_binding_operations(path, comment_spans, matched))
    elif language == "rust":
        # T-0378: same use/binding-aware resolution as
        # `scan_file_capabilities`'s rust branch, named-entry-granular so an
        # audit finding can still cite library/rationale/safer_alternative
        # for an aliased `use` call the raw-text needle scan misses.
        matched.extend(_extra_rust_binding_operations(path, comment_spans, matched))
    elif language == "c-cpp":
        # T-0379: same macro-alias-aware resolution as `scan_file_
        # capabilities`'s c-cpp branch, named-entry-granular so an audit
        # finding can still cite library/rationale/safer_alternative for a
        # macro-renamed call the raw-text needle scan misses.
        matched.extend(_extra_c_binding_operations(path, comment_spans, matched))
    return tuple(matched)


def _extra_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_python_binding_operations` entries not already present in
    `already_matched` (T-0328) -- a set-based dedupe (each `_DangerousOperation`
    is a frozen, hashable model) so `_scan_file_operations` never does an
    O(n) membership scan per resolved entry."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _python_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra


def _extra_ts_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_ts_binding_operations` entries not already present in
    `already_matched` (T-0377) -- TS/JS sibling of `_extra_binding_
    operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _ts_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra


# T-0378: import/binding-aware resolution for Rust, mirroring the T-0328
# python / T-0377 TS discipline above but scoped to what a Rust `use`
# statement actually needs: `use std::process::Command as C;` binds a local
# alias to a fully-qualified path, and a subsequent `C::new(...)` call must
# resolve to `std::process::Command::new` the same way `Command::new(...)`
# would -- the raw-text lexical scan looks for a literal `Command::new(`/
# `std::` substring, so a renamed `use` import evades it entirely.
#
# Bind table (`_rust_use_table`) forms:
#   use std::process::Command;        -> {"Command": "std::process::Command"}
#   use std::process::Command as C;   -> {"C": "std::process::Command"}
#   use foo;                          -> {"foo": "foo"}
# Grouped/nested `use` forms (`use std::fs::{self, File};`,
# `use a::{b, c as d};`) are a documented, deliberately out-of-scope
# limitation (T-0378) -- narrower than this pass's acceptance criteria
# (aliased `use` + local-shadow discipline), left for a follow-up ticket
# rather than risking an under-tested grammar-shape guess.
#
# Scope-awareness (mandatory, mirrors T-0328/T-0377): a function/closure
# PARAMETER or a local `let` binding of the same name as a `use`-bound alias
# SHADOWS it in every enclosing scope from the site up to the file
# (`source_file`) root -- `fn f() { let C = 5; C::new(...) }` (a local
# variable that happens to share the alias's name, then gets called like a
# path -- contrived but the same no-false-positive discipline as the
# python/TS resolvers) must not resolve `C` to the `use`-bound path.
#
# T-0378 ROUND 2 (reviewer REJECT -- soundness hole, T-0339 fail-closed):
# round 1's shadow check was ORDER-INSENSITIVE -- it collected every name
# bound ANYWHERE in the enclosing scope into a plain set, so a capability
# call textually BEFORE a same-named `let` rebinding was wrongly treated as
# already shadowed and silently dropped:
#
#   use std::process::Command as C;
#   fn f() {
#       C::new("sh");   // executes BEFORE `let C` -- MUST resolve to exec
#       let C = 5;
#   }
#
# A `let` binding does not hoist in Rust -- a use of the name before its
# `let` refers to whatever it resolved to beforehand (here, the `use`-bound
# alias), not the not-yet-effective local. Fixed: `_rust_scope_bound_names`
# now maps `name -> byte position from which it shadows`, not just `name`;
# `_rust_shadowing_scope` only treats a binding as shadowing a given call
# site when `site.start_byte >= that position` (`_RUST_ALWAYS_SHADOWS`, -1,
# for parameters and nested-fn-item names, which ARE in scope for the whole
# body/block by construction -- only `let` targets get a real position, the
# `let_declaration` node's own `start_byte`). A name rebound multiple times
# keeps its EARLIEST recorded position (`_record_rust_binding`): once truly
# shadowed, a call site stays shadowed, it never un-shadows.
_RUST_SCOPE_TYPES = ("function_item", "closure_expression", "source_file")


def _rust_path_text(node) -> str | None:  # noqa: ANN001
    """Flatten a `scoped_identifier` (`a::b::c`) or bare `identifier` node
    into its `::`-joined text, or `None` for any other node shape -- the
    Rust analog of walking a python `attribute` chain / TS `member_
    expression` into a dotted string."""
    if node.type == "identifier":
        return node_text(node)
    if node.type != "scoped_identifier":
        return None
    parts: list[str] = []

    def collect(n) -> None:  # noqa: ANN001
        if n.type == "identifier":
            parts.append(node_text(n))
        elif n.type == "scoped_identifier":
            for child in n.children:
                collect(child)

    collect(node)
    return "::".join(parts) if parts else None


def _bind_rust_use_as_clause(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `use_as_clause` node's contribution to `_rust_use_table`: `use
    PATH as ALIAS;` -> `{ALIAS: PATH}` (grammar shape: `[path_node, "as",
    alias_identifier]`, path first and alias last by construction)."""
    children = node.children
    if len(children) < 3:
        return
    alias_node = children[-1]
    if alias_node.type != "identifier":
        return
    full = _rust_path_text(children[0])
    if full:
        table[node_text(alias_node)] = full


def _bind_rust_use_declaration(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `use_declaration` node's contribution to `_rust_use_table`: an
    `as`-aliased path (`_bind_rust_use_as_clause`) or a bare path (`use
    std::process::Command;` -> `{"Command": "std::process::Command"}`,
    keyed by the path's last segment). Grouped/nested `use` lists
    (`scoped_use_list`/`use_list`) are not bound -- documented limitation,
    see the T-0378 block comment above."""
    for child in node.children:
        if child.type == "use_as_clause":
            _bind_rust_use_as_clause(child, table)
        elif child.type in ("identifier", "scoped_identifier"):
            full = _rust_path_text(child)
            if full:
                alias = full.rsplit("::", 1)[-1]
                table.setdefault(alias, full)


def _rust_use_table(root_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide local-alias -> resolved-path binding table (T-0378),
    built from every `use_declaration` in the tree (not just top-level --
    mirrors `_py_import_table`'s function-scoped-import over-approximation:
    a module/fn-local `use` still contributes a file-wide binding)."""
    table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "use_declaration":
            _bind_rust_use_declaration(node, table)
        for child in node.children:
            visit(child)

    visit(root_node)
    return table


#: sentinel `bound` position meaning "shadows from the very start of the
#: scope, regardless of call-site position" -- used for function/closure
#: PARAMETERS (always in scope for the whole body) and nested `fn` item
#: names (Rust hoists a block-local `fn`, so it can be called before its
#: textual definition within the same block). Only `let` bindings get a
#: REAL position (T-0378 round 2, see `_RUST_SCOPE_TYPES` block comment).
_RUST_ALWAYS_SHADOWS = -1


def _record_rust_binding(bound: dict[str, int], name: str, position: int) -> None:
    """Record that `name` starts shadowing an enclosing `use` alias at byte
    `position` within its scope, keeping the EARLIEST position on repeat
    bindings of the same name (a `let x` rebound twice still shadows from
    its first occurrence onward, never un-shadows) -- the position-aware
    T-0378 round 2 fix's core bookkeeping primitive."""
    existing = bound.get(name)
    bound[name] = position if existing is None else min(existing, position)


def _collect_rust_param_name(node, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add one `parameters`/`closure_parameters`-node child's bound name to
    `bound` at `_RUST_ALWAYS_SHADOWS` (a plain `identifier` for a closure
    param with no type annotation, or the leading `identifier` child of a
    `parameter`/`self_parameter` node -- the name always precedes the
    `:`/type in the Rust grammar, so the first `identifier` child found is
    the binding). A parameter is in scope for the WHOLE function body by
    construction, so it shadows regardless of call-site position -- no
    "used before declared" case exists for parameters the way it does for
    a mid-body `let`."""
    if node.type == "identifier":
        _record_rust_binding(bound, node_text(node), _RUST_ALWAYS_SHADOWS)
        return
    if node.type == "parameter":
        for child in node.children:
            if child.type == "identifier":
                _record_rust_binding(bound, node_text(child), _RUST_ALWAYS_SHADOWS)
                return


def _collect_rust_let_target(node, let_start: int, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add every name a `let_declaration` binds to `bound` AT `let_start`
    (the enclosing `let_declaration` node's own `start_byte`, T-0378 round
    2) -- stopping at the first `:` (type annotation) or `=` (initializer)
    child so only the PATTERN side is walked; recurses through simple
    nested patterns (e.g. a tuple pattern) collecting plain `identifier`
    leaves, mirroring `_collect_target_names`'s python job at Rust's
    coarser grain. Recording the BINDING's position (not `_RUST_ALWAYS_
    SHADOWS`) is what makes a call site textually BEFORE this `let` still
    resolve through the enclosing `use` alias instead of being wrongly
    treated as already shadowed."""
    for child in node.children:
        if child.type in (":", "="):
            break
        if child.type == "identifier":
            _record_rust_binding(bound, node_text(child), let_start)
        elif child.type not in ("let", "mutable_specifier"):
            _collect_rust_let_target(child, let_start, bound)


def _rust_scope_bind_step(node, is_top: bool, bound: dict[str, int]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_rust_scope_bound_names`'s walk: add whatever
    name(s) `node` binds directly to `bound` (with `_RUST_ALWAYS_SHADOWS`
    for params/nested-fn-names, or the `let_declaration`'s own `start_byte`
    for a `let` target, T-0378 round 2), and report whether the walk should
    recurse into `node`'s children (False at a nested scope boundary --
    mirrors `_scope_bind_step`'s python job)."""
    node_type = node.type
    if not is_top and node_type in ("function_item", "closure_expression"):
        if node_type == "function_item":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                _record_rust_binding(bound, node_text(name_node), _RUST_ALWAYS_SHADOWS)
        return False
    if node_type in ("parameters", "closure_parameters"):
        for child in node.children:
            _collect_rust_param_name(child, bound)
        return False
    if node_type == "let_declaration":
        _collect_rust_let_target(node, node.start_byte, bound)
    return True


def _rust_scope_bound_names(scope_node) -> dict[str, int]:  # noqa: ANN001
    """Every name bound DIRECTLY within `scope_node` (a `function_item`/
    `closure_expression`/`source_file` node), mapped to the byte position
    from which it starts shadowing an enclosing `use` alias -- parameters,
    `let` targets, and nested `fn`/closure names -- WITHOUT recursing into
    a nested scope's own body. T-0378 round 2: unlike the python/TS
    resolvers' plain name SET, this is POSITION-aware (`name -> start_
    byte`, `_RUST_ALWAYS_SHADOWS` for params/nested-fn-names) so a call
    site textually BEFORE a same-named `let` rebinding is correctly NOT
    treated as shadowed -- Rust `let` bindings do not hoist; a use before
    the `let` refers to whatever the name resolved to beforehand (here, the
    `use`-bound alias), same as the real Rust name-resolution rule this
    scanner approximates."""
    bound: dict[str, int] = {}

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _rust_scope_bind_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _rust_shadowing_scope(name: str, site, scope_cache: dict[int, dict[str, int]]):  # noqa: ANN001, ANN201
    """The nearest LOCAL scope node enclosing `site` that binds `name`
    directly AT OR BEFORE `site`'s own `start_byte` (per `_rust_scope_
    bound_names`, cached per scope node in `scope_cache`), or `None` if no
    enclosing scope binds it before this position -- the T-0378 shadow
    check every resolution goes through before consulting the `use`
    binding table. T-0378 round 2: POSITION-aware (fail-closed, T-0339) --
    a `let` binding recorded at a LATER byte position than `site` does NOT
    shadow this particular call site (it hasn't taken effect yet), so
    resolution correctly falls through to the `use` table instead of
    silently dropping a capability call that textually precedes its
    same-named local rebinding. Mirrors `_shadowing_scope`'s scope-walk
    shape, not its (order-insensitive) membership test."""
    cur = site.parent
    while cur is not None:
        if cur.type in _RUST_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = _rust_scope_bound_names(cur)
                scope_cache[key] = cached
            position = cached.get(name)
            if position is not None and site.start_byte >= position:
                return cur
            if cur.type == "source_file":
                break
        cur = cur.parent
    return None


def _rust_is_shadowed(name: str, site, scope_cache: dict[int, dict[str, int]]) -> bool:  # noqa: ANN001
    """True if `name` is bound by a local scope enclosing `site` AT OR
    BEFORE `site`'s position (T-0378 round 2 position-aware shadow check)
    -- thin bool wrapper over `_rust_shadowing_scope`, mirrors `_is_
    shadowed`."""
    return _rust_shadowing_scope(name, site, scope_cache) is not None


def _resolve_rust_identifier(
    node, use_table: dict[str, str], scope_cache: dict[int, dict[str, int]]
) -> str | None:  # noqa: ANN001
    """Resolve a bare `identifier` node to its `use`-bound target, or `None`
    if it is locally shadowed AT THIS POSITION (T-0378 round 2) or not
    `use`-bound at all."""
    name = node_text(node)
    if _rust_is_shadowed(name, node, scope_cache):
        return None
    return use_table.get(name)


def _resolve_rust_scoped(
    node, use_table: dict[str, str], scope_cache: dict[int, dict[str, int]]
) -> str | None:  # noqa: ANN001
    """Resolve a `scoped_identifier` chain (`Head::rest::of::path`) by
    resolving its leading segment through `_resolve_rust_identifier` and
    re-appending the remaining `::`-joined segments -- e.g. `C::new` with
    `C` bound to `std::process::Command` resolves to
    `std::process::Command::new`."""
    parts: list = []

    def collect(n) -> None:  # noqa: ANN001
        if n.type == "identifier":
            parts.append(n)
        elif n.type == "scoped_identifier":
            for child in n.children:
                collect(child)

    collect(node)
    if not parts:
        return None
    resolved_head = _resolve_rust_identifier(parts[0], use_table, scope_cache)
    if resolved_head is None:
        return None
    rest = "::".join(node_text(p) for p in parts[1:])
    return f"{resolved_head}::{rest}" if rest else resolved_head


def _resolve_rust_expr(
    node, use_table: dict[str, str], scope_cache: dict[int, dict[str, int]]
) -> str | None:  # noqa: ANN001
    """Resolve one Rust expression node (a bare `identifier` or a
    `scoped_identifier` chain) to its `use`-bound target, or `None` if it is
    locally shadowed or not `use`-bound. Mirrors `_resolve_py_expr`/
    `_resolve_ts_expr`'s dispatch."""
    if node.type == "identifier":
        return _resolve_rust_identifier(node, use_table, scope_cache)
    if node.type == "scoped_identifier":
        return _resolve_rust_scoped(node, use_table, scope_cache)
    return None


def _collect_rust_candidates(
    node,
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    candidates: list[tuple[str, int, int]],
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every `call_expression` whose `function` resolves
    through `use_table` (T-0378) -- mirrors `_collect_py_candidates`/
    `_collect_ts_candidates`'s job. Only the call site's function target is
    a resolvable "path" here (a bare `Command::new` field/method-style
    resolution beyond a plain scoped call is not attempted, matching this
    pass's narrower acceptance criteria)."""
    if node.type == "call_expression":
        func = node.child_by_field_name("function")
        if func is not None and func.type in ("identifier", "scoped_identifier"):
            resolved = _resolve_rust_expr(func, use_table, scope_cache)
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_rust_candidates(child, use_table, scope_cache, candidates)


def _rust_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_path, start_byte, end_byte)` this Rust file's call
    sites resolve to through its `use` binding table and POSITION-aware
    enclosing-scope shadow check (T-0378, round 2 fixes an order-
    insensitivity soundness hole -- see `_rust_scope_bound_names`). Empty
    for a non-rust file, an unparseable file, or one `frob.lang` has no
    grammar for -- degrades to the pre-existing lexical-only scan, never
    raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "rust":
        return ()

    use_table = _rust_use_table(tree.root_node)
    scope_cache: dict[int, dict[str, int]] = {}
    candidates: list[tuple[str, int, int]] = []
    _collect_rust_candidates(tree.root_node, use_table, scope_cache, candidates)
    return tuple(candidates)


def _rust_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via Rust `use`/binding-aware resolution
    only (T-0378) -- the union of every registry needle that matches a
    resolved call target, for sites outside a comment span. Merged into
    `scan_file_capabilities`'s lexical result; adds recall (aliased `use`
    evasions) without touching the existing raw-text path at all. Mirrors
    `_python_binding_capabilities`/`_ts_binding_capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _rust_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


def _rust_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` rust entries observed via `use`/binding-aware
    resolution only (T-0378) -- `_scan_file_operations`'s resolver-backed
    sibling to `_rust_binding_capabilities`. Mirrors `_python_binding_
    operations`/`_ts_binding_operations`."""
    candidates = _rust_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "rust" or not entry.needles:
            continue
        for resolved, start, end in candidates:
            if _fully_in_any_span(start, end, comment_spans):
                continue
            if any(
                _needle_matches_resolved(needle, resolved) for needle in entry.needles
            ):
                matched.append(entry)
                break
    return tuple(matched)


def _extra_rust_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_rust_binding_operations` entries not already present in
    `already_matched` (T-0378) -- Rust sibling of `_extra_binding_
    operations`/`_extra_ts_binding_operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _rust_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra


# T-0379: import/binding-aware resolution for C/C++, the fourth binding
# resolver alongside T-0328 (python) / T-0377 (TS) / T-0378 (rust). C/C++'s
# dominant renaming idiom is the preprocessor, not an import system: `#define
# SYS system` makes `SYS("sh")` a call to `system` with no `"system("`
# substring anywhere in the file's own text, evading the raw-text needle
# scan the same way an aliased python `import`/rust `use` does. Only a
# SIMPLE object-like macro whose value is a single bare identifier is
# resolved (`#define SYS system`) -- a function-like macro (`#define SYS(x)
# system(x)`) is a `preproc_function_def` node, a structurally different
# shape, and is a documented, deliberately out-of-scope limitation here
# (mirrors the T-0378 grouped-`use` limitation note above): a function-like
# macro already re-expands to literal "system(" text at its call site in
# common usage, so the raw-text lexical scan still has a real (if weaker)
# chance at it, unlike the pure-rename case this resolver targets.
#
# A `using NAMESPACE::NAME;` declaration or namespace-qualified call site
# (`fs::system(...)` after `namespace fs = std;`) needs NO special
# resolution here: the registry's own needles are bare substrings
# (`"system("`), which still occur verbatim inside a qualified call --
# `_needle_hits_outside_comments` already catches those lexically. Type-only
# aliases (`typedef`/C++11 `using X = Y;` alias-declarations) do not rename
# a CALLABLE and are out of scope for the same reason.
#
# Shadow-awareness mirrors `_rust_shadowing_scope`'s POSITION-aware
# discipline (T-0378 round 2, T-0339 fail-closed): a local variable or
# function parameter sharing a macro alias's name must not have a call site
# textually BEFORE its own declaration wrongly treated as shadowed. Block
# scoping (nested `compound_statement` scopes each shadowing independently)
# is over-approximated to "the whole enclosing function" -- matching the
# python/rust resolvers' function-granularity, not per-block C scoping;
# documented, not a silent gap.
_C_SCOPE_TYPES = ("function_definition", "translation_unit")

#: sentinel `bound` position meaning "shadows from the very start of the
#: scope" -- used for function PARAMETERS (in scope for the whole body).
#: Mirrors `_RUST_ALWAYS_SHADOWS`.
_C_ALWAYS_SHADOWS = -1

#: macro name -> single bare-identifier alias target regex (T-0379): only
#: matches an object-like macro's fully-stripped value when it is itself a
#: valid identifier -- a function-like macro body, an expression, or a
#: multi-token replacement never matches and is left unresolved (documented
#: limitation, see the T-0379 block comment above).
_C_BARE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _c_macro_alias_table(root_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide macro-name -> resolved-target binding table (T-0379),
    built from every `preproc_def` (object-like `#define NAME VALUE`) whose
    stripped value is itself a bare identifier -- transitively chased
    (`#define A B` + `#define B system` resolves `A` to `system`) so a
    multi-hop rename still resolves, mirroring `_rust_use_table`'s file-wide
    over-approximation (a function-local `#define` still contributes a
    file-wide binding, since the C preprocessor has no block scope)."""
    raw: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "preproc_def":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if name_node is not None and value_node is not None:
                value = node_text(value_node).strip()
                if _C_BARE_IDENTIFIER_RE.match(value):
                    raw[node_text(name_node)] = value
        for child in node.children:
            visit(child)

    visit(root_node)

    resolved: dict[str, str] = {}
    for name in raw:
        seen: set[str] = set()
        cur = name
        while cur in raw and cur not in seen:
            seen.add(cur)
            cur = raw[cur]
        resolved[name] = cur
    return resolved


def _c_declared_name(node) -> str | None:  # noqa: ANN001
    """The identifier a C/C++ declarator node ultimately names, following
    its `declarator` field through any `pointer_declarator`/`array_
    declarator`/`init_declarator`/reference wrapper down to the innermost
    plain `identifier` leaf -- e.g. `int *system3 = 0` (`init_declarator` ->
    `pointer_declarator` -> `identifier`) resolves to `"system3"`. `None`
    for a declarator shape with no reachable identifier (e.g. an abstract
    declarator)."""
    # PERF006: rewritten from tail recursion to an explicit loop -- Python
    # has no TCO, and the walk depth tracks a declarator chain's nesting
    # (pointer/array/init/reference wrappers), which is not statically
    # bounded, so a loop removes the stack-overflow hazard outright rather
    # than merely proving a depth bound.
    while node is not None:
        if node.type == "identifier":
            return node_text(node)
        node = node.child_by_field_name("declarator")
    return None


def _c_collect_declaration_names(node, position: int, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add every name a `declaration` node binds to `bound` at `position`
    (T-0379, mirrors `_collect_rust_let_target`'s job at C's coarser
    grammar grain) -- a plain `declaration` node's direct children are
    either bare `identifier`s (`int x, y;`) or `init_declarator`s (`int x =
    5;`), so both shapes are scanned at the top level without needing to
    recurse past them."""
    for child in node.children:
        if child.type in ("identifier", "init_declarator"):
            name = _c_declared_name(child)
            if name:
                _record_rust_binding(bound, name, position)


def _c_scope_bind_step(node, is_top: bool, bound: dict[str, int]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_c_scope_bound_names`'s walk: add whatever
    name(s) `node` binds directly to `bound` (`_C_ALWAYS_SHADOWS` for a
    function parameter, the enclosing `declaration`'s own `start_byte` for
    a local variable, T-0379 mirrors T-0378 round 2's position-aware
    discipline), and report whether the walk should recurse into `node`'s
    children (False at a nested function boundary or once a binding node
    has been fully handled -- mirrors `_rust_scope_bind_step`'s job)."""
    node_type = node.type
    if not is_top and node_type == "function_definition":
        return False
    if node_type == "parameter_declaration":
        name = _c_declared_name(node.child_by_field_name("declarator"))
        if name:
            _record_rust_binding(bound, name, _C_ALWAYS_SHADOWS)
        return False
    if node_type == "declaration":
        _c_collect_declaration_names(node, node.start_byte, bound)
        return False
    return True


def _c_scope_bound_names(scope_node) -> dict[str, int]:  # noqa: ANN001
    """Every name bound within `scope_node` (a `function_definition`/
    `translation_unit` node, T-0379), mapped to the byte position from
    which it starts shadowing an enclosing macro alias -- function
    parameters and local variable declarations -- WITHOUT recursing into a
    nested function's own body. Mirrors `_rust_scope_bound_names`'s
    position-aware (`name -> start_byte`) shape, over-approximated to
    function granularity rather than per-`compound_statement` C block
    scoping (documented, see the T-0379 block comment above)."""
    bound: dict[str, int] = {}

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _c_scope_bind_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _c_shadowing_scope(name: str, site, scope_cache: dict[int, dict[str, int]]):  # noqa: ANN001, ANN201
    """The nearest enclosing `_C_SCOPE_TYPES` node that binds `name` at or
    before `site`'s own `start_byte` (per `_c_scope_bound_names`, cached per
    scope node), or `None` if no enclosing scope shadows the macro alias at
    this position -- the T-0379 shadow check every resolution goes through,
    mirroring `_rust_shadowing_scope`'s walk/cache shape and position-aware
    (fail-closed, T-0339) semantics."""
    cur = site.parent
    while cur is not None:
        if cur.type in _C_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = _c_scope_bound_names(cur)
                scope_cache[key] = cached
            position = cached.get(name)
            if position is not None and site.start_byte >= position:
                return cur
            if cur.type == "translation_unit":
                break
        cur = cur.parent
    return None


def _c_is_shadowed(name: str, site, scope_cache: dict[int, dict[str, int]]) -> bool:  # noqa: ANN001
    """True if `name` is bound by a local scope enclosing `site` at or
    before `site`'s position (T-0379) -- thin bool wrapper over `_c_
    shadowing_scope`, mirrors `_rust_is_shadowed`."""
    return _c_shadowing_scope(name, site, scope_cache) is not None


def _resolve_c_identifier(
    node, alias_table: dict[str, str], scope_cache: dict[int, dict[str, int]]
) -> str | None:  # noqa: ANN001
    """Resolve a bare `identifier` call-target node to its macro-aliased
    target, or `None` if it is locally shadowed at this position (T-0379)
    or not macro-bound at all."""
    name = node_text(node)
    if _c_is_shadowed(name, node, scope_cache):
        return None
    return alias_table.get(name)


def _collect_c_candidates(
    node,
    alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    candidates: list[tuple[str, int, int]],
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every `call_expression` whose `function` is a bare
    `identifier` that resolves through `alias_table` (T-0379) -- mirrors
    `_collect_rust_candidates`'s job. A qualified/namespaced or field-
    expression call target is not a resolvable macro alias by construction
    (a macro name is always a single bare identifier) and is skipped."""
    if node.type == "call_expression":
        func = node.child_by_field_name("function")
        if func is not None and func.type == "identifier":
            resolved = _resolve_c_identifier(func, alias_table, scope_cache)
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_c_candidates(child, alias_table, scope_cache, candidates)


def _c_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_name, start_byte, end_byte)` this C/C++ file's call
    sites resolve to through its macro alias table and POSITION-aware
    enclosing-scope shadow check (T-0379). Empty for a non-c/cpp file, an
    unparseable file, or one `frob.lang` has no grammar for -- degrades to
    the pre-existing lexical-only scan, never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label not in ("c", "cpp"):
        return ()

    alias_table = _c_macro_alias_table(tree.root_node)
    scope_cache: dict[int, dict[str, int]] = {}
    candidates: list[tuple[str, int, int]] = []
    _collect_c_candidates(tree.root_node, alias_table, scope_cache, candidates)
    return tuple(candidates)


def _c_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via C/C++ macro-alias-aware resolution only
    (T-0379) -- the union of every registry needle that matches a resolved
    call target, for sites outside a comment span. Merged into `scan_file_
    capabilities`'s lexical result; adds recall (macro-renamed dangerous
    calls) without touching the existing raw-text path at all. Mirrors
    `_rust_binding_capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _c_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


def _c_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` c-cpp entries observed via macro-alias-aware
    resolution only (T-0379) -- `_scan_file_operations`'s resolver-backed
    sibling to `_c_binding_capabilities`. Mirrors `_rust_binding_
    operations`."""
    candidates = _c_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "c-cpp" or not entry.needles:
            continue
        for resolved, start, end in candidates:
            if _fully_in_any_span(start, end, comment_spans):
                continue
            if any(
                _needle_matches_resolved(needle, resolved) for needle in entry.needles
            ):
                matched.append(entry)
                break
    return tuple(matched)


def _extra_c_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_c_binding_operations` entries not already present in
    `already_matched` (T-0379) -- C/C++ sibling of `_extra_rust_binding_
    operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _c_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra


def _operation_entry_matches(
    entry: _DangerousOperation, raw: bytes, comment_spans: tuple[ByteSpan, ...]
) -> bool:
    """Whether one `DANGEROUS_OPERATIONS` entry's needle(s) (or bare-compile
    special check) hit in `raw` outside `comment_spans`."""
    if entry.needles:
        return any(
            _needle_hits_outside_comments(raw, needle.encode("utf-8"), comment_spans)
            for needle in entry.needles
        )
    if entry.language == "python" and entry.function_or_pattern.startswith("compile("):
        return _has_bare_compile_call(raw, comment_spans)
    return False


# The CVE-fingerprint sibling of `_scan_file_operations` (T-0153): a
# fingerprint's `language` must match `path`'s scanned language bucket AND
# at least one of its `needles` must appear in the file's text, the SAME
# recall-over-precision substring philosophy `_matched_capabilities`
# already uses (module docstring). Imports `frob.strata` LAZILY (not at
# module scope): `frob.strata._effects` imports THIS module for its own
# `_PATTERNS`/`language_for` join, so a top-level `frob.strata` import
# here would be a genuine import cycle -- deferred until call time, when
# both packages have finished initializing.
# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
# frob:ticket T-0153
def _scan_file_fingerprints(path: Path) -> tuple[CveFingerprint, ...]:
    """The `frob.strata.CVE_FINGERPRINTS` entries whose needle(s) matched in
    `path`'s raw text."""
    from frob.strata import CVE_FINGERPRINTS

    language = language_for(path)
    if language is None:
        return ()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.warning("vet: could not read %s for fingerprint scan: %s", path, exc)
        return ()

    comment_spans = _comment_byte_spans(path)
    matched = tuple(
        entry
        for entry in CVE_FINGERPRINTS
        if entry.language == language
        and any(
            _needle_hits_outside_comments_ws(raw, needle.encode("utf-8"), comment_spans)
            for needle in entry.needles
        )
    )
    if matched:
        _log.info(
            "vet: %s: cve fingerprints matched: %s",
            path,
            sorted(entry.id for entry in matched),
        )
    return matched


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
def _decode_to_exec_signal(path: Path) -> bool:
    """True if one function's body reaches both a decode-ish and an exec-ish
    token (docs/modules/vet.md "eval-reachability": the highest-precision detector).

    Uses `frob.lang` symbol extraction so the two tokens must co-occur inside
    the SAME function body, not merely the same file.
    """
    language = language_for(path)
    if language is None:
        return False
    parsed = parse_file(path)
    if parsed.is_err:
        _log.debug(
            "vet: %s: parse failed for decode-to-exec scan: %s", path, parsed.danger_err
        )
        return False

    for symbol in parsed.danger_ok.symbols:
        if _body_reaches_decode_and_exec(" ".join(symbol.body_tokens)):
            _log.warning(
                "vet: decode-to-exec dataflow in %s::%s", path, symbol.qualname
            )
            return True
    return False


_DECODE_NEEDLES = (
    "base64",
    "b64decode",
    "atob",
    "fromhex",
    "fromCharCode",
    "decode(",
    "zlib.decompress",
)
_EXEC_NEEDLES = (
    "eval",
    "exec",
    "Function",
    "compile",
    "__import__",
    "vm.runInContext",
)


def _body_reaches_decode_and_exec(body: str) -> bool:
    """True if one function body's token text reaches both a decode-ish and an
    exec-ish token -- the co-occurrence VET004's highest-precision signal needs."""
    has_decode = any(needle in body for needle in _DECODE_NEEDLES)
    has_exec = any(needle in body for needle in _EXEC_NEEDLES)
    return has_decode and has_exec


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
def _scan_directory_capabilities(
    source_dir: Path, *, max_files: int = 500
) -> tuple[frozenset[str], bool]:
    """Aggregate capabilities across every scannable file under `source_dir`.

    Returns `(capabilities, decode_to_exec_hit)`. Bounded by `max_files` so a
    huge vendored dependency tree cannot make `frob vet` unusable.
    """
    capabilities, decode_to_exec_hit, scanned = _aggregate_capabilities(
        source_dir, max_files
    )
    _log.info(
        "vet: %s: scanned %d file(s), capabilities=%s, decode-to-exec=%s",
        source_dir,
        scanned,
        sorted(capabilities),
        decode_to_exec_hit,
    )
    return frozenset(capabilities), decode_to_exec_hit


def _is_test_path(path: Path) -> bool:
    """True for fixture files under a `test`/`tests` dir -- pure capability noise."""
    return "test" in path.parts or "tests" in path.parts


# True for this module's own source file, the T-0158 registry it compiles
# `_PATTERNS` from, or the T-0153 fingerprint catalog it matches
# `_scan_file_fingerprints` against (excluded from directory aggregation
# since all three contain every needle as literal data, guaranteeing a
# self-match unrelated to what the code does). Public (T-0201): the
# SINGLE shared self-match exclusion -- vet's own directory aggregation
# below AND every `frob.strata._selfconform`/`_effects` join path must
# call this same function rather than keep parallel private copies, or a
# future pattern-catalog file re-introduces the T-0151 self-match class
# in whichever join path forgot to exclude it. This was T-0201's root
# cause: `_selfconform.py`'s extended-kind/all-kind scans and
# `_effects.py`'s line-effect scan all predated this export and had no
# exclusion of their own.
#
# T-0253 round 1 (REJECTED): matched by `_SELF_PATTERN_SUFFIXES` (package-
# relative path suffix) alone, with no scan-target check. That closed the
# non-editable-install false positive but opened a real evasion hole: a
# malicious dependency placing a file at a path ending in
# `frob/vet/_capability.py` would be silently excluded from `frob vet`'s
# capability scan too, since suffix matching cannot distinguish "this is
# frob auditing itself" from "this is frob vetting someone else's tree
# that happens to mimic frob's layout."
#
# T-0253 round 2 (this version): `root` is now the caller's scan-target
# discriminator -- the suffix match only fires when `_is_frob_repo_root
# (root)` says `root` IS frob's own repository checkout (its own
# `pyproject.toml` name plus its `frob-core`/`strata-core` crate
# directories), never based on `path` alone and never based on where the
# RUNNING package's own files happen to live (round 0's bug, identity
# comparison against `_SELF_PATH` et al., which broke under a non-
# editable global install). `root` defaults to `None`, which ALWAYS
# fails the discriminator (fail-closed, deny-by-default, matching this
# codebase's charter posture elsewhere) -- a caller that omits `root`
# gets "never exclude, always scan" rather than a crash, so this stays
# source-compatible with any caller written against the pre-T-0253
# one-argument signature while still closing the evasion hole for every
# real caller in this repo (all of which pass `root` explicitly).
# Self-conformance callers (`_selfconform.py`/`_effects.py`) always pass
# frob's own repo root by construction, so this is a no-op there; `frob
# vet` scanning a dependency passes that dependency's own source root,
# which is never frob's repo, so the exclusion correctly never fires and
# the file is scanned like any other.
# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0201
# frob:ticket T-0253
def is_self_pattern_path(
    path: Path,
    root: Path | None = None,
    suffixes: tuple[tuple[str, ...], ...] = _SELF_PATTERN_SUFFIXES,
) -> bool:
    """True for this module's own source file, or the T-0158/T-0153 pattern
    catalogs it compiles from, when `root` is frob's own repo checkout.

    `suffixes` (T-0539) defaults to this module's own `_SELF_PATTERN_
    SUFFIXES` but lets an unrelated pattern-table gate (e.g.
    `frob.gates._pii_structural`'s PII011/PII012 detector-definition/
    corpus/fixture self-match class) reuse the SAME root-identity-gated
    discriminator (`_is_frob_repo_root` + path-suffix match) against its
    OWN suffix list, rather than re-deriving a second copy of this
    discriminator for a different pattern-table gate."""
    if root is None or not _is_frob_repo_root(root):
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    parts = resolved.parts
    return any(
        len(parts) >= len(suffix) and parts[-len(suffix) :] == suffix
        for suffix in suffixes
    )


def _is_self_path(path: Path, source_dir: Path) -> bool:
    """Private alias for `is_self_pattern_path` (T-0201) kept so this
    module's own two pre-existing call sites did not need a rename in the
    same diff as the export; new callers should use the public name.
    `source_dir` (T-0253) is the scan-target discriminator: the directory
    walk's own root, threaded straight through -- see `is_self_pattern_path`
    for why the exclusion must be gated on this rather than on `path`
    alone."""
    return is_self_pattern_path(path, source_dir)


def _aggregate_capabilities(
    source_dir: Path, max_files: int
) -> tuple[set[str], bool, int]:
    """Union capabilities plus a decode-to-exec hit across scannable files,
    bounded by `max_files`. Returns `(capabilities, hit, files_scanned)`."""
    capabilities: set[str] = set()
    decode_to_exec_hit = False
    scanned = 0
    for ext in _EXT_LANGUAGE:
        if scanned >= max_files:
            break
        # frob:ticket T-0471
        for path in iter_files(source_dir, suffix=ext):
            if scanned >= max_files:
                _log.warning(
                    "vet: %s: capability scan truncated at %d file(s)",
                    source_dir,
                    max_files,
                )
                break
            if _is_test_path(path) or _is_self_path(path, source_dir):
                continue
            capabilities |= scan_file_capabilities(path)
            if not decode_to_exec_hit:
                decode_to_exec_hit = _decode_to_exec_signal(path)
            scanned += 1
    return capabilities, decode_to_exec_hit, scanned


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
# frob:ticket T-0153
def _scan_directory_fingerprints(
    source_dir: Path, *, max_files: int = 500
) -> tuple["CveFingerprint", ...]:
    """Aggregate `frob.strata.CVE_FINGERPRINTS` matches across every scannable
    file under `source_dir` -- the fingerprint sibling of
    `_scan_directory_capabilities` (T-0153: wires `_scan_file_fingerprints`
    into the SAME directory-walk shape `_scan_source` (`frob.vet._scan`)
    already calls `_scan_directory_capabilities` from, so a dependency
    containing e.g. `yaml.load(...)`/`pickle.loads(...)` surfaces a real
    `frob vet` finding, not just a direct-import-only capability). Bounded
    by `max_files`, same test/self-path exclusions as `scan_directory_
    capabilities` (`_is_test_path`/`_is_self_path`)."""
    matched, scanned = _aggregate_fingerprints(source_dir, max_files)
    if matched:
        _log.info(
            "vet: %s: scanned %d file(s), fingerprints=%s",
            source_dir,
            scanned,
            sorted(entry.id for entry in matched),
        )
    return tuple(matched)


def _aggregate_fingerprints(
    source_dir: Path, max_files: int
) -> tuple[set["CveFingerprint"], int]:
    """Union `CveFingerprint` matches across scannable files, bounded by
    `max_files`. Returns `(matched, files_scanned)` -- the fingerprint
    sibling of `_aggregate_capabilities`, same walk/exclusion shape."""
    matched: set[CveFingerprint] = set()
    scanned = 0
    for ext in _EXT_LANGUAGE:
        if scanned >= max_files:
            break
        # frob:ticket T-0471
        for path in iter_files(source_dir, suffix=ext):
            if scanned >= max_files:
                _log.warning(
                    "vet: %s: fingerprint scan truncated at %d file(s)",
                    source_dir,
                    max_files,
                )
                break
            if _is_test_path(path) or _is_self_path(path, source_dir):
                continue
            matched.update(_scan_file_fingerprints(path))
            scanned += 1
    return matched, scanned


__all__ = [
    "SCANNED_LANGUAGES",
    "_decode_to_exec_signal",
    "is_self_pattern_path",
    "language_for",
    "_scan_directory_capabilities",
    "_scan_directory_fingerprints",
    "scan_file_capabilities",
    "_scan_file_fingerprints",
    "_scan_file_operations",
]
