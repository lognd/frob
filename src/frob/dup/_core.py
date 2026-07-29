"""Thin Result-returning shim over the `frob_core` native extension.

Matches the lithos `CoreFailure` pattern named in docs/modules/dup.md: PyO3 calls
never cross the boundary as exceptions the rest of `frob.dup` has to know
about -- `core_available()` gates every call site, and a missing extension
becomes `Err(DupError.CoreUnavailable)`, never a silent downgrade.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: src/frob/dup/_core.py's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from functools import lru_cache

from typani import Err, Ok
from typani.result import Result

from frob.dup._models import AntiUnifyTemplate, DupError
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/dup.md#rust-core
INSTALL_HINT = (
    "install with: uv pip install ./frob-core  (or: maturin develop, from frob-core/)"
)


# frob:doc docs/modules/dup.md#rust-core
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
# frob:waive COV007 reason="docs/modules/dup.md's Rust-core section individually \
# frob:describes each private frob_core shim by name (T-0524) -- a deliberate \
# per-function architecture doc, not accidental doc-anchor drift onto a private helper"
def _r3_canonical_hash(tokens: tuple[str, ...]) -> Result[str, DupError]:
    """R3: canonicalized-AST subtree hash of a normalized token sequence."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(frob_core.r3_canonical_hash(list(tokens)))


# frob:doc docs/modules/dup.md#rust-core
# frob:waive COV007 reason="docs/modules/dup.md's Rust-core section individually \
# frob:describes each private frob_core shim by name (T-0524) -- a deliberate \
# per-function architecture doc, not accidental doc-anchor drift onto a private helper"
def _winnow_fingerprints(
    tokens: tuple[str, ...], k: int, w: int
) -> Result[tuple[int, ...], DupError]:
    """R4: winnowed fingerprint set over `tokens` with k-gram/window sizes."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(tuple(frob_core.winnow_fingerprints(list(tokens), k, w)))


# frob:doc docs/modules/dup.md#rust-core
# frob:waive COV007 reason="docs/modules/dup.md's Rust-core section individually \
# frob:describes each private frob_core shim by name (T-0524) -- a deliberate \
# per-function architecture doc, not accidental doc-anchor drift onto a private helper"
def _candidate_pairs(
    fingerprint_sets: tuple[tuple[int, ...], ...], min_shared: int
) -> Result[tuple[tuple[int, int], ...], DupError]:
    """R4 candidate discovery: index pairs sharing >= `min_shared` fingerprints."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    sets = [list(fps) for fps in fingerprint_sets]
    return Ok(tuple(tuple(p) for p in frob_core.candidate_pairs(sets, min_shared)))


