"""R3-R5 fingerprinting, candidate pairing/verification, and clone-group
assembly (split from `dup/_pipeline.py`, T-1086).

The `_FpState`-threaded fingerprint passes (R3 canonical hash, R4 winnowed
fingerprints + prefilters + statement-alignment/APTED verification, R5
Weisfeiler-Lehman dataflow hashing), the R1.5 exact-region pass, and the
public `find_clones`/`find_helper_clones` entry points that assemble a
`CloneReport` from every rung's groups -- see docs/modules/dup.md#pipeline.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

from typani import Err, Ok
from typani.result import Result

from frob.dup._cache import get_fingerprint, get_verdict, put_fingerprint, put_verdict
from frob.dup._core import (
    INSTALL_HINT,
    _candidate_pairs,
    _exact_regions,
    _r3_canonical_hash,
    _tree_edit_similarity,
    _wl_hash,
    _winnow_fingerprints,
    core_available,
)
from frob.dup._models import (
    CloneMatchGroup,
    ClonePair,
    CloneRegion,
    CloneReport,
    DupConfig,
    DupError,
    DupStats,
)
from frob.dup._pipeline._callgraph import (
    _apted_similarity_for_pair,
    _build_dataflow_graph,
    _core_symbol_tree,
    _inline_private_calls,
    _parsed_symbols_by_path,
    _real_dataflow_graph,
    touched_refs,
)
from frob.dup._pipeline._normalize import (
    _digest,
    _line_for_statement_index,
    _normalize_error_channel,
    _normalize_guard_shape,
    _r1_hash,
    _r2_hash,
    _r2_normalize,
    _region_span_for_alignment,
    _split_statements,
    _statement_hashes,
)
from frob.dup._pipeline._shared import (
    _BRANCH_KEYWORDS,
    _CORPUS_EPOCH,
    _R4_APTED_VERDICT_METHOD,
    _R4_FP_RUNG,
    _R4_K,
    _R4_MIN_SHARED,
    _R4_SIMILARITY_FLOOR,
    _R4_VERDICT_METHOD,
    _R4_W,
    _R5_FP_RUNG,
    _R5_ITERATIONS,
    _R5_SIMILARITY,
    _FpState,
    _log,
)
from frob.dup._template import build_group_template
from frob.gitio import Diff
from frob.graph._models import GraphSnapshot, SymbolKind


def _r3_fingerprint(
    state: _FpState, digest: str, normalized: tuple[str, ...]
) -> str | None:
    """R3 canonical hash for a normalized token stream, cache-backed. `None`
    when the frob_core kernel errors (caller skips the symbol's R4/R5)."""
    cached = get_fingerprint(state.root, digest, "r3")
    if cached is not None:
        state.cache_hits += 1
        return str(cached[0])
    result = _r3_canonical_hash(normalized)
    if result.is_err:
        return None
    put_fingerprint(state.root, digest, "r3", (result.danger_ok,))
    return result.danger_ok


def _r4_fingerprint(
    state: _FpState, symref: str, digest: str, normalized: tuple[str, ...]
) -> None:
    """Compute/cache the R4 winnowed fingerprint set for `symref`."""
    cached = get_fingerprint(state.root, digest, _R4_FP_RUNG)
    if cached is not None:
        state.cache_hits += 1
        state.fp_by_ref[symref] = cast("tuple[int, ...]", tuple(cached))
        return
    result = _winnow_fingerprints(normalized, _R4_K, _R4_W)
    if result.is_ok:
        state.fp_by_ref[symref] = result.danger_ok
        put_fingerprint(state.root, digest, _R4_FP_RUNG, result.danger_ok)


def _dataflow_graph(
    root: Path, record: Any, body_tokens: tuple[str, ...]
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]]:
    """The R5 def-use/control graph for a symbol: the real statement-node
    graph when a subtree is available, else the token co-occurrence proxy."""
    body_tree = _core_symbol_tree(root, record)
    real = _real_dataflow_graph(body_tree) if body_tree is not None else None
    if real is not None:
        return real
    return _build_dataflow_graph(_split_statements(body_tokens))


