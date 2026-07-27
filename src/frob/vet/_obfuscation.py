"""The VET004 obfuscation ensemble (docs/modules/vet.md "Obfuscation detection").

Implements the tractable slice: string-literal Shannon entropy vs a fixed
per-language baseline, Unicode bidi/zero-width/homoglyph scan (deterministic,
always fatal), and hex-identifier ratio (obfuscator.io-style `_0x...` names).
Decode-to-exec dataflow lives in `_capability.py` (it needs `frob.lang`
symbol bodies, not raw text). Detection is fatal, never "deobfuscate and
judge" (docs/modules/vet.md).

Cut from this slice (documented, not hidden -- docs/modules/vet.md "Honest limits"):
packer/flattener AST-shape metrics (dispatch-loop density, opaque
predicates), evasion-trigger conditional-guard queries, and stego scans over
non-code files. These need a cost/benefit case tree-sitter queries alone
don't cheaply buy; VET008 (artifact/source divergence) that would corroborate
the minified-vs-obfuscated call is also out of scope here (0.2.x proper).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/vet/_obfuscation.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from frob.excludes import iter_files
from frob.logging import get_logger

_log = get_logger(__name__)

# Per-language entropy baseline: legitimate source string literals (URLs,
# format strings, docstrings) cluster well below this; base64/hex blobs
# cluster above it. Deliberately conservative to keep false positives low.
_ENTROPY_THRESHOLD = 4.5
_MIN_STRING_LEN = 24

# T-0208: `_high_entropy_strings` used to scan with a regex whose alternation
# `(?:\\.|(?!\1).)*` catastrophically backtracks on real files -- a 9.6KB
# fixture (blib2to3/pgen2/conv.py, stdlib-adjacent, nothing adversarial in
# it) profiled at ~90ms in the regex alone vs ~0.3ms for the entropy math
# over the same matches, and the pilot-repo profile that filed this ticket
# showed 82 of 120 profiled seconds inside this function across 785 calls.
# `_iter_string_literals` below replaces it with a single left-to-right scan
# (no backtracking, no lookahead) that is O(len(text)) by construction.
#
# T-0208 review round 2: a 4096-char truncation of the CONTENT fed to the
# entropy check (rather than just the returned/logged snippet) is WRONG,
# not just a perf tradeoff -- Shannon entropy is a property of the whole
# sample, and truncating a real hit can pull its score back under
# threshold. Measured on a real file (cryptography's pkcs7.py, a
# mismatched-quote span, not even a real payload): entropy(full 7575-char
# span) = 4.602 (fires, matches the old regex), entropy(same span
# truncated to 4096) = 4.472 (silent -- a genuine detection loss, not the
# disclosed "truncating a base64 blob still trips on its opening bytes"
# case that reasoning assumed). `_iter_string_literals` therefore no
# longer truncates content: the O(n) argument for the underlying scan
# does not depend on a length cap -- every successful (closing) literal's
# scan consumes its own span once and the outer loop never revisits those
# characters, so total scan work across ALL successful literals in a file
# is bounded by `len(text)` regardless of how any single literal's length
# is distributed; only a FAILED open needs to be O(1) (the
# `last_single`/`last_double` reject below already guarantees that). What
# remains is a pure memory/DoS safety ceiling, `_MAX_CANDIDATE_LEN`,
# raised to 1MB so it is never reached by a real source string and only
# guards against a single-file OOM from an adversarial multi-hundred-MB
# "string". The candidate-COUNT cap remains a distinct, still-needed
# safety valve against files with huge numbers of small quoted tokens
# (generated data tables).
_MAX_CANDIDATE_LEN = 1_000_000
_MAX_CANDIDATES_PER_FILE = 4000

# Files above this size are skipped for the (whole) obfuscation scan (DEBUG
# note, not silent) -- past this size a file is a data/vendor blob, not
# something a hand-obfuscated payload hides inside inconspicuously
# (docs/modules/vet.md "Honest limits").
_MAX_SCAN_BYTES = 2 * 1024 * 1024


# Escapes (`\\x`) are skipped as a pair. Entropy is computed over the FULL
# literal, never truncated (review round 2 -- see the T-0208 note above:
# truncating changes the entropy score and can hide a real hit).
# `_MAX_CANDIDATE_LEN` is a 1MB memory-safety ceiling, not a normal-path
# cap; the file is capped at `_MAX_CANDIDATES_PER_FILE` literals.
#
# UNTERMINATED CANDIDATES (review round 1 caught this): a quote char with
# no matching close anywhere later in the file is NOT a literal -- it
# matches the OLD regex's actual behavior (a failed match attempt at that
# start position, retried one char later), not "run to end of text".
# Treating it as a literal was an undisclosed behavior change: after a
# mismatched-quote region consumes the file's last `'`, the old regex
# gives up on that open quote and correctly re-syncs on the next
# docstring's triple-quote; the old (buggy) version of this function
# instead swallowed that docstring into one giant unterminated "literal",
# silently DROPPING it from the entropy check -- a detection gap, not a
# disclosed false-positive tradeoff.
#
# Detecting "no closing quote anywhere later" naively (scan-to-EOF, then
# discard and retry one char over) reintroduces the exact quadratic
# blowup T-0208 fixed, for a file with many trailing unmatched quote
# chars. Fixed with an O(1) reject: `last_single`/`last_double` are each
# quote type's LAST raw occurrence in the text, computed once; if a
# candidate opens at or after that position, it can never close and is
# rejected without scanning -- one linear pre-pass plus O(1) per
# rejection keeps the whole function O(len(text)).
# frob:waive PERF003 reason="two-pointer scan not a join; each char visited once, O(n)"
def _iter_string_literals(text: str) -> list[str]:
    """Single-pass, backtracking-free scan for `'...'`/`"..."` literal
    bodies (single-char delimiters only, matching the prior regex's scope)."""
    n = len(text)
    literals: list[str] = []
    last_single = text.rfind("'")
    last_double = text.rfind('"')
    i = 0
    while i < n and len(literals) < _MAX_CANDIDATES_PER_FILE:
        i, literal = _consume_one_candidate(text, i, n, last_single, last_double)
        if literal is not None:
            literals.append(literal)
    return literals


def _consume_one_candidate(
    text: str, i: int, n: int, last_single: int, last_double: int
) -> tuple[int, str | None]:
    """Advance past `text[i]`: either a matched literal body (returned) and
    the index just past its closing quote, or a rejected candidate/
    non-quote char and `i + 1`."""
    ch = text[i]
    if ch not in ("'", '"'):
        return i + 1, None
    quote = ch
    last_occurrence = last_single if quote == "'" else last_double
    if last_occurrence <= i:
        # No further occurrence of `quote` exists anywhere later in the
        # file -- this candidate cannot close. Fail in O(1), matching the
        # old regex's "no match at this start position".
        return i + 1, None
    start = i + 1
    end = _scan_literal_end(text, quote, start, n)
    if end is None:
        # The raw last-occurrence pre-check said a `quote` exists later,
        # but every one of them was consumed as the second half of a
        # `\\.` escape pair before we reached it -- still "cannot close",
        # just discovered by the careful scan instead of the fast
        # pre-check. Same fail-and-retry-one-char-over outcome.
        return i + 1, None
    next_i = (end + 1) if end < n and text[end] == quote else max(end, i + 1)
    return next_i, text[start:end]


def _scan_literal_end(text: str, quote: str, start: int, n: int) -> int | None:
    """The index of `quote`'s closing occurrence starting from `start`
    (escape-pair-aware, capped at `_MAX_CANDIDATE_LEN`), or `None` if it
    never closes within that cap."""
    j = start
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == quote:
            return j
        if j - start >= _MAX_CANDIDATE_LEN:
            return j
        j += 1
    return None


# Trojan Source (CVE-2021-42574) bidi overrides + zero-width characters.
# Written as codepoints (not literal glyphs) to keep this file pure ASCII.
_BIDI_ZERO_WIDTH = {
    chr(0x202A),  # LEFT-TO-RIGHT EMBEDDING
    chr(0x202B),  # RIGHT-TO-LEFT EMBEDDING
    chr(0x202C),  # POP DIRECTIONAL FORMATTING
    chr(0x202D),  # LEFT-TO-RIGHT OVERRIDE
    chr(0x202E),  # RIGHT-TO-LEFT OVERRIDE
    chr(0x2066),  # LEFT-TO-RIGHT ISOLATE
    chr(0x2067),  # RIGHT-TO-LEFT ISOLATE
    chr(0x2068),  # FIRST STRONG ISOLATE
    chr(0x2069),  # POP DIRECTIONAL ISOLATE
    chr(0x200B),  # ZERO WIDTH SPACE
    chr(0x200C),  # ZERO WIDTH NON-JOINER
    chr(0x200D),  # ZERO WIDTH JOINER
    chr(0xFEFF),  # ZERO WIDTH NO-BREAK SPACE / BOM
}

_HEX_IDENTIFIER_RE = re.compile(r"\b_0x[0-9a-fA-F]{4,}\b")
_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_HEX_RATIO_THRESHOLD = 0.15


def _shannon_entropy(s: str) -> float:
    """Bits/char Shannon entropy; 0.0 for an empty string."""
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _high_entropy_strings(text: str) -> tuple[str, ...]:
    """String literals whose Shannon entropy exceeds the baseline -- likely
    base64/hex/packed payloads rather than legitimate code strings. O(len(text))
    single-pass scan (T-0208 -- see the module-level note on the regex this
    replaced)."""
    hits = []
    for literal in _iter_string_literals(text):
        if len(literal) < _MIN_STRING_LEN:
            continue
        entropy = _shannon_entropy(literal)
        if entropy >= _ENTROPY_THRESHOLD:
            hits.append(literal[:40])
    if hits:
        _log.warning("vet: %d high-entropy string literal(s) found", len(hits))
    return tuple(hits)


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:waive TEST005 reason="_invisible_text_signal 85.7% branch cover, debt T-0160"
def _invisible_text_signal(text: str) -> bool:
    """True if `text` contains a Unicode bidi override, zero-width character,
    or BOM outside the file's leading position -- the Trojan Source family.
    Deterministic, zero false positives, always fatal."""
    bom = chr(0xFEFF)
    for i, ch in enumerate(text):
        if ch in _BIDI_ZERO_WIDTH:
            if ch == bom and i == 0:
                continue  # a leading BOM is a legitimate encoding marker
            _log.error("vet: invisible/bidi character U+%04X found in source", ord(ch))
            return True
    return False


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _hex_identifier_ratio_signal(text: str) -> bool:
    """True if `_0x...`-style identifiers (obfuscator.io's default rename
    scheme) dominate the identifier population."""
    identifiers = _IDENTIFIER_RE.findall(text)
    if len(identifiers) < 20:
        return False
    hex_hits = len(_HEX_IDENTIFIER_RE.findall(text))
    ratio = hex_hits / len(identifiers)
    if ratio >= _HEX_RATIO_THRESHOLD:
        _log.warning("vet: hex-identifier ratio %.2f exceeds threshold", ratio)
        return True
    return False


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:waive TEST005 reason="_scan_text_obfuscation 85.7% branch cover, debt T-0160"
def _scan_text_obfuscation(text: str) -> tuple[str, ...]:
    """All obfuscation signal names present in `text` (empty = clean)."""
    signals: list[str] = []
    if _high_entropy_strings(text):
        signals.append("high-entropy-string")
    if _invisible_text_signal(text):
        signals.append("invisible-text")
    if _hex_identifier_ratio_signal(text):
        signals.append("hex-identifier-ratio")
    return tuple(signals)


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _scan_directory_obfuscation(
    source_dir: Path, *, max_files: int = 500
) -> tuple[str, ...]:
    """Union of obfuscation signals across every text-ish file under `source_dir`."""
    signals = _collect_dir_signals(source_dir, max_files)
    if signals:
        _log.warning("vet: %s: obfuscation signals: %s", source_dir, sorted(signals))
    return tuple(sorted(signals))


# T-0400 audit finding #5: C/C++/Kotlin were entirely excluded, so the
# deterministic Trojan-Source bidi/zero-width scan (CVE-2021-42574,
# demonstrated in C/C++) never ran on a C/C++/Kotlin dependency at all --
# not a precision tradeoff, a blind spot on the one sound detector in this
# module.
_SCANNABLE_SUFFIXES = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".kt",
)


