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
"""

# frob:ticket T-0151
# frob:ticket T-0158
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from frob.lang import parse_file
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


def _has_bare_compile_call(text: str) -> bool:
    """True if `compile(` appears as a bare builtin call, not a dotted method
    access like `re.compile(`/`ast.compile(` (T-0151: the builtin turning a
    code string into a code object is eval-adjacent; `re.compile(` is not,
    and was the entire source of this scanner's cross-file false positives)."""
    needle = "compile("
    idx = 0
    while True:
        idx = text.find(needle, idx)
        if idx == -1:
            return False
        prev = text[idx - 1] if idx > 0 else ""
        if prev != "." and not (prev.isalnum() or prev == "_"):
            return True
        idx += len(needle)


# language -> capability -> extra callable(text) -> bool, applied ON TOP of
# the plain substring needles above for needles that need one bit more
# context than "does this substring appear anywhere" (T-0151: `compile(`
# as a bare builtin call vs. `re.compile(`/`x.compile(` method access).
_SPECIAL_CHECKS: dict[str, dict[str, tuple[Callable[[str], bool], ...]]] = {
    "python": {"eval": (_has_bare_compile_call,)},
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


# frob:doc docs/modules/vet.md#public-api
def language_for(path: Path) -> str | None:
    """The pattern-table bucket for `path`'s extension (T-0158: C/C++ is now
    a first-class `"c-cpp"` bucket, not `None`), or `None` for an extension
    with no registry-backed language at all."""
    return _EXT_LANGUAGE.get(path.suffix.lower())


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="scan_file_capabilities 76.9% branch cover, debt T-0160"
def scan_file_capabilities(path: Path) -> frozenset[str]:
    """Capability tokens observed in one source file's raw text."""
    language = language_for(path)
    if language is None:
        _log.debug("vet: no capability pattern table for %s; treating as opaque", path)
        return frozenset()
    table = _PATTERNS[language]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("vet: could not read %s for capability scan: %s", path, exc)
        return frozenset()

    found = _matched_capabilities(text, table, language)
    if found:
        _log.info("vet: %s: capabilities observed: %s", path, sorted(found))
    return frozenset(found)


def _matched_capabilities(
    text: str, table: dict[str, tuple[str, ...]], language: str
) -> set[str]:
    """Capability tokens whose needle set appears anywhere in `text`, plus
    any `_SPECIAL_CHECKS` hit for that language/capability (T-0151)."""
    found: set[str] = set()
    for capability, needles in table.items():
        if any(needle in text for needle in needles):
            found.add(capability)
    for capability, checks in _SPECIAL_CHECKS.get(language, {}).items():
        if any(check(text) for check in checks):
            found.add(capability)
    return found


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0158
def scan_file_operations(path: Path) -> tuple[DangerousOperation, ...]:
    """The specific `DANGEROUS_OPERATIONS` registry entries whose needle(s)
    matched in `path`'s raw text -- the richer sibling of
    `scan_file_capabilities` (T-0158 addendum 1) that lets a caller name
    WHICH library/function fired, not just the bare capability kind. An
    entry with no `needles` (bare-builtin `compile()`, matched only via
    `_has_bare_compile_call`) is included when that special check hits."""
    language = language_for(path)
    if language is None:
        return ()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("vet: could not read %s for operation scan: %s", path, exc)
        return ()

    matched: list[DangerousOperation] = []
    # frob:waive PERF003 reason="flat scan of a fixed table, not a nested join"
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != language:
            continue
        if entry.needles:
            if any(needle in text for needle in entry.needles):
                matched.append(entry)
        elif entry.language == "python" and entry.function_or_pattern.startswith(
            "compile("
        ):
            if _has_bare_compile_call(text):
                matched.append(entry)
    return tuple(matched)


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0153
def scan_file_fingerprints(path: Path) -> tuple[CveFingerprint, ...]:
    """The `frob.strata.CVE_FINGERPRINTS` entries whose needle(s) matched in
    `path`'s raw text -- the CVE-fingerprint sibling of `scan_file_operations`
    (T-0153): a fingerprint's `language` must match `path`'s scanned language
    bucket AND at least one of its `needles` must appear in the file's text,
    the SAME recall-over-precision substring philosophy `_matched_
    capabilities` already uses (module docstring). Imports `frob.strata`
    LAZILY (not at module scope): `frob.strata._effects` imports THIS module
    for its own `_PATTERNS`/`language_for` join, so a top-level `frob.strata`
    import here would be a genuine import cycle -- deferred until call time,
    when both packages have finished initializing."""
    from frob.strata import CVE_FINGERPRINTS

    language = language_for(path)
    if language is None:
        return ()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("vet: could not read %s for fingerprint scan: %s", path, exc)
        return ()

    matched = tuple(
        entry
        for entry in CVE_FINGERPRINTS
        if entry.language == language
        and any(needle in text for needle in entry.needles)
    )
    if matched:
        # frob:waive PERF004 reason="one sort for a single log call, not per-iteration"
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


def _is_self_path(path: Path) -> bool:
    """True for this module's own source file, the T-0158 registry it
    compiles `_PATTERNS` from, or the T-0153 fingerprint catalog it matches
    `scan_file_fingerprints` against (excluded from directory aggregation
    since all three contain every needle as literal data, guaranteeing a
    self-match unrelated to what the code does)."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return resolved in (_SELF_PATH, _REGISTRY_PATH, _FINGERPRINT_CATALOG_PATH)


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
            if _is_test_path(path) or _is_self_path(path):
                continue
            capabilities |= scan_file_capabilities(path)
            if not decode_to_exec_hit:
                decode_to_exec_hit = decode_to_exec_signal(path)
            scanned += 1
    return capabilities, decode_to_exec_hit, scanned


__all__ = [
    "decode_to_exec_signal",
    "language_for",
    "scan_directory_capabilities",
    "scan_file_capabilities",
    "scan_file_fingerprints",
    "scan_file_operations",
]