def _r5_fingerprint(
    state: _FpState, digest: str, record: Any, body_tokens: tuple[str, ...]
) -> int | None:
    """R5 Weisfeiler-Lehman graph hash for a symbol, cache-backed. `None`
    when the frob_core kernel errors."""
    cached = get_fingerprint(state.root, digest, _R5_FP_RUNG)
    if cached is not None:
        state.cache_hits += 1
        return cast(int, cached[0])
    adjacency, labels = _dataflow_graph(state.root, record, body_tokens)
    result = _wl_hash(adjacency, labels, _R5_ITERATIONS)
    if result.is_err:
        return None
    put_fingerprint(state.root, digest, _R5_FP_RUNG, (result.danger_ok,))
    return result.danger_ok


def _body_tokens_for_symbol(state: _FpState, record: Any) -> tuple[str, ...] | None:
    """`record`'s body tokens (private-helper-inlined, T-0288), parsing/caching
    its file if not already loaded. `None` when the body is missing or the
    INLINED token count is under `cfg.min_tokens` -- inlining runs before the
    threshold check so a symbol whose logic was split into private helpers
    is measured by its real logic size, not the arch-forced call-site size.
    """
    path = record.id.path
    if path not in state.tokens_by_path:
        state.tokens_by_path[path] = _parsed_symbols_by_path(state.root, path)
    raw_tokens = state.tokens_by_path[path].get(record.id.qualname)
    if not raw_tokens:
        return None
    symref = f"{path}::{record.id.qualname}"
    body_tokens = _inline_private_calls(state, symref, raw_tokens)
    if len(body_tokens) < state.cfg.min_tokens:
        return None
    return body_tokens


def _fingerprint_symbol(state: _FpState, symref: str, record: Any) -> None:
    """Fingerprint one snapshot symbol into every rung bucket on `state`.

    Bucketing every symbol (not just touched ones) lets a touched symbol
    match a pre-existing, untouched one. Bodies below `cfg.min_tokens` are
    skipped. An R3 kernel error skips the symbol's remaining rungs.
    """
    body_tokens = _body_tokens_for_symbol(state, record)
    if body_tokens is None:
        return
    state.fingerprinted += 1
    state.body_tokens_by_ref[symref] = body_tokens
    digest = _digest(body_tokens)
    state.digest_by_ref[symref] = digest
    normalized = _r2_normalize(body_tokens)

    state.size_by_ref[symref] = len(body_tokens)
    state.metric_by_ref[symref] = sum(
        1 for tok in body_tokens if tok in _BRANCH_KEYWORDS
    )
    state.vector_by_ref[symref] = _characteristic_vector(normalized)

    state.r1_buckets[_r1_hash(body_tokens)].append(symref)
    state.r2_buckets[_r2_hash(body_tokens)].append(symref)

    # frob:ticket T-0974
    # R3-R5 are native-call-per-symbol and dominate cold-cache cost at
    # whole-snapshot scale (see DupConfig.native_rungs_enabled's docstring
    # for the measured budget-blowout this guards). R1/R2 above stay
    # unconditional -- cheap, pure-Python, and the reason `[dup].enforce`
    # can default on at all.
    if not state.cfg.native_rungs_enabled:
        return

    r3_hash = _r3_fingerprint(state, digest, normalized)
    if r3_hash is None:
        return
    state.r3_buckets["r3:" + r3_hash].append(symref)

    _r4_fingerprint(state, symref, digest, normalized)

    wl = _r5_fingerprint(state, digest, record, body_tokens)
    if wl is None:
        return
    state.r5_buckets[wl].append(symref)