def _collect_dir_signals(source_dir: Path, max_files: int) -> set[str]:
    """Union obfuscation signals over readable source files, bounded by `max_files`."""
    signals: set[str] = set()
    scanned = 0
    # frob:ticket T-0471
    for path in iter_files(source_dir):
        if scanned >= max_files:
            _log.warning(
                "vet: %s: obfuscation scan truncated at %d files", source_dir, max_files
            )
            break
        if path.suffix.lower() not in _SCANNABLE_SUFFIXES:
            continue
        text = _read_scannable_text(path)
        if text is None:
            continue
        signals |= set(_scan_text_obfuscation(text))
        scanned += 1
    return signals


def _read_scannable_text(path: Path) -> str | None:
    """`path`'s text if it's under `_MAX_SCAN_BYTES` and readable, else
    `None` (logged)."""
    try:
        if path.stat().st_size > _MAX_SCAN_BYTES:
            _log.debug(
                "vet: skipping %s for obfuscation scan: %d bytes exceeds "
                "%d-byte cap (T-0208)",
                path,
                path.stat().st_size,
                _MAX_SCAN_BYTES,
            )
            return None
    except OSError as exc:
        _log.warning("vet: could not stat %s for obfuscation scan: %s", path, exc)
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("vet: could not read %s for obfuscation scan: %s", path, exc)
        return None


__all__ = [
    "_hex_identifier_ratio_signal",
    "_high_entropy_strings",
    "_invisible_text_signal",
    "_scan_directory_obfuscation",
    "_scan_text_obfuscation",
]
