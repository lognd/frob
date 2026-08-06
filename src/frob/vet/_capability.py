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

T-0769: docstring prose counted as observed capability. T-0209's comment-span
exclusion above only ever covered tree-sitter COMMENT nodes; a python
module/class/function-head DOCSTRING is a `string` expression-statement, a
completely different node type, so needle prose written there (e.g.
`_concurrency.py`'s fork/pool-hazard docstrings literally spelling
`subprocess.Popen(...)`/`os.fork()`) fell straight through the comment
filter and was observed as a real capability -- a docstring is a non-
executable string CONSTANT, it cannot spawn a process, so excluding it from
raw-text observation is sound and does not weaken the fail-closed posture
for executable code (the string-literal carve-out in the T-0209 paragraph
above is about ordinary in-code string literals that CAN be an exec vector,
e.g. an `eval`-shaped payload; a docstring never executes, so it is not
that case). `_docstring_byte_spans_from_tree` computes the same kind of
span `_comment_byte_spans_from_tree` does (T-1210 renamed both to take an
already-parsed tree rather than a path, so `_non_executable_byte_spans` can
share one `raw_tree` parse and cache the unioned, sorted result per
(path, content-hash) -- see that function's docstring in
`_capability_core.py`), for python only (the only language this module
extracts a docstring concept for at all), and `_non_executable_byte_spans`
unions the two -- every call site that used to pass `_comment_byte_spans`
now passes this union instead, so a needle inside a docstring is treated
exactly like a needle inside a `#` comment. Separately, T-0769 found the
SAME class of miss one level up: `frob.strata._effects._line_effects`'s
line-level needle scan (feeding THREAT004/`check_capability_conformance`,
which strata's SYS100 selfconform check delegates to) does its own raw
`needle in line` substring test with NO comment-or-docstring awareness at
all -- it does not even call into this module's span machinery. That was
the actual mechanism behind the reported `_concurrency.py:56` false
positive (prose inside a `#:` COMMENT, still missed because the line-level
path is comment-blind, not just docstring-blind). `non_executable_line_
numbers` below is the shared primitive both paths now use: `_effects.py`
was updated (T-0769, in this same ticket's expanded scope) to skip any
matched line that primitive reports as non-executable, closing both
instances of the same underlying gap with one span computation.

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

# frob:waive INV006 preset="split-carried-prose"
# frob:ticket T-0151
# frob:ticket T-0158
# frob:ticket T-0244
from __future__ import annotations

from pathlib import Path

from frob.logging import get_logger

from ._capability_c import (
    _c_binding_capabilities,
    _c_resolved_candidates,
    _extra_c_binding_operations,
)
from ._capability_core import (
    _EXT_LANGUAGE,
    _PATTERNS,
    _SPECIAL_CHECKS,
    ByteSpan,
    _embedded_capabilities,
    _embedded_operations,
    _matched_capabilities,
    _non_executable_byte_spans,
    _operation_entry_matches,
)
from ._capability_kotlin import _extra_kt_binding_operations, _kt_binding_capabilities
from ._capability_python import (
    _python_binding_capabilities,
    _python_binding_operations,
    _python_resolved_candidates,
)
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation
from ._capability_rust import (
    _extra_rust_binding_operations,
    _rust_binding_capabilities,
    _rust_resolved_candidates,
)
from ._capability_scan import (
    _arg_looks_literal,
    _byte_offset_inside_string_literal,
    _decode_to_exec_signal,
    _needle_construct_findings,
    _opaque_indirection_findings,
    _OpaqueFinding,
    _scan_directory_capabilities,
    _scan_directory_fingerprints,
    _scan_file_fingerprints,
    _split_top_level_args,
    _structural_opaque_findings,
    _subscript_key_looks_literal,
    is_self_pattern_path,
)
from ._capability_typescript import (
    _extra_ts_binding_operations,
    _ts_binding_capabilities,
    _ts_resolved_candidates,
)

_log = get_logger(__name__)


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


# frob:ticket T-0769
# frob:ticket T-0972
# frob:doc docs/modules/vet.md#public-api
# frob:waive AFFECT001 reason="T-1371 only widens the already-documented 'never raises' contract to cover a surprising span shape, not just the OSError read failure -- no observable behavior change, so docs/modules/vet.md#public-api needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
# frob:tests \
# tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_execut\
# able_line_numbers_surprising_span_shape_is_empty kind="unit"  # noqa: E501
def non_executable_line_numbers(path: Path) -> frozenset[int]:
    """Every 1-indexed line number in `path` that a comment or python
    docstring span (`_non_executable_byte_spans`, T-0209/T-0769) touches --
    the shared primitive `frob.strata._effects._line_effects`'s LINE-level
    needle scan uses to get the same comment/docstring exclusion this
    module's own raw-text scanners already apply, instead of duplicating
    span computation with its own, unfiltered `needle in line` check
    (T-0769: that duplication was the actual root cause of the reported
    `_concurrency.py:56` false positive -- a needle inside a `#:` COMMENT,
    missed because the line-level path never consulted comment spans at
    all, docstrings or not). A line is included if ANY part of it overlaps
    a non-executable span, not only a fully-covered line -- deliberately
    coarser than the byte-precise `_fully_in_any_span` check the set-level
    scanners use, since a caller here only has line numbers to filter
    against, never byte offsets. Returns an empty frozenset for a file with
    no comment/docstring spans at all (never raises)."""
    spans = _non_executable_byte_spans(path)
    if not spans:
        return frozenset()
    try:
        raw = path.read_bytes()
    except OSError:
        return frozenset()
    lines: set[int] = set()
    try:
        # frob:waive PERF002 reason="each (start, end) span needs its own byte-count query over a different sub-range; not a repeated identical count to hoist"  # noqa: E501
        for start, end in spans:
            first_line = raw.count(b"\n", 0, start) + 1
            last_line = raw.count(b"\n", 0, max(end - 1, 0)) + 1
            lines.update(range(first_line, last_line + 1))
    except (KeyError, TypeError, ValueError):
        # "Never raises" (this function's own docstring) covers a
        # surprising span shape too, not just the read failure above
        # (EXHAUST001/EXHAUST002, T-1371).
        return frozenset()
    except Exception:
        return frozenset()
    return frozenset(lines)


# frob:doc docs/modules/vet.md#public-api
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

    comment_spans = _non_executable_byte_spans(path)
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
        # T-0379/T-0662/T-0663: C/C++ sibling of the T-0328/T-0377/T-0378
        # binding passes above -- catches a macro-renamed dangerous call
        # (`#define SYS system; SYS(x)`) and (T-0662/T-0663) a function-
        # pointer variable/assignment/struct-field/array/default-arg/
        # structured-binding alias the raw-text needle scan structurally
        # cannot.
        found |= _c_binding_capabilities(path, table, comment_spans)
    elif language == "kotlin":
        # T-0664: kotlin sibling of the binding passes above -- catches an
        # `import ... as`-aliased or `::`-referenced dangerous call the
        # raw-text needle scan structurally cannot.
        found |= _kt_binding_capabilities(path, table, comment_spans)
    if found:
        _log.info("vet: %s: capabilities observed: %s", path, sorted(found))
    return frozenset(found)


# frob:ticket T-0158
# frob:ticket T-0565
# frob:waive ARCH001 reason="a linear read/match/extend orchestration pipeline over already-extracted helpers (raw-text match, T-0328 binding match, T-0244 embedded match, T-0662/T-0663/T-0664 per-language binding branches); each step is a single named call, splitting further would multiply indirection without shrinking real complexity" ceiling="70"  # noqa: E501
# frob:tests tests/test_vet.py::TestCapabilityScan.test_scan_file_operations_names_registry_entry  # noqa: E501
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

    comment_spans = _non_executable_byte_spans(path)
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
        # T-0379/T-0662/T-0663: same macro/alias-aware resolution as
        # `scan_file_capabilities`'s c-cpp branch, named-entry-granular so
        # an audit finding can still cite library/rationale/safer_
        # alternative for a macro-renamed or aliased call the raw-text
        # needle scan misses.
        matched.extend(_extra_c_binding_operations(path, comment_spans, matched))
    elif language == "kotlin":
        # T-0664: same import/alias-aware resolution as `scan_file_
        # capabilities`'s kotlin branch, named-entry-granular so an audit
        # finding can still cite library/rationale/safer_alternative for an
        # aliased/`::`-referenced call the raw-text needle scan misses.
        matched.extend(_extra_kt_binding_operations(path, comment_spans, matched))
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


# T-0380: `_resolved_candidates_for_language` dispatches to whichever
# language's `_python_resolved_candidates`/`_ts_resolved_candidates`/
# `_rust_resolved_candidates`/`_c_resolved_candidates` binding table was
# already built for capability resolution (T-0328/T-0377/T-0378/T-0379) --
# one shared dispatch point so fingerprint scanning reuses the SAME
# resolver tables rather than growing its own copy (charter: no
# duplication). Kotlin is deliberately excluded: no `CVE_FINGERPRINTS`
# entry is tagged `language="kotlin"` today, so there is nothing for a
# `_kt_resolved_candidates` branch here to resolve against.
def _resolved_candidates_for_language(
    path: Path, language: str
) -> tuple[tuple[str, int, int], ...]:
    """The binding-resolved `(resolved_dotted_target, start, end)` triples
    for `path`, using whichever language's resolver table
    `_scan_file_fingerprints` needs -- empty for a language with no
    binding-aware resolver (returns () safely, degrading that language to
    lexical-only matching)."""
    if language == "python":
        return _python_resolved_candidates(path)
    if language == "typescript":
        return _ts_resolved_candidates(path)
    if language == "rust":
        return _rust_resolved_candidates(path)
    if language == "c-cpp":
        return _c_resolved_candidates(path)
    return ()


__all__ = [
    "SCANNED_LANGUAGES",
    "_OpaqueFinding",
    "_SPECIAL_CHECKS",
    "_decode_to_exec_signal",
    "is_self_pattern_path",
    "language_for",
    "_arg_looks_literal",
    "_byte_offset_inside_string_literal",
    "_needle_construct_findings",
    "_opaque_indirection_findings",
    "_scan_directory_capabilities",
    "_scan_directory_fingerprints",
    "_split_top_level_args",
    "_structural_opaque_findings",
    "_subscript_key_looks_literal",
    "scan_file_capabilities",
    "_scan_file_fingerprints",
    "_scan_file_operations",
]