def _pair(
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    similarity: float,
    rung: str,
    alignment: tuple[tuple[int, int], ...] = (),
) -> ClonePair:
    """A `ClonePair` for refs `a`/`b` using each side's whole symbol span."""
    return ClonePair(
        left=CloneRegion(ref=a, span=snapshot.symbols[a].span),
        right=CloneRegion(ref=b, span=snapshot.symbols[b].span),
        similarity=similarity,
        rung=rung,
        alignment=alignment,
    )


def _bucket_pairs(
    members: list[str],
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> Iterator[tuple[str, str]]:
    """Unordered new ref pairs in one bucket: skipping untouched-only pairs
    (when `touched` is set) and any pair already reported by an earlier rung."""
    if len(members) < 2:
        return
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            a, b = members[i], members[j]
            if touched is not None and a not in touched and b not in touched:
                continue
            if frozenset((a, b)) in seen_pairs:
                continue
            yield a, b


def _hash_rung_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> list[tuple[ClonePair, ...]]:
    """R1/R2/R3 exact-hash-collision clone groups."""
    groups: list[tuple[ClonePair, ...]] = []
    for name, buckets, similarity, rung in (
        ("r1", state.r1_buckets, 1.0, "r1"),
        ("r2", state.r2_buckets, 0.95, "r2"),
        ("r3", state.r3_buckets, 0.9, "r3"),
    ):
        for members in buckets.values():
            group = [
                _pair(a, b, snapshot, similarity, rung)
                for a, b in _consume_pairs(
                    _bucket_pairs(members, touched, seen_pairs), seen_pairs, state
                )
            ]
            if group:
                groups.append(tuple(group))
        _log.debug("find_clones: rung=%s buckets=%d", name, len(buckets))
    return groups


def _consume_pairs(
    pairs: Iterator[tuple[str, str]],
    seen_pairs: set[frozenset[str]],
    state: _FpState,
) -> Iterator[tuple[str, str]]:
    """Mark each yielded pair seen and count it verified as it is consumed."""
    for a, b in pairs:
        seen_pairs.add(frozenset((a, b)))
        state.pairs_verified += 1
        yield a, b


def _r4_alignment(
    state: _FpState, a: str, b: str, d1: str, d2: str
) -> tuple[float, tuple[tuple[int, int], ...]] | None:
    """The statement-Levenshtein similarity + alignment for an R4 candidate
    pair, cache-backed. `None` when the frob_core kernel errors."""
    cached = get_verdict(state.root, d1, d2, _R4_VERDICT_METHOD, _CORPUS_EPOCH)
    if cached is not None:
        state.cache_hits += 1
        raw = cast("list[list[int]]", cached[1])
        return cast(float, cached[0]), tuple((p[0], p[1]) for p in raw)
    # T-0785: channel-normalize (but do NOT alpha-rename -- real identifier
    # text still has to line up exactly for this near-miss floor's raw
    # per-statement hash match) before splitting into statements, so an
    # `Err(...)`/`None`/`raise` exit shape difference alone does not sink a
    # pair's near-miss floor the way the motivating git-common-dir pair did
    # (audit M3). `state.body_tokens_by_ref` itself stays untouched (R1's
    # exact-hash and the cache-key digest both intentionally still see the
    # literal, un-normalized text).
    # T-0801/T-0800: also fold in the combined-vs-split guard axis
    # (`_normalize_guard_shape`) here, not just in `_r2_normalize` -- this
    # near-miss floor is the actual gate the real git-common-dir pair was
    # sinking under (0.444, below `_R4_SIMILARITY_FLOOR`) even after
    # T-0785's error-channel axis alone; identifiers still stay literal,
    # same posture as the error-channel normalization above.
    a_hashes = _statement_hashes(
        _split_statements(
            _normalize_guard_shape(
                _normalize_error_channel(state.body_tokens_by_ref[a])
            )
        )
    )
    b_hashes = _statement_hashes(
        _split_statements(
            _normalize_guard_shape(
                _normalize_error_channel(state.body_tokens_by_ref[b])
            )
        )
    )
    result = _tree_edit_similarity(a_hashes, b_hashes)
    if result.is_err:
        return None
    sim, alignment_pairs = result.danger_ok
    put_verdict(
        state.root,
        d1,
        d2,
        _R4_VERDICT_METHOD,
        _CORPUS_EPOCH,
        (sim, alignment_pairs),
        state.cfg.cache_entries,
    )
    return sim, alignment_pairs


def _r4_spans(
    state: _FpState,
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    alignment_pairs: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], tuple[int, int]]:
    """The narrowed left/right region spans for an R4 match's alignment."""
    a_chunks = _split_statements(state.body_tokens_by_ref[a])
    b_chunks = _split_statements(state.body_tokens_by_ref[b])
    a_idx = tuple(p[0] for p in alignment_pairs)
    b_idx = tuple(p[1] for p in alignment_pairs)
    left = _region_span_for_alignment(snapshot.symbols[a].span, len(a_chunks), a_idx)
    right = _region_span_for_alignment(snapshot.symbols[b].span, len(b_chunks), b_idx)
    return left, right


