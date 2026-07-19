"""Tree-sitter-backed capability scan over a dependency's local source
(docs/modules/vet.md "Capability taxonomy" + "Mechanics").

Detection is a per-language token/substring scan over `frob.lang`-parsed
source (Python/JS-TS/Rust/C-C++ -- T-0158 adds C/C++ as a first-class
scanned language, retiring the old blanket "honestly-empty" exemption; see
`frob.vet._capability_registry` for the per-(kind, language) matrix that
now makes this claim checkable). A missing/unreadable file never crashes
the scan; it degrades to an empty capability set plus a
`source-unavailable`-shaped note (docs/modules/vet.md "Honest limits").

T-0158: `_PATTERNS` below is no longer hand-maintained needle tuples --
it is COMPILED from `frob.vet._capability_registry.DANGEROUS_OPERATIONS`,
the single-source structured dangerous-operations registry (one entry per
{language, library, function_or_pattern, capability_kind, cwe_links,
rationale, safer_alternative, severity}). `scan_file_capabilities` keeps
returning a bare `frozenset[str]` of capability kinds (its existing
public contract); `scan_file_operations` is the new richer entry point
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
`scan_directory_capabilities` excludes this module's own file from
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
"""

# frob:ticket T-0151
# frob:ticket T-0158
from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from frob.lang import COMMENT_TYPES, parse_file, raw_tree
from frob.logging import get_logger

from ._capability_registry import DANGEROUS_OPERATIONS, DangerousOperation

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
# `is_self_pattern_path` is reached from `scan_directory_capabilities`/
# `scan_directory_fingerprints`, the SAME public entrypoints `frob vet` uses
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
    */site-packages/<name>` (`frob.vet._source.locate_pypi_source`), so
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


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0158
def scan_file_operations(path: Path) -> tuple[DangerousOperation, ...]:
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
    return tuple(matched)


def _operation_entry_matches(
    entry: DangerousOperation, raw: bytes, comment_spans: tuple[ByteSpan, ...]
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


# The CVE-fingerprint sibling of `scan_file_operations` (T-0153): a
# fingerprint's `language` must match `path`'s scanned language bucket AND
# at least one of its `needles` must appear in the file's text, the SAME
# recall-over-precision substring philosophy `_matched_capabilities`
# already uses (module docstring). Imports `frob.strata` LAZILY (not at
# module scope): `frob.strata._effects` imports THIS module for its own
# `_PATTERNS`/`language_for` join, so a top-level `frob.strata` import
# here would be a genuine import cycle -- deferred until call time, when
# both packages have finished initializing.
# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0153
def scan_file_fingerprints(path: Path) -> tuple[CveFingerprint, ...]:
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
            _needle_hits_outside_comments(raw, needle.encode("utf-8"), comment_spans)
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
def decode_to_exec_signal(path: Path) -> bool:
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
def scan_directory_capabilities(
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
# `scan_file_fingerprints` against (excluded from directory aggregation
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
def is_self_pattern_path(path: Path, root: Path | None = None) -> bool:
    """True for this module's own source file, or the T-0158/T-0153 pattern
    catalogs it compiles from, when `root` is frob's own repo checkout."""
    if root is None or not _is_frob_repo_root(root):
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    parts = resolved.parts
    return any(
        len(parts) >= len(suffix) and parts[-len(suffix) :] == suffix
        for suffix in _SELF_PATTERN_SUFFIXES
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
        for path in source_dir.rglob(f"*{ext}"):
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
                decode_to_exec_hit = decode_to_exec_signal(path)
            scanned += 1
    return capabilities, decode_to_exec_hit, scanned


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0153
def scan_directory_fingerprints(
    source_dir: Path, *, max_files: int = 500
) -> tuple["CveFingerprint", ...]:
    """Aggregate `frob.strata.CVE_FINGERPRINTS` matches across every scannable
    file under `source_dir` -- the fingerprint sibling of
    `scan_directory_capabilities` (T-0153: wires `scan_file_fingerprints`
    into the SAME directory-walk shape `_scan_source` (`frob.vet._scan`)
    already calls `scan_directory_capabilities` from, so a dependency
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
        for path in source_dir.rglob(f"*{ext}"):
            if scanned >= max_files:
                _log.warning(
                    "vet: %s: fingerprint scan truncated at %d file(s)",
                    source_dir,
                    max_files,
                )
                break
            if _is_test_path(path) or _is_self_path(path, source_dir):
                continue
            matched.update(scan_file_fingerprints(path))
            scanned += 1
    return matched, scanned


__all__ = [
    "SCANNED_LANGUAGES",
    "decode_to_exec_signal",
    "is_self_pattern_path",
    "language_for",
    "scan_directory_capabilities",
    "scan_directory_fingerprints",
    "scan_file_capabilities",
    "scan_file_fingerprints",
    "scan_file_operations",
]
