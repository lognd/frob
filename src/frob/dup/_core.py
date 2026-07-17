"""Thin Result-returning shim over the `frob_core` native extension.

Matches the lithos `CoreFailure` pattern named in docs/dup.md: PyO3 calls
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

INSTALL_HINT = (
    "install with: uv pip install ./frob-core  (or: maturin develop, from frob-core/)"
)


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


def r3_canonical_hash(tokens: tuple[str, ...]) -> Result[str, DupError]:
    """R3: canonicalized-AST subtree hash of a normalized token sequence."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(frob_core.r3_canonical_hash(list(tokens)))


def winnow_fingerprints(
    tokens: tuple[str, ...], k: int, w: int
) -> Result[tuple[int, ...], DupError]:
    """R4: winnowed fingerprint set over `tokens` with k-gram/window sizes."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(tuple(frob_core.winnow_fingerprints(list(tokens), k, w)))


def candidate_pairs(
    fingerprint_sets: tuple[tuple[int, ...], ...], min_shared: int
) -> Result[tuple[tuple[int, int], ...], DupError]:
    """R4 candidate discovery: index pairs sharing >= `min_shared` fingerprints."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    sets = [list(fps) for fps in fingerprint_sets]
    return Ok(tuple(tuple(p) for p in frob_core.candidate_pairs(sets, min_shared)))


def tree_edit_similarity(
    a: tuple[int, ...], b: tuple[int, ...]
) -> Result[tuple[float, tuple[tuple[int, int], ...]], DupError]:
    """R4 verification: statement-sequence similarity and matched-index alignment."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    sim, alignment = frob_core.tree_edit_similarity(list(a), list(b))
    return Ok((sim, tuple(tuple(p) for p in alignment)))


__all__ = [
    "INSTALL_HINT",
    "candidate_pairs",
    "core_available",
    "r3_canonical_hash",
    "tree_edit_similarity",
    "winnow_fingerprints",
]