def _r4_verify_pair(
    state: _FpState,
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    seen_pairs: set[frozenset[str]],
) -> ClonePair | None:
    """Verify one R4 candidate pair, counting it and reporting a `ClonePair`
    when it clears the near-miss floor (else `None`)."""
    d1, d2 = state.digest_by_ref[a], state.digest_by_ref[b]
    verdict = _r4_alignment(state, a, b, d1, d2)
    if verdict is None:
        return None
    sim, alignment_pairs = verdict
    state.pairs_verified += 1
    seen_pairs.add(frozenset((a, b)))
    if sim < _R4_SIMILARITY_FLOOR:
        return None
    left_span, right_span = _r4_spans(state, a, b, snapshot, alignment_pairs)
    reported_sim = _r4_reported_sim(state, a, b, snapshot, d1, d2, sim)
    return ClonePair(
        left=CloneRegion(ref=a, span=left_span),
        right=CloneRegion(ref=b, span=right_span),
        similarity=reported_sim,
        rung="r4",
        alignment=alignment_pairs,
    )


def _r4_reported_sim(
    state: _FpState,
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    d1: str,
    d2: str,
    fallback: float,
) -> float:
    """Reported R4 similarity: cached/real APTED, else `fallback`."""
    cached = get_verdict(
        state.root, d1, d2, _R4_APTED_VERDICT_METHOD, _CORPUS_EPOCH
    )
    if cached is not None:
        state.cache_hits += 1
        return cast(float, cached[0])
    apted_sim = _apted_similarity_for_pair(
        state.root, snapshot.symbols[a], snapshot.symbols[b]
    )
    if apted_sim is not None:
        put_verdict(
            state.root,
            d1,
            d2,
            _R4_APTED_VERDICT_METHOD,
            _CORPUS_EPOCH,
            (apted_sim, ()),
            state.cfg.cache_entries,
        )
        return apted_sim
    return fallback


def _r4_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> list[tuple[ClonePair, ...]]:
    """R4 near-miss clone groups: winnow-fingerprint candidates verified by
    statement alignment, then refined by real tree-edit distance."""
    r4_refs = list(state.fp_by_ref)
    if len(r4_refs) < 2:
        return []
    sets = tuple(state.fp_by_ref[r] for r in r4_refs)
    candidates_result = _candidate_pairs(sets, _R4_MIN_SHARED)
    if candidates_result.is_err:
        _log.debug("find_clones: r4 candidate discovery unavailable")
        return []
    r4_group: list[ClonePair] = []
    for i, j in candidates_result.danger_ok:
        pair = _r4_candidate_pair(state, r4_refs, i, j, snapshot, touched, seen_pairs)
        if pair is not None:
            r4_group.append(pair)
    return [tuple(r4_group)] if r4_group else []