# frob:doc docs/modules/dup.md#rust-core
# frob:waive COV007 reason="docs/modules/dup.md's Rust-core section individually \
# frob:describes each private frob_core shim by name (T-0524) -- a deliberate \
# per-function architecture doc, not accidental doc-anchor drift onto a private helper"
def _tree_edit_similarity(
    a: tuple[int, ...], b: tuple[int, ...]
) -> Result[tuple[float, tuple[tuple[int, int], ...]], DupError]:
    """R4 verification: statement-sequence similarity and matched-index alignment."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    sim, alignment = frob_core.tree_edit_similarity(list(a), list(b))
    return Ok((sim, tuple(tuple(p) for p in alignment)))


# frob:doc docs/modules/dup.md#rung-r4
# frob:waive COV007 reason="docs/modules/dup.md's rung-r4 anchor individually \
# frob:describes this private frob_core shim by name (T-0524) -- a deliberate \
# per-function architecture doc, not accidental doc-anchor drift onto a private helper"
def _apted_similarity(
    labels_a: tuple[str, ...],
    parents_a: tuple[int, ...],
    labels_b: tuple[str, ...],
    parents_b: tuple[int, ...],
) -> Result[float, DupError]:
    """R4 verification (real): Zhang-Shasha tree-edit-distance similarity.

    `labels_*`/`parents_*` come from `frob.lang.flatten_tree` over a
    `frob.lang.symbol_tree` export -- real subtree structure, not the flat
    statement-hash sequence `_tree_edit_similarity` compares.
    """
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(
        frob_core.apted_similarity(
            list(labels_a), list(parents_a), list(labels_b), list(parents_b)
        )
    )


# frob:doc docs/modules/dup.md#anti-unification-plotkin-lgg
def anti_unify(
    labels_a: tuple[str, ...],
    parents_a: tuple[int, ...],
    labels_b: tuple[str, ...],
    parents_b: tuple[int, ...],
) -> Result[AntiUnifyTemplate, DupError]:
    """Plotkin lgg: lockstep anti-unification template + per-side hole bindings.

    `labels_*`/`parents_*` are the same `(labels, parents)` node-array pair
    `_apted_similarity` consumes. A hole-ceiling failure (template >50%
    `$hole_N` placeholders -- too little shared structure to be a
    meaningful generalization) comes back as
    `Err(DupError.HoleCeilingExceeded)`; the caller falls back to treating
    the pair as a plain (non-generalized) clone pair, per
    docs/modules/dup-sota-survey.md section 4.
    """
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    ok, tpl_labels, tpl_parents, bindings_a, bindings_b = frob_core.anti_unify(
        list(labels_a), list(parents_a), list(labels_b), list(parents_b)
    )
    if not ok:
        return Err(DupError.HoleCeilingExceeded)
    return Ok(
        AntiUnifyTemplate(
            labels=tuple(tpl_labels),
            parents=tuple(tpl_parents),
            bindings_a=tuple(tuple(p) for p in bindings_a),
            bindings_b=tuple(tuple(p) for p in bindings_b),
        )
    )


# frob:doc docs/modules/dup.md#rung-r1-5
# frob:waive COV007 reason="docs/modules/dup.md's R1.5 section documents this private \
# frob_core shim's algorithm directly (T-0524) -- a deliberate architecture doc, not \
# accidental doc-anchor drift onto a private helper"
# frob:waive DEAD001 reason="confirmed exercised: called from \
# frob.dup._pipeline._fingerprint's R6 region path (_core._exact_regions(...)) -- a \
# real cross-package private call the best-effort callgraph resolves same-directory \
# privates only, does not trace across the T-1086 dup/_pipeline package split"
def _exact_regions(
    documents: tuple[tuple[str, ...], ...], min_len: int, max_run_size: int = 200
) -> Result[tuple[tuple[tuple[int, int, int, int, int], ...], bool], DupError]:
    """R1.5: exact repeated-region discovery via a generalized suffix array
    over `documents`' concatenated (already-normalized) token streams.

    Each returned `(doc_a, start_a, doc_b, start_b, length)` names two
    token-offset windows -- one per document index into `documents` --
    that match exactly for `length` tokens. Unlike R1/R2 (whole-body
    hashing), this finds copy-pasted sub-regions inside otherwise-different
    documents; see docs/modules/dup.md's rung table.

    `max_run_size` (T-0273) bounds the O(k^2) pair emission for one
    equal-token run of size `k` -- a run larger than `max_run_size` only
    pairs its first `max_run_size` occurrences, and the returned `bool` is
    `True` iff at least one run was capped this way. This is an honest
    truncation signal, not a silent drop (the T-0193-recall-bug lesson):
    callers must surface it rather than treat the region list as
    exhaustive when it is `True`.
    """
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    docs = [list(d) for d in documents]
    regions, truncated = frob_core.exact_regions(docs, min_len, max_run_size)
    return Ok((tuple(tuple(r) for r in regions), truncated))


# frob:doc docs/modules/dup.md#rung-r5
# frob:waive COV007 reason="docs/modules/dup.md's rung-r5 anchor individually \
# frob:describes this private frob_core shim by name (T-0524) -- a deliberate \
# per-function architecture doc, not accidental doc-anchor drift onto a private helper"
def _wl_hash(
    adjacency: tuple[tuple[int, int], ...], labels: tuple[str, ...], iterations: int
) -> Result[int, DupError]:
    """R5: Weisfeiler-Lehman graph-kernel hash of a def-use/control adjacency."""
    if not core_available():
        return Err(DupError.CoreUnavailable)
    import frob_core

    return Ok(frob_core.wl_hash(list(adjacency), list(labels), iterations))


__all__ = [
    "INSTALL_HINT",
    "anti_unify",
    "_apted_similarity",
    "_candidate_pairs",
    "core_available",
    "_exact_regions",
    "_r3_canonical_hash",
    "_tree_edit_similarity",
    "_wl_hash",
    "_winnow_fingerprints",
]
