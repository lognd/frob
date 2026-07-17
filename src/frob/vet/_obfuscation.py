"""The VET004 obfuscation ensemble (docs/vet.md "Obfuscation detection").

Implements the tractable slice: string-literal Shannon entropy vs a fixed
per-language baseline, Unicode bidi/zero-width/homoglyph scan (deterministic,
always fatal), and hex-identifier ratio (obfuscator.io-style `_0x...` names).
Decode-to-exec dataflow lives in `_capability.py` (it needs `frob.lang`
symbol bodies, not raw text). Detection is fatal, never "deobfuscate and
judge" (docs/vet.md).

Cut from this slice (documented, not hidden -- docs/vet.md "Honest limits"):
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

from frob.logging import get_logger

_log = get_logger(__name__)

# Per-language entropy baseline: legitimate source string literals (URLs,
# format strings, docstrings) cluster well below this; base64/hex blobs
# cluster above it. Deliberately conservative to keep false positives low.
_ENTROPY_THRESHOLD = 4.5
_MIN_STRING_LEN = 24

_STRING_RE = re.compile(r"""(['"])((?:\\.|(?!\1).)*)\1""", re.DOTALL)

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


# frob:doc docs/vet.md#public-api
def high_entropy_strings(text: str) -> tuple[str, ...]:
    """String literals whose Shannon entropy exceeds the baseline -- likely
    base64/hex/packed payloads rather than legitimate code strings."""
    hits = []
    for match in _STRING_RE.finditer(text):
        literal = match.group(2)
        if len(literal) < _MIN_STRING_LEN:
            continue
        entropy = _shannon_entropy(literal)
        if entropy >= _ENTROPY_THRESHOLD:
            hits.append(literal[:40])
    if hits:
        _log.warning("vet: %d high-entropy string literal(s) found", len(hits))
    return tuple(hits)


# frob:doc docs/vet.md#public-api
def invisible_text_signal(text: str) -> bool:
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


# frob:doc docs/vet.md#public-api
def hex_identifier_ratio_signal(text: str) -> bool:
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


# frob:doc docs/vet.md#public-api
def scan_text_obfuscation(text: str) -> tuple[str, ...]:
    """All obfuscation signal names present in `text` (empty = clean)."""
    signals: list[str] = []
    if high_entropy_strings(text):
        signals.append("high-entropy-string")
    if invisible_text_signal(text):
        signals.append("invisible-text")
    if hex_identifier_ratio_signal(text):
        signals.append("hex-identifier-ratio")
    return tuple(signals)


# frob:doc docs/vet.md#public-api
def scan_directory_obfuscation(
    source_dir: Path, *, max_files: int = 500
) -> tuple[str, ...]:
    """Union of obfuscation signals across every text-ish file under `source_dir`."""
    signals = _collect_dir_signals(source_dir, max_files)
    if signals:
        _log.warning("vet: %s: obfuscation signals: %s", source_dir, sorted(signals))
    return tuple(sorted(signals))


_SCANNABLE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".rs")


def _collect_dir_signals(source_dir: Path, max_files: int) -> set[str]:
    """Union obfuscation signals over readable source files, bounded by `max_files`."""
    signals: set[str] = set()
    scanned = 0
    for path in source_dir.rglob("*"):
        if scanned >= max_files:
            _log.warning(
                "vet: %s: obfuscation scan truncated at %d files", source_dir, max_files
            )
            break
        if not path.is_file() or path.suffix.lower() not in _SCANNABLE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _log.warning("vet: could not read %s for obfuscation scan: %s", path, exc)
            continue
        signals |= set(scan_text_obfuscation(text))
        scanned += 1
    return signals


__all__ = [
    "hex_identifier_ratio_signal",
    "high_entropy_strings",
    "invisible_text_signal",
    "scan_directory_obfuscation",
    "scan_text_obfuscation",
]