def _characteristic_vector(normalized: tuple[str, ...]) -> dict[str, int]:
    """DECKARD-style characteristic vector (docs/modules/dup-sota-survey.md
    item 4, T-0197): a histogram over shape CATEGORIES of the R2-normalized
    token stream, one bucket per distinct keyword/punctuation token plus a
    single collapsed `"IDENT"` bucket for every alpha-renamed placeholder.

    Real DECKARD builds this histogram over per-subtree AST *node-type*
    labels; `frob.lang.RawSymbol.body_tokens` is a flat leaf-token tuple
    with no per-token node-type metadata, so this uses the R2-normalized
    LEXICAL shape as the cheap stand-in -- documented deviation, same
    posture as the module docstring's other "no `frob.lang` per-token
    metadata yet" notes. Collapsing all placeholders to one bucket keeps
    the vector identifier-count-position-independent (two trees renamed
    with a different NUMBER of distinct identifiers should still look
    similar), matching DECKARD's rename-invariance property.
    """
    histogram: dict[str, int] = defaultdict(int)
    for tok in normalized:
        bucket = "IDENT" if tok.startswith("_v") and tok[2:].isdigit() else tok
        histogram[bucket] += 1
    return dict(histogram)


def _cosine_similarity(vec_a: dict[str, int], vec_b: dict[str, int]) -> float:
    """Cosine similarity of two sparse count-histograms; `1.0` if both are empty."""
    if not vec_a and not vec_b:
        return 1.0
    if not vec_a or not vec_b:
        return 0.0
    keys = vec_a.keys() & vec_b.keys()
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    norm_a = sum(v * v for v in vec_a.values()) ** 0.5
    norm_b = sum(v * v for v in vec_b.values()) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _nicad_size_ratio_ok(state: _FpState, a: str, b: str) -> bool:
    """NiCad-style size-ratio pre-filter (docs/modules/dup-sota-survey.md
    item 2's one adoptable idea, T-0197): reject a candidate pair whose
    token-count ratio is wilder than `cfg.prefilter_size_ratio` -- two
    bodies of grossly different size are not a plausible Type-1/2/3 clone
    pair. `min/max` so the ratio is always in `(0, 1]`; missing sizes (a
    symbol not seen by `_fingerprint_symbol`, should not happen for an R4
    candidate) pass through rather than reject."""
    size_a, size_b = state.size_by_ref.get(a), state.size_by_ref.get(b)
    if not size_a or not size_b:
        return True
    ratio = min(size_a, size_b) / max(size_a, size_b)
    return ratio >= state.cfg.prefilter_size_ratio


def _oreo_metric_ratio_ok(state: _FpState, a: str, b: str) -> bool:
    """Oreo-style metric-ratio pre-filter (docs/modules/dup-sota-survey.md
    item 6, non-ML half, T-0197): reject a candidate pair whose branch-
    keyword count (a cheap McCabe-complexity proxy, `_BRANCH_KEYWORDS`)
    ratio is wilder than `cfg.prefilter_metric_ratio`. Add-one smoothed so
    two straight-line (zero-branch) bodies never spuriously divide-by-zero
    or get rejected outright -- only a real, large complexity gap prunes."""
    metric_a = state.metric_by_ref.get(a, 0) + 1
    metric_b = state.metric_by_ref.get(b, 0) + 1
    ratio = min(metric_a, metric_b) / max(metric_a, metric_b)
    return ratio >= state.cfg.prefilter_metric_ratio


def _deckard_vector_ok(state: _FpState, a: str, b: str) -> bool:
    """DECKARD characteristic-vector pre-filter (T-0197): reject a candidate
    pair whose `_characteristic_vector` cosine similarity is below
    `cfg.prefilter_vector_similarity` -- structurally dissimilar token-shape
    profiles are not a plausible clone pair. Missing vectors pass through
    rather than reject."""
    vec_a, vec_b = state.vector_by_ref.get(a), state.vector_by_ref.get(b)
    if vec_a is None or vec_b is None:
        return True
    return _cosine_similarity(vec_a, vec_b) >= state.cfg.prefilter_vector_similarity


