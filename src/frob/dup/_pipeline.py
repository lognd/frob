"""The smart-dup pipeline: fingerprint -> candidates -> verify -> report.

Implements docs/dup.md's `find_clones` across the full rung ladder:

- R1 (exact token hash) and R2 (alpha-renamed token hash) are pure Python,
  always available -- they operate directly on `frob.lang`'s
  `RawSymbol.body_tokens`.
- R3 (canonicalized subtree hash), R4 (winnowed fingerprints + candidate
  discovery + statement-alignment verification), and R5 (Weisfeiler-Lehman
  dataflow-graph hashing) all need the `frob_core` native extension. Per
  docs/dup.md's no-silent-fallback rule there is no pure-Python
  reimplementation of R3+ to fall back on: `find_clones` treats the whole
  ladder as one call and returns `Err(DupError.CoreUnavailable)` up front
  when `frob_core` is not importable.
- R6 (`probe_equivalence`) is opt-in and orchestrated separately -- it is
  never called from `find_clones`/the DUP gate path, only from a caller
  that explicitly wants behavioral probing (docs/dup.md: "opt-in --probe
  path").

**Deviations from docs/dup.md** (recorded, not silently dropped):
- R2's alpha-renaming abstracts every identifier-shaped token uniformly
  (no scope/locals distinction), because `frob.lang.RawSymbol.body_tokens`
  is a flat leaf-token tuple with no node-type metadata attached -- unlike
  the legacy `frob.dup._legacy` scanner, which walked tree-sitter nodes
  directly. Good enough to catch pure rename clones; a future
  `frob.lang` token-kind channel would make it exact.
- R3 is computed by the frob_core kernel over the R2-normalized token
  stream, not full literal-abstraction/control-flow normalization (which
  `frob.lang` does not yet expose per-token). frob_core's own
  `tree_edit_similarity` is a statement-sequence Levenshtein alignment,
  not full APTED -- see its docstring.
- **Statement chunking is a keyword heuristic, not real AST statement
  boundaries.** `body_tokens` is a flat leaf-token tuple with no
  statement/newline markers, so R4's "statement alignment" and R5's
  def-use graph both need *some* notion of a statement. `_split_statements`
  cuts the token stream every time a statement-starting keyword appears
  (`if`, `for`, `return`, ...). This is honest best-effort, not a real
  parse: it can mis-split multi-line expressions or nested nested
  one-liners. Recorded as `frob:todo T-0001` follow-up: a `frob.lang`
  statement-boundary channel would make this exact.
- **R5's def-use/control-dependence graph is a co-occurrence proxy, not a
  real dataflow graph.** frob.lang exposes no scope/def/use resolution, so
  `_build_dataflow_graph` connects every identifier-shaped token to every
  other identifier-shaped token within the same heuristic statement chunk
  (an undirected co-occurrence edge), and labels a token "def" if the next
  token is `=` (plain assignment only -- augmented assignment, tuple
  unpacking, and `for`-target binding are all folded into "use"). This
  catches reordered-statement, same-locals-touched clones; it will both
  under- and over-connect relative to true CFG/DFG edges. Recorded as
  `frob:todo T-0001` follow-up.
- **R6's purity heuristic is conservative and token-based**, not a real
  effect analysis: a body is treated as pure only if it contains none of
  `_IMPURE_TOKENS` (IO, exec/eval, global/nonlocal, common stdlib
  side-effect modules). False negatives (rejecting an actually-pure
  function) are expected and safe; false positives (probing an impure
  function) are the failure mode this heuristic exists to avoid, so it
  errs toward refusal.
- R6 only probes Python callables loaded from the worktree by
  `importlib`; other `frob.lang` languages return `Err(DupError.NotPure)`
  (no cross-language FFI harness exists to call a Rust/TS/C function from
  Python).
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import time
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from typani import Err, Ok
from typani.result import Result

from frob.dup import _cache, _core
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
        "def",
        "class",
        "return",
        "if",
        "elif",
        "else",
        "for",
        "while",
        "in",
        "not",
        "and",
        "or",
        "is",
        "import",
        "from",
        "as",
        "with",
        "try",
        "except",
        "finally",
        "raise",
        "pass",
        "break",
        "continue",
        "lambda",
        "yield",
        "async",
        "await",
        "None",
        "True",
        "False",
        "self",
        "cls",
        "global",
        "nonlocal",
        "assert",
        "del",
    }
)

# Statement-starting keywords for the heuristic chunker (module docstring's
# "Statement chunking" deviation note).
_STMT_STARTERS = frozenset(
    {
        "if",
        "elif",
        "else",
        "for",
        "while",
        "return",
        "assert",
        "raise",
        "pass",
        "break",
        "continue",
        "with",
        "try",
        "except",
        "finally",
        "yield",
        "global",
        "nonlocal",
        "del",
        "import",
        "from",
    }
)

# Tokens that make a body ineligible for R6 probing (module docstring's
# "R6's purity heuristic" deviation note). Substring-matched against every
# token so `os.system`, `sys.exit`, dotted-attribute IO all trip it even
# though `frob.lang` tokens are leaf-level (e.g. "os", ".", "system").
_IMPURE_TOKENS = frozenset(
    {
        "open",
        "print",
        "input",
        "exec",
        "eval",
        "compile",
        "__import__",
        "global",
        "nonlocal",
        "os",
        "sys",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "random",
        "time",
        "datetime",
        "environ",
        "write",
        "read",
        "remove",
        "unlink",
        "system",
        "popen",
        "getenv",
        "setattr",
        "delattr",
    }
)

# R4 winnowing k-gram/window sizes and the near-miss acceptance floor.
_R4_K = 5
_R4_W = 4
_R4_MIN_SHARED = 2
_R4_SIMILARITY_FLOOR = 0.6

# R5 iteration count for the WL-kernel refinement and its match similarity
# (WL hashing is a boolean collide/not-collide signal, not a continuous
# metric, so an exact-hash match is reported at a fixed high similarity).
_R5_ITERATIONS = 2
_R5_SIMILARITY = 0.88

# Cache "method" tags and a fixed corpus epoch (bumped only if the
# winnowing/WL parameters above ever change -- there is no generator
# dependency for R4/R5, unlike R6's fuzz-corpus epoch).
_R4_VERDICT_METHOD = "r4"
_R5_FP_RUNG = "r5"
_R4_FP_RUNG = "r4fp"
_CORPUS_EPOCH = 0


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


def _digest(tokens: tuple[str, ...]) -> str:
    """Content-addressed digest of a symbol body (the dup cache's cache key)."""
    payload = "\x00".join(tokens).encode("utf-8", "surrogatepass")
    return hashlib.sha256(payload).hexdigest()


def _split_statements(tokens: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """Heuristic statement chunker -- see the module docstring's deviation note."""
    if not tokens:
        return ()
    chunks: list[list[str]] = [[]]
    for tok in tokens:
        if tok in _STMT_STARTERS and chunks[-1]:
            chunks.append([])
        chunks[-1].append(tok)
    return tuple(tuple(c) for c in chunks if c)


def _statement_hashes(chunks: tuple[tuple[str, ...], ...]) -> tuple[int, ...]:
    """One stable int hash per statement chunk, for `tree_edit_similarity`."""
    return tuple(hash(c) & 0xFFFFFFFFFFFFFFFF for c in chunks)


def _line_for_statement_index(span: tuple[int, int], idx: int, total: int) -> int:
    """Best-effort line number for statement `idx` of `total`, spread over `span`.

    No real line-per-statement mapping exists (the heuristic chunker has no
    source-position info), so this distributes statement indices evenly
    across the symbol's known line span -- a documented approximation, not
    an exact mapping.
    """
    lo, hi = span
    if total <= 1:
        return lo
    frac = idx / (total - 1)
    return lo + round(frac * (hi - lo))


def _region_span_for_alignment(
    span: tuple[int, int],
    total: int,
    matched_indices: tuple[int, ...],
) -> tuple[int, int]:
    """The contiguous line subrange covering `matched_indices` of `total` statements.

    Falls back to the whole `span` when there is nothing to narrow (region-
    subsection matching per docs/dup.md: a subsection hit should report a
    tighter span than the whole symbol whenever the alignment does not
    cover every statement).
    """
    if not matched_indices or total <= 1:
        return span
    lo_idx, hi_idx = min(matched_indices), max(matched_indices)
    lo = _line_for_statement_index(span, lo_idx, total)
    hi = _line_for_statement_index(span, hi_idx, total)
    return (min(lo, hi), max(lo, hi))


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


def _build_dataflow_graph(
    chunks: tuple[tuple[str, ...], ...],
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]]:
    """R5: a co-occurrence adjacency + def/use labels over identifier tokens.

    See the module docstring's "R5's def-use/control-dependence graph"
    deviation note -- this is a proxy, not a real dataflow graph.
    """
    nodes: list[str] = []  # label per node
    adjacency: list[tuple[int, int]] = []
    for chunk in chunks:
        chunk_node_ids: list[int] = []
        for i, tok in enumerate(chunk):
            if not (_IDENT_RE.match(tok) and tok not in _KEYWORDS):
                continue
            is_def = i + 1 < len(chunk) and chunk[i + 1] == "="
            nodes.append("def" if is_def else "use")
            chunk_node_ids.append(len(nodes) - 1)
        for a in range(len(chunk_node_ids)):
            for b in range(a + 1, len(chunk_node_ids)):
                adjacency.append((chunk_node_ids[a], chunk_node_ids[b]))
    return tuple(adjacency), tuple(nodes)


def find_clones(
    snapshot: GraphSnapshot, cfg: DupConfig, diff: Diff | None = None
) -> Result[CloneReport, DupError]:
    """Run the full R1-R5 rung ladder over `snapshot` (R6 is opt-in, separate).

    `diff` restricts the "new side" to touched symbols (the DUP001 gate
    path); `diff=None` scans the whole snapshot. Fingerprints and pairwise
    verdicts are read/written through `frob.dup._cache` (content-addressed
    by body digest), so re-runs over an unchanged body/pair skip recompute.
    """
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
    r5_buckets: dict[int, list[str]] = defaultdict(list)
    fingerprinted = 0
    cache_hits = 0
    tokens_by_path: dict[str, dict[str, tuple[str, ...]]] = {}
    body_tokens_by_ref: dict[str, tuple[str, ...]] = {}
    digest_by_ref: dict[str, str] = {}
    fp_by_ref: dict[str, tuple[int, ...]] = {}

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
        body_tokens_by_ref[symref] = body_tokens
        digest = _digest(body_tokens)
        digest_by_ref[symref] = digest
        normalized = _r2_normalize(body_tokens)

        r1_buckets[_r1_hash(body_tokens)].append(symref)
        r2_buckets[_r2_hash(body_tokens)].append(symref)

        # R3: canonicalized subtree hash, computed by the frob_core kernel
        # over the same alpha-renamed token stream (a simplification of
        # true R3 canonicalization -- see the module docstring's
        # Deviations note; literal abstraction/control-flow normalization
        # is not yet exposed by frob.lang). Cached by digest.
        cached_r3 = _cache.get_fingerprint(root, digest, "r3")
        if cached_r3 is not None:
            cache_hits += 1
            r3_hash = str(cached_r3[0])
        else:
            r3_result = _core.r3_canonical_hash(normalized)
            if r3_result.is_err:
                continue
            r3_hash = r3_result.danger_ok
            _cache.put_fingerprint(root, digest, "r3", (r3_hash,))
        r3_buckets["r3:" + r3_hash].append(symref)

        # R4: winnowed fingerprint set, cached by digest.
        cached_fp = _cache.get_fingerprint(root, digest, _R4_FP_RUNG)
        if cached_fp is not None:
            cache_hits += 1
            fp_by_ref[symref] = cast(tuple[int, ...], tuple(cached_fp))
        else:
            fp_result = _core.winnow_fingerprints(normalized, _R4_K, _R4_W)
            if fp_result.is_ok:
                fps = fp_result.danger_ok
                fp_by_ref[symref] = fps
                _cache.put_fingerprint(root, digest, _R4_FP_RUNG, fps)

        # R5: Weisfeiler-Lehman graph-kernel hash over the def-use proxy
        # graph, cached by digest.
        cached_wl = _cache.get_fingerprint(root, digest, _R5_FP_RUNG)
        if cached_wl is not None:
            cache_hits += 1
            wl = cast(int, cached_wl[0])
        else:
            adjacency, labels = _build_dataflow_graph(_split_statements(body_tokens))
            wl_result = _core.wl_hash(adjacency, labels, _R5_ITERATIONS)
            if wl_result.is_err:
                continue
            wl = wl_result.danger_ok
            _cache.put_fingerprint(root, digest, _R5_FP_RUNG, (wl,))
        r5_buckets[wl].append(symref)

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

    # R4: candidate discovery over winnowed fingerprints, then statement-
    # alignment verification (skips anything already matched by R1-R3).
    r4_refs = list(fp_by_ref)
    if len(r4_refs) >= 2:
        sets = tuple(fp_by_ref[r] for r in r4_refs)
        candidates_result = _core.candidate_pairs(sets, _R4_MIN_SHARED)
        if candidates_result.is_ok:
            r4_group: list[ClonePair] = []
            for i, j in candidates_result.danger_ok:
                a, b = r4_refs[i], r4_refs[j]
                if touched is not None and a not in touched and b not in touched:
                    continue
                key = frozenset((a, b))
                if key in seen_pairs:
                    continue
                d1, d2 = digest_by_ref[a], digest_by_ref[b]
                cached_verdict = _cache.get_verdict(
                    root, d1, d2, _R4_VERDICT_METHOD, _CORPUS_EPOCH
                )
                if cached_verdict is not None:
                    cache_hits += 1
                    sim = cast(float, cached_verdict[0])
                    raw_alignment = cast("list[list[int]]", cached_verdict[1])
                    alignment_pairs = tuple((p[0], p[1]) for p in raw_alignment)
                else:
                    a_chunks = _split_statements(body_tokens_by_ref[a])
                    b_chunks = _split_statements(body_tokens_by_ref[b])
                    a_hashes = _statement_hashes(a_chunks)
                    b_hashes = _statement_hashes(b_chunks)
                    sim_result = _core.tree_edit_similarity(a_hashes, b_hashes)
                    if sim_result.is_err:
                        continue
                    sim, alignment_pairs = sim_result.danger_ok
                    _cache.put_verdict(
                        root,
                        d1,
                        d2,
                        _R4_VERDICT_METHOD,
                        _CORPUS_EPOCH,
                        (sim, alignment_pairs),
                        cfg.cache_entries,
                    )
                pairs_verified += 1
                seen_pairs.add(key)
                if sim < _R4_SIMILARITY_FLOOR:
                    continue
                a_chunks = _split_statements(body_tokens_by_ref[a])
                b_chunks = _split_statements(body_tokens_by_ref[b])
                a_idx = tuple(p[0] for p in alignment_pairs)
                b_idx = tuple(p[1] for p in alignment_pairs)
                left_span = _region_span_for_alignment(
                    snapshot.symbols[a].span, len(a_chunks), a_idx
                )
                right_span = _region_span_for_alignment(
                    snapshot.symbols[b].span, len(b_chunks), b_idx
                )
                r4_group.append(
                    ClonePair(
                        left=CloneRegion(ref=a, span=left_span),
                        right=CloneRegion(ref=b, span=right_span),
                        similarity=sim,
                        rung="r4",
                        alignment=alignment_pairs,
                    )
                )
            if r4_group:
                groups.append(tuple(r4_group))
        else:
            _log.debug("find_clones: r4 candidate discovery unavailable")

    # R5: WL-hash bucket collisions not already found by an earlier rung.
    r5_group: list[ClonePair] = []
    for members in r5_buckets.values():
        if len(members) < 2:
            continue
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
                r5_group.append(
                    ClonePair(
                        left=CloneRegion(ref=a, span=snapshot.symbols[a].span),
                        right=CloneRegion(ref=b, span=snapshot.symbols[b].span),
                        similarity=_R5_SIMILARITY,
                        rung="r5",
                    )
                )
    if r5_group:
        groups.append(tuple(r5_group))

    stats = DupStats(
        fingerprinted=fingerprinted,
        cache_hits=cache_hits,
        pairs_verified=pairs_verified,
    )
    _log.info(
        "find_clones: %d group(s), %d pair(s) verified, %d symbol(s) fingerprinted, "
        "%d cache hit(s)",
        len(groups),
        pairs_verified,
        fingerprinted,
        cache_hits,
    )
    return Ok(CloneReport(groups=tuple(groups), stats=stats))


_builtin_generators_registered = False


def _ensure_builtin_generators() -> None:
    """Register plain-builtin Arbitrary strategies once (int/float/str/bool).

    `frob.fuzz.resolve` only derives generators for pydantic `BaseModel`
    subclasses or types with a declared/registered strategy -- it has no
    built-in fallback for `int`/`str`/etc. R6 probing overwhelmingly needs
    exactly those scalar types, so this registers them once, through the
    same public `frob.fuzz.register` mechanism the docs describe for
    "third-party types the caller cannot annotate" -- plain builtins are
    exactly that case for a probe harness that does not own the probed
    function's module.
    """
    global _builtin_generators_registered
    if _builtin_generators_registered:
        return
    from frob.fuzz._arbitrary import HYPOTHESIS_AVAILABLE, register

    if not HYPOTHESIS_AVAILABLE:
        return
    import hypothesis.strategies as st

    register(int, st.integers(min_value=-10_000, max_value=10_000))
    register(float, st.floats(allow_nan=False, allow_infinity=False, width=32))
    register(str, st.text(max_size=20))
    register(bool, st.booleans())
    _builtin_generators_registered = True


def _is_pure_heuristic(tokens: tuple[str, ...]) -> bool:
    """Conservative purity check -- see the module docstring's R6 deviation note."""
    return not any(tok in _IMPURE_TOKENS for tok in tokens)


def _load_python_callable(root: Path, path: str, qualname: str) -> Any | None:
    """Best-effort `importlib` load of a top-level or `Class.method` callable."""
    if not path.endswith(".py"):
        return None
    file_path = root / path
    try:
        module_name = f"_frob_dup_probe_{hash(path)}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - any import-time failure means "can't probe"
        _log.debug("probe_equivalence: failed to load %s: %s", path, exc)
        return None

    obj: Any = module
    for part in qualname.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj if callable(obj) else None


def probe_equivalence(
    a: str, b: str, snapshot: GraphSnapshot, budget_s: float
) -> Result[ProbeVerdict, DupError]:
    """R6: observational-equivalence probing for effect-free candidate pairs.

    Refuses (`Err(NotPure)`) unless both `a` and `b` pass the conservative
    token-based purity heuristic AND both load as importable Python
    callables (see the module docstring's R6 deviation notes). Draws
    inputs from `frob.fuzz`'s Arbitrary generators keyed on `a`'s
    parameter type hints (falls back to `Err(NoGenerator)` when a
    parameter's type has no resolvable generator) and compares outputs
    for up to `budget_s` seconds.
    """
    root = Path(snapshot.root)
    a_rec = snapshot.symbols.get(a)
    b_rec = snapshot.symbols.get(b)
    if a_rec is None or b_rec is None:
        _log.debug("probe_equivalence: %s or %s not in snapshot", a, b)
        return Err(DupError.NotPure)

    a_tokens = _parsed_symbols_by_path(root, a_rec.id.path).get(a_rec.id.qualname)
    b_tokens = _parsed_symbols_by_path(root, b_rec.id.path).get(b_rec.id.qualname)
    if not a_tokens or not b_tokens:
        _log.debug("probe_equivalence: %s or %s has no body tokens", a, b)
        return Err(DupError.NotPure)
    if not (_is_pure_heuristic(a_tokens) and _is_pure_heuristic(b_tokens)):
        _log.info("probe_equivalence: %s vs %s -- purity heuristic refuses", a, b)
        return Err(DupError.NotPure)

    fn_a = _load_python_callable(root, a_rec.id.path, a_rec.id.qualname)
    fn_b = _load_python_callable(root, b_rec.id.path, b_rec.id.qualname)
    if fn_a is None or fn_b is None:
        _log.info("probe_equivalence: %s or %s could not be loaded as a callable", a, b)
        return Err(DupError.NotPure)

    import inspect

    from frob.fuzz._arbitrary import resolve

    _ensure_builtin_generators()

    try:
        sig = inspect.signature(fn_a)
    except (TypeError, ValueError):
        return Err(DupError.NotPure)

    strategies: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            return Err(DupError.NoGenerator)
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            return Err(DupError.NoGenerator)
        gen_result = resolve(annotation)
        if gen_result.is_err:
            return Err(DupError.NoGenerator)
        strategies[name] = gen_result.danger_ok

    cases_run = 0
    equivalent = True
    counterexample: dict[str, str] | None = None
    start = time.monotonic()
    max_cases = 50
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        while (
            equivalent and cases_run < max_cases and time.monotonic() - start < budget_s
        ):
            kwargs = {name: strategy.example() for name, strategy in strategies.items()}
            cases_run += 1
            try:
                result_a = fn_a(**kwargs)
            except Exception as exc:  # noqa: BLE001 - comparing failure modes, not raising
                result_a = ("__frob_exc__", type(exc).__name__)
            try:
                result_b = fn_b(**kwargs)
            except Exception as exc:  # noqa: BLE001 - comparing failure modes, not raising
                result_b = ("__frob_exc__", type(exc).__name__)
            if result_a != result_b:
                equivalent = False
                counterexample = {
                    **{k: repr(v) for k, v in kwargs.items()},
                    "left_result": repr(result_a),
                    "right_result": repr(result_b),
                }

    _log.info(
        "probe_equivalence: %s vs %s -- equivalent=%s cases_run=%d",
        a,
        b,
        equivalent,
        cases_run,
    )
    return Ok(
        ProbeVerdict(
            left=a,
            right=b,
            equivalent=equivalent,
            cases_run=cases_run,
            counterexample=counterexample,
        )
    )


__all__ = ["find_clones", "probe_equivalence", "touched_refs"]
