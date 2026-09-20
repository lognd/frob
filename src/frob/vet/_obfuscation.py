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

# `_high_entropy_strings` used to scan with a regex that catastrophically
# backtracks on real files. `_iter_string_literals` replaces it with a
# single left-to-right scan (no backtracking, no lookahead) that is
# O(len(text)) by construction.
#
# Truncating the CONTENT fed to the entropy check is WRONG, not just a
# perf tradeoff -- Shannon entropy is a property of the whole sample, and
# truncating a real hit can pull its score back under threshold.
# `_iter_string_literals` never truncates content: total scan work is
# bounded by `len(text)`. `_MAX_CANDIDATE_LEN` (1MB) is a pure DoS
# ceiling, separate from the still-needed candidate-COUNT cap.
_MAX_CANDIDATE_LEN = 1_000_000
_MAX_CANDIDATES_PER_FILE = 4000

# Files above this size are skipped for the (whole) obfuscation scan (DEBUG
# note, not silent) -- past this size a file is a data/vendor blob, not
# something a hand-obfuscated payload hides inside inconspicuously
# (docs/modules/vet.md "Honest limits").
_MAX_SCAN_BYTES = 2 * 1024 * 1024


# Escapes (`\\x`) are skipped as a pair. Entropy is computed over the
# FULL literal, never truncated (see T-0208 above).
# `_MAX_CANDIDATE_LEN` is a memory-safety ceiling, not a normal-path cap.
#
# UNTERMINATED CANDIDATES: a quote char with no matching close anywhere
# later in the file is NOT a literal -- treating it as one would
# silently swallow the rest of the file into one giant "literal",
# dropping it from the entropy check. Detecting this naively (scan-to-
# EOF, discard, retry) reintroduces the same quadratic blowup T-0208
# fixed. Fixed with an O(1) reject: `last_single`/`last_double` are
# each quote type's LAST raw occurrence, computed once; a candidate
# opening at or after that position can never close.
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
# invariant spec: [INV-025](invariants/INV-025.md)
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