def _passes_r4_prefilters(state: _FpState, a: str, b: str) -> bool:
    """All three R4 candidate pre-filters (T-0197), ANDed: NiCad size-ratio,
    Oreo metric-ratio, DECKARD characteristic-vector similarity. A pair must
    clear every filter to reach the expensive `_r4_verify_pair` alignment/
    APTED path -- these are PRUNE-ONLY (docs/modules/dup-sota-survey.md
    survey items 2/4/6): failing a filter skips verification, it never adds
    a clone report on its own. `cfg.prefilter_enabled=False` disables all
    three (the pre-T-0197 behavior, every candidate reaches verification)."""
    if not state.cfg.prefilter_enabled:
        return True
    return (
        _nicad_size_ratio_ok(state, a, b)
        and _oreo_metric_ratio_ok(state, a, b)
        and _deckard_vector_ok(state, a, b)
    )


def _r4_candidate_pair(
    state: _FpState,
    r4_refs: list[str],
    i: int,
    j: int,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> ClonePair | None:
    """One `_candidate_pairs` index pair, filtered and verified into a
    `ClonePair` (or `None`)."""
    if i == j:
        # T-0191: unlike _bucket_pairs' range(i+1, len(members)) (which
        # structurally cannot self-pair), frob_core._candidate_pairs can
        # hand back (i, i) when a symbol's own fingerprint set collides
        # with itself past _R4_MIN_SHARED -- observed for real on this
        # repo's dup cache module post-refactor. Skip rather than
        # report a symbol as its own clone.
        return None
    a, b = r4_refs[i], r4_refs[j]
    if a == b:
        return None
    if touched is not None and a not in touched and b not in touched:
        return None
    if frozenset((a, b)) in seen_pairs:
        return None
    if not _passes_r4_prefilters(state, a, b):
        state.pairs_prefiltered += 1
        return None
    return _r4_verify_pair(state, a, b, snapshot, seen_pairs)


def _region_line_span(
    span: tuple[int, int], start: int, length: int, total_tokens: int
) -> tuple[int, int]:
    """The approximate line subrange for a `[start, start+length)` token
    window inside a symbol spanning `span`, via the same proportional
    index/total interpolation `_line_for_statement_index` uses for
    statement indices -- there is no per-token line map (`body_tokens` is a
    flat leaf-token tuple), so this is a documented approximation, not an
    exact mapping."""
    lo = _line_for_statement_index(span, start, total_tokens)
    hi = _line_for_statement_index(
        span, min(start + length - 1, total_tokens - 1), total_tokens
    )
    return (min(lo, hi), max(lo, hi))


def _region_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
    cfg: DupConfig,
) -> list[tuple[ClonePair, ...]]:
    """R1.5: exact repeated-region clone groups via the frob_core generalized
    suffix-array kernel over every fingerprinted symbol's R2-normalized
    token stream.

    Off by default (`cfg.region_kernel_enabled`, docs/modules/dup.md's
    `[dup].region_kernel` knob), an opt-in on top of `[dup].enforce` itself.
    Unlike R1/R2 (whole-body hashing), finds a copy-pasted sub-region living
    inside two otherwise-different symbol bodies.
    """
    if not cfg.region_kernel_enabled:
        return []
    refs = list(state.body_tokens_by_ref)
    if len(refs) < 2:
        return []
    normalized_docs = tuple(_r2_normalize(state.body_tokens_by_ref[r]) for r in refs)
    result = _exact_regions(
        normalized_docs, cfg.region_min_tokens, cfg.region_run_cap
    )
    if result.is_err:
        _log.debug("find_clones: r1.5 exact-region kernel unavailable")
        return []
    hits, truncated = result.danger_ok
    if truncated:
        # T-0273: an equal-token run exceeded [dup].region_run_cap and its
        # pair emission was capped -- an honest signal, not a silent drop
        # (the T-0193-recall-bug lesson). Some region pairs inside that
        # oversized run were not reported.
        _log.warning(
            "find_clones: r1.5 exact-region kernel truncated pair emission "
            "for at least one equal-token run larger than "
            "[dup].region_run_cap=%d; some region pairs in that run were "
            "not reported",
            cfg.region_run_cap,
        )
    group: list[ClonePair] = [
        pair
        for pair in (
            _region_candidate_pair(
                state, snapshot, refs, normalized_docs, touched, seen_pairs, hit
            )
            for hit in hits
        )
        if pair is not None
    ]
    return [tuple(group)] if group else []


