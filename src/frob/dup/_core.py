"""Thin Result-returning shim over the `frob_core` native extension.

Matches the lithos `CoreFailure` pattern named in docs/modules/dup.md: PyO3 calls
never cross the boundary as exceptions the rest of `frob.dup` has to know
about -- `core_available()` gates every call site, and a missing extension
becomes `Err(DupError.CoreUnavailable)`, never a silent downgrade.
"""

from __future__ import annotations

from functools import lru_cache

from typani import Err, Ok
from typani.result import Result

from frob.dup._models import DupError
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/dup.md#rust-core
INSTALL_HINT = (
    "install with: uv pip install ./frob-core  (or: maturin develop, from frob-core/)"
)


# frob:doc docs/modules/dup.md#rust-core
# frob:waive TEST005 reason="core_available 66.7% branch cover, debt T-0160"
@lru_cache(maxsize=1)
def core_available() -> bool:
    """Whether the compiled `frob_core` extension is importable, cached once."""
    try:
        import frob_core  # noqa: F401
    except ImportError:
        _log.warning(
            "frob_core not importable; R3+ dup rungs disabled. %s", INSTALL_HINT
        )
        return False
    return True


# frob:doc docs/modules/dup.md#rust-core
def r3_canonical_hash(tokens: tuple[str, ...]) -> Result[str, DupError]:
    """R3: canonicalized-AST subtree hash of a normalized token sequence."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(frob_core.r3_canonical_hash(list(tokens)))


# frob:doc docs/modules/dup.md#rust-core
def winnow_fingerprints(
    tokens: tuple[str, ...], k: int, w: int
) -> Result[tuple[int, ...], DupError]:
    """R4: winnowed fingerprint set over `tokens` with k-gram/window sizes."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(tuple(frob_core.winnow_fingerprints(list(tokens), k, w)))


# frob:doc docs/modules/dup.md#rust-core
def candidate_pairs(
    fingerprint_sets: tuple[tuple[int, ...], ...], min_shared: int
) -> Result[tuple[tuple[int, int], ...], DupError]:
    """R4 candidate discovery: index pairs sharing >= `min_shared` fingerprints."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    sets = [list(fps) for fps in fingerprint_sets]
    return Ok(tuple(tuple(p) for p in frob_core.candidate_pairs(sets, min_shared)))


# frob:doc docs/modules/dup.md#rust-core
def tree_edit_similarity(
    a: tuple[int, ...], b: tuple[int, ...]
) -> Result[tuple[float, tuple[tuple[int, int], ...]], DupError]:
    """R4 verification: statement-sequence similarity and matched-index alignment."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    sim, alignment = frob_core.tree_edit_similarity(list(a), list(b))
    return Ok((sim, tuple(tuple(p) for p in alignment)))


# frob:doc docs/modules/dup.md#rung-r4
def apted_similarity(
    labels_a: tuple[str, ...],
    parents_a: tuple[int, ...],
    labels_b: tuple[str, ...],
    parents_b: tuple[int, ...],
) -> Result[float, DupError]:
    """R4 verification (real): Zhang-Shasha tree-edit-distance similarity.

    `labels_*`/`parents_*` come from `frob.lang.flatten_tree` over a
    `frob.lang.symbol_tree` export -- real subtree structure, not the flat
    statement-hash sequence `tree_edit_similarity` compares.
    """
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(
        frob_core.apted_similarity(
            list(labels_a), list(parents_a), list(labels_b), list(parents_b)
        )
    )


# frob:doc docs/modules/dup.md#rung-r1-5
def exact_regions(
    documents: tuple[tuple[str, ...], ...], min_len: int
) -> Result[tuple[tuple[int, int, int, int, int], ...], DupError]:
    """R1.5: exact repeated-region discovery via a generalized suffix array
    over `documents`' concatenated (already-normalized) token streams.

    Each returned `(doc_a, start_a, doc_b, start_b, length)` names two
    token-offset windows -- one per document index into `documents` --
    that match exactly for `length` tokens. Unlike R1/R2 (whole-body
    hashing), this finds copy-pasted sub-regions inside otherwise-different
    documents; see docs/modules/dup.md's rung table.
    """
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    docs = [list(d) for d in documents]
    return Ok(tuple(tuple(r) for r in frob_core.exact_regions(docs, min_len)))


# frob:doc docs/modules/dup.md#rung-r5
def wl_hash(
    adjacency: tuple[tuple[int, int], ...], labels: tuple[str, ...], iterations: int
) -> Result[int, DupError]:
    """R5: Weisfeiler-Lehman graph-kernel hash of a def-use/control adjacency."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(frob_core.wl_hash(list(adjacency), list(labels), iterations))


__all__ = [
    "INSTALL_HINT",
    "apted_similarity",
    "candidate_pairs",
    "core_available",
    "exact_regions",
    "r3_canonical_hash",
    "tree_edit_similarity",
    "wl_hash",
    "winnow_fingerprints",
]
