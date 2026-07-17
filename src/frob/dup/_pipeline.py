"""The smart-dup pipeline: fingerprint -> candidates -> verify -> report.

Implements docs/dup.md's `find_clones`. R1 (exact token hash) and R2
(alpha-renamed token hash) are pure Python and always available -- they
operate directly on `frob.lang`'s `RawSymbol.body_tokens`. R3 (canonicalized
subtree hash, via the `frob_core` kernel) and R4 (winnowed fingerprints +
tree-edit verification) need the native extension. Per docs/dup.md's
no-silent-fallback rule there is no pure-Python reimplementation of R3+ to
fall back on: `find_clones` treats the whole ladder as one call and returns
`Err(DupError.CoreUnavailable)` up front when `frob_core` is not importable,
rather than silently downgrading to an R1/R2-only scan. R4's candidate
discovery + tree-edit verification and R5/R6 are recorded scope but not
wired into `find_clones` in this pass -- see the Deviations note below.

**Deviations from docs/dup.md** (recorded, not silently dropped):
- R2's alpha-renaming abstracts every identifier-shaped token uniformly
  (no scope/locals distinction), because `frob.lang.RawSymbol.body_tokens`
  is a flat leaf-token tuple with no node-type metadata attached -- unlike
  the legacy `frob.dup._legacy` scanner, which walked tree-sitter nodes
  directly. Good enough to catch pure rename clones; a future
  `frob.lang` token-kind channel would make it exact.
- R5 (Weisfeiler-Lehman graph-kernel hashing) and R6 (observational
  equivalence probing) are not implemented in this pass -- `frob:todo
  T-0001` marks both as follow-up work. `probe_equivalence` exists as a
  stub that always returns `Err(DupError.NotPure)` until R6 lands, which
  is honest (R6 "refuses symbols not provably effect-free" per the doc,
  and purity analysis does not exist yet either).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.dup import _core
from frob.dup._models import (
    ClonePair,
    CloneRegion,
    CloneReport,
    DupConfig,
    DupError,
    DupStats,
    ProbeVerdict,
)
from frob.gitio import Diff
from frob.graph._models import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_KEYWORDS = frozenset(
    {
        "def", "class", "return", "if", "elif", "else", "for", "while", "in",
        "not", "and", "or", "is", "import", "from", "as", "with", "try",
        "except", "finally", "raise", "pass", "break", "continue", "lambda",
        "yield", "async", "await", "None", "True", "False", "self", "cls",
        "global", "nonlocal", "assert", "del",
    }
)


def _r1_hash(tokens: tuple[str, ...]) -> str:
    """R1: exact token hash (copy-paste clones)."""
    return "r1:" + str(hash(tokens))


def _r2_normalize(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Alpha-rename every identifier-shaped token to a positional placeholder."""
    mapping: dict[str, str] = {}
    normalized: list[str] = []
    for tok in tokens:
        if _IDENT_RE.match(tok) and tok not in _KEYWORDS:
            if tok not in mapping:
                mapping[tok] = f"_v{len(mapping)}"
            normalized.append(mapping[tok])
        else:
            normalized.append(tok)
    return tuple(normalized)


def _r2_hash(tokens: tuple[str, ...]) -> str:
    """R2: alpha-renamed token hash -- every identifier-shaped token abstracted."""
    return "r2:" + str(hash(_r2_normalize(tokens)))


def touched_refs(snapshot: GraphSnapshot, diff: Diff) -> frozenset[str]:
    """Symrefs in `snapshot` whose span overlaps a `diff` hunk (the "new side")."""
    touched: set[str] = set()
    hunks_by_file: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for hunk in diff.hunks:
        hunks_by_file[hunk.file].append(hunk.span)
    for symref, record in snapshot.symbols.items():
        spans = hunks_by_file.get(record.id.path)
        if not spans:
            continue
        lo, hi = record.span
        for h_lo, h_hi in spans:
            if lo <= h_hi and h_lo <= hi:
                touched.add(symref)
                break
    return frozenset(touched)


def _parsed_symbols_by_path(root: Path, path: str) -> dict[str, tuple[str, ...]]:
    """qualname -> body_tokens for every symbol `frob.lang` extracts from `path`."""
    from frob.lang import parse_file

    result = parse_file(root / path)
    if result.is_err:
        _log.debug("find_clones: %s failed to parse (%s)", path, result.err)
        return {}
    return {s.qualname: s.body_tokens for s in result.danger_ok.symbols}