def _region_candidate_pair(
    state: _FpState,
    snapshot: GraphSnapshot,
    refs: list[str],
    normalized_docs: tuple[tuple[str, ...], ...],
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
    hit: tuple[int, int, int, int, int],
) -> ClonePair | None:
    """One `_exact_regions` hit `(da, oa, db, ob, length)`, filtered and
    turned into an r1.5 `ClonePair` (or `None`)."""
    da, oa, db, ob, length = hit
    a, b = refs[da], refs[db]
    if a == b:
        return None
    if touched is not None and a not in touched and b not in touched:
        return None
    if frozenset((a, b)) in seen_pairs:
        return None
    seen_pairs.add(frozenset((a, b)))
    state.pairs_verified += 1
    left_span = _region_line_span(
        snapshot.symbols[a].span, oa, length, len(normalized_docs[da])
    )
    right_span = _region_line_span(
        snapshot.symbols[b].span, ob, length, len(normalized_docs[db])
    )
    return ClonePair(
        left=CloneRegion(ref=a, span=left_span),
        right=CloneRegion(ref=b, span=right_span),
        similarity=1.0,
        rung="r1.5",
    )


def _r5_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> list[tuple[ClonePair, ...]]:
    """R5 clone groups: WL-hash bucket collisions not found by an earlier rung."""
    r5_group = [
        _pair(a, b, snapshot, _R5_SIMILARITY, "r5")
        for members in state.r5_buckets.values()
        for a, b in _consume_pairs(
            _bucket_pairs(members, touched, seen_pairs), seen_pairs, state
        )
    ]
    return [tuple(r5_group)] if r5_group else []


# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0918
# frob:ticket T-1224
# frob:ticket T-2232
# frob:waive AFFECT001 reason="T-2232: this diff only retargets this file's \
# frob.dup._cache/frob.dup._core imports at the leaf submodules (breaking an import \
# cycle through frob/dup/__init__.py's namespace, T-2211's discovery of it); \
# find_clones's own behavior, signature, and documented contract are unchanged, \
# nothing here for docs/modules/dup.md#public-api to reflect"
def find_clones(
    snapshot: GraphSnapshot, cfg: DupConfig, diff: Diff | None = None
) -> Result[CloneReport, DupError]:
    """Run the full R1-R5 rung ladder over `snapshot` (R6 is opt-in, separate).

    `diff` restricts the "new side" to touched symbols (the DUP001 gate
    path); `diff=None` scans the whole snapshot. Fingerprints and pairwise
    verdicts are read/written through `frob.dup._cache` (content-addressed
    by body digest), so re-runs over an unchanged body/pair skip recompute.

    T-0918 used to wrap this entire rung ladder in `frob.process._lock.
    derived_state_write_lock`, taking a real cross-process EXCLUSIVE
    `derived_state_lock` for the WHOLE computation whenever called
    standalone (no-op only when nested inside `frob check`'s SHARED
    hold). T-1224: that serialized every concurrent reader (e.g. another
    `frob check`'s SHARED hold) against a standalone rebuild for the
    entire clones-stage duration (observed ~240s under profiling), even
    though the only state this function actually MUTATES on disk is the
    `frob.dup._cache` fingerprint/verdict cache -- the rung computation
    itself is read-only against the snapshot and the cache. The lock is
    now taken individually, only around each `frob.dup._cache.
    put_fingerprint`/`put_verdict` call (see those functions), so a
    standalone rebuild only blocks concurrent readers for the brief
    duration of an actual cache write, not for the whole rung ladder.
    """
    if not core_available():
        _log.warning(
            "find_clones: frob_core unavailable, refusing R3+ scan. %s",
            INSTALL_HINT,
        )
        return Err(DupError.CoreUnavailable)

    root = Path(snapshot.root)
    touched = touched_refs(snapshot, diff) if diff is not None else None
    state = _FpState(root=root, cfg=cfg)
    for symref, record in snapshot.symbols.items():
        _fingerprint_symbol(state, symref, record)

    groups = _all_rung_groups(state, snapshot, touched, cfg)
    return Ok(_clone_report(state, groups))


def _is_private_helper(record: Any) -> bool:
    """True for a FUNCTION/METHOD symbol whose short name is `_`-prefixed
    (private/module-local, not re-exported) -- the population `find_helper_clones`
    scans."""
    short = record.id.qualname.rsplit(".", 1)[-1]
    return (
        record.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)
        and not record.public
        and short.startswith("_")
    )


# frob:doc docs/modules/dup.md#pipeline
def find_helper_clones(
    snapshot: GraphSnapshot, cfg: DupConfig
) -> Result[CloneReport, DupError]:
    """Dedicated dup pass over the PRIVATE-helper population (T-0288, pair (b)).

    Arch-forced over-splitting spawns families of near-identical tiny
    private helpers -- often below the whole-symbol `cfg.min_tokens`
    default, so `find_clones` alone would never compare them. This restricts
    the snapshot to private/module-local FUNCTION/METHOD symbols and reruns
    the same rung ladder with `cfg.helper_min_tokens` (a much lower floor)
    in place of `cfg.min_tokens`, so over-splitting is itself caught, not
    just the calls-inlined comparison `find_clones` now also does.
    """
    helper_symbols = {
        symref: record
        for symref, record in snapshot.symbols.items()
        if _is_private_helper(record)
    }
    helper_snapshot = snapshot.model_copy(update={"symbols": helper_symbols})
    helper_cfg = cfg.model_copy(update={"min_tokens": cfg.helper_min_tokens})
    return find_clones(helper_snapshot, helper_cfg)


def _clone_report(state: _FpState, groups: list[tuple[ClonePair, ...]]) -> CloneReport:
    """Assemble the final `CloneReport` (groups + run stats) and log the summary.

    Each group's `template` is best-effort: `build_group_template` never
    raises, returning `None` when reverse-templating is not possible for
    that group (docs/modules/dup.md's "Reverse-templating report" section)
    -- a missing template never blocks the report itself.
    """
    stats = DupStats(
        fingerprinted=state.fingerprinted,
        cache_hits=state.cache_hits,
        pairs_verified=state.pairs_verified,
        pairs_prefiltered=state.pairs_prefiltered,
    )
    clone_groups = tuple(
        CloneMatchGroup(pairs=group, template=build_group_template(state.root, group))
        for group in groups
    )
    _log.info(
        "find_clones: %d group(s), %d pair(s) verified, %d pair(s) prefiltered, "
        "%d symbol(s) fingerprinted, %d cache hit(s)",
        len(clone_groups),
        state.pairs_verified,
        state.pairs_prefiltered,
        state.fingerprinted,
        state.cache_hits,
    )
    return CloneReport(groups=clone_groups, stats=stats)


def _all_rung_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    cfg: DupConfig,
) -> list[tuple[ClonePair, ...]]:
    """Every clone group across the R1-R5 ladder, in rung order (R1/R2/R3,
    R1.5, R4, R5)."""
    seen_pairs: set[frozenset[str]] = set()
    groups = _hash_rung_groups(state, snapshot, touched, seen_pairs)
    groups += _region_groups(state, snapshot, touched, seen_pairs, cfg)
    groups += _r4_groups(state, snapshot, touched, seen_pairs)
    groups += _r5_groups(state, snapshot, touched, seen_pairs)
    return groups