def find_clones(
    snapshot: GraphSnapshot, cfg: DupConfig, diff: Diff | None = None
) -> Result[CloneReport, DupError]:
    """Run the rung ladder over `snapshot`; `diff` restricts the new side (DUP001)."""
    if not _core.core_available():
        _log.warning(
            "find_clones: frob_core unavailable, refusing R3+ scan. %s",
            _core.INSTALL_HINT,
        )
        return Err(DupError.CoreUnavailable)

    touched = touched_refs(snapshot, diff) if diff is not None else None

    root = Path(snapshot.root)
    r1_buckets: dict[str, list[str]] = defaultdict(list)
    r2_buckets: dict[str, list[str]] = defaultdict(list)
    r3_buckets: dict[str, list[str]] = defaultdict(list)
    fingerprinted = 0
    tokens_by_path: dict[str, dict[str, tuple[str, ...]]] = {}
    for symref, record in snapshot.symbols.items():
        # Bucket every symbol (not just touched ones) so a touched symbol can
        # match against a pre-existing, untouched one.
        path = record.id.path
        if path not in tokens_by_path:
            tokens_by_path[path] = _parsed_symbols_by_path(root, path)
        body_tokens = tokens_by_path[path].get(record.id.qualname)
        if not body_tokens or len(body_tokens) < cfg.min_tokens:
            continue
        fingerprinted += 1
        r1_buckets[_r1_hash(body_tokens)].append(symref)
        r2_buckets[_r2_hash(body_tokens)].append(symref)

        # R3: canonicalized subtree hash, computed by the frob_core kernel
        # over the same alpha-renamed token stream (a simplification of
        # true R3 canonicalization -- see the module docstring's
        # Deviations note; literal abstraction/control-flow normalization
        # is not yet exposed by frob.lang).
        r3_result = _core.r3_canonical_hash(_r2_normalize(body_tokens))
        if r3_result.is_ok:
            r3_buckets["r3:" + r3_result.danger_ok].append(symref)

    groups: list[tuple[ClonePair, ...]] = []
    seen_pairs: set[frozenset[str]] = set()
    pairs_verified = 0

    for rung_name, buckets, similarity, rung_label in (
        ("r1", r1_buckets, 1.0, "r1"),
        ("r2", r2_buckets, 0.95, "r2"),
        ("r3", r3_buckets, 0.9, "r3"),
    ):
        for members in buckets.values():
            if len(members) < 2:
                continue
            group: list[ClonePair] = []
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    if touched is not None and a not in touched and b not in touched:
                        continue
                    key = frozenset((a, b))
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    pairs_verified += 1
                    group.append(
                        ClonePair(
                            left=CloneRegion(ref=a, span=snapshot.symbols[a].span),
                            right=CloneRegion(ref=b, span=snapshot.symbols[b].span),
                            similarity=similarity,
                            rung=rung_label,
                        )
                    )
            if group:
                groups.append(tuple(group))
        _log.debug("find_clones: rung=%s buckets=%d", rung_name, len(buckets))

    stats = DupStats(
        fingerprinted=fingerprinted,
        cache_hits=0,
        pairs_verified=pairs_verified,
    )
    _log.info(
        "find_clones: %d group(s), %d pair(s) verified, %d symbol(s) fingerprinted",
        len(groups),
        pairs_verified,
        fingerprinted,
    )
    return Ok(CloneReport(groups=tuple(groups), stats=stats))


def probe_equivalence(
    a: str, b: str, snapshot: GraphSnapshot, budget_s: float
) -> Result[ProbeVerdict, DupError]:
    """R6: observational-equivalence probing (not implemented, frob:todo T-0001).

    Always `Err(NotPure)`: no purity analysis exists yet to certify `a`/`b`
    as effect-free, so refusing is the honest answer per docs/dup.md ("R6
    refuses symbols not provably effect-free").
    """
    _log.debug("probe_equivalence: %s vs %s -- R6 not implemented, refusing", a, b)
    return Err(DupError.NotPure)


__all__ = ["find_clones", "probe_equivalence", "touched_refs"]
