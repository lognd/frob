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
  `frob.lang` does not yet expose per-token).
- **R4 verification is now real tree edit distance.** `_apted_similarity_for_pair`
  calls `frob.lang.symbol_tree` to get actual node structure for both
  candidates and runs `frob_core.apted_similarity` (Zhang-Shasha over the
  real subtree, not a flat statement sequence) -- the REPORTED similarity
  on a `ClonePair` is this real metric. The statement-sequence Levenshtein
  (`_core.tree_edit_similarity`, still a real algorithm, just over a
  flatter unit) is kept as the near-miss floor check and the source of the
  region-span narrowing (`_region_span_for_alignment`) -- that alignment
  is still statement-index-based, not node-based, which is why it is kept
  separate from the reported similarity rather than replaced outright.
  Falls back to the statement-Levenshtein similarity when either side's
  subtree cannot be recovered (a parse failure, or a region whose span
  does not resolve to a single node).
- **Statement chunking is a keyword heuristic, not real AST statement
  boundaries** -- but only on the FALLBACK path now. `_split_statements`
  (cutting `body_tokens` at statement-starting keywords) still backs the
  R4 near-miss floor/alignment and the R5 fallback graph; the R5 primary
  path (`_real_dataflow_graph`) uses actual `block`-node children from
  `frob.lang.symbol_tree`, which are real AST statement boundaries, not a
  keyword guess. `frob:todo T-0001` follow-up: extend real statement
  boundaries to the R4 alignment/region-span path too.
- **R5's def-use/control-dependence graph is real when a `frob.lang`
  subtree is available.** `_real_dataflow_graph` finds the function's
  `block` node, labels identifiers "def"/"use" from actual `assignment`
  node child position (not a "next token is `=`" guess), and adds a
  sequential control-flow edge between consecutive statements -- real
  execution order, which the old proxy had no notion of at all. Still not
  a full CFG (no branch-edge fan-out for `if`/`for`/`while`, no true
  reaching-definitions dataflow) and augmented assignment/tuple-unpacking/
  `for`-target binding still fold into "use" -- recorded as `frob:todo
  T-0001` follow-up. `_build_dataflow_graph` (the original co-occurrence
  proxy) is kept as the fallback for regions where no `block` node is
  found (non-function regions, parse failures).
- **R7 (`probe_smt_equivalence`) is the bounded-SMT rung** docs/dup.md
  named as a research item, now real for its explicitly bounded subset:
  single-`return`, int/bool-annotated, straight-line functions built from
  `+ - * // %`, comparisons, `and/or/not`, and one `if`-expression --
  see `_smt_translate`'s accepted node set. Anything outside that subset
  is `Err(DupError.SmtUnsupported)`, never silently approximated. Opt-in
  and never called from `find_clones`/the gate path, same as R6. Requires
  the optional `z3-solver` dependency (`uv pip install frob[smt]`);
  degrades to `Err(DupError.SmtUnavailable)` without it.
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
_R4_APTED_VERDICT_METHOD = "r4apted"

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


# frob:doc docs/dup.md#pipeline
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
    """R5 fallback: a co-occurrence adjacency + def/use labels over identifier
    tokens, used only when `_real_dataflow_graph` cannot recover real
    statement nodes (parse failure, non-function region). See the module
    docstring's "R5's def-use/control-dependence graph" deviation note --
    this token-proxy path is intentionally kept as the honest fallback, not
    silently passed off as the real thing.
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


_STATEMENT_NODE_LABELS = frozenset(
    {
        "expression_statement",
        "if_statement",
        "for_statement",
        "while_statement",
        "return_statement",
        "with_statement",
        "try_statement",
        "pass_statement",
        "break_statement",
        "continue_statement",
        "raise_statement",
        "assert_statement",
        "global_statement",
        "nonlocal_statement",
        "import_statement",
        "import_from_statement",
        "delete_statement",
    }
)


def _find_block(node: Any) -> Any | None:
    """Depth-first search for the first `block` node (a Python function
    body's statement container) under `node`."""
    if node.label == "block":
        return node
    for child in node.children:
        found = _find_block(child)
        if found is not None:
            return found
    return None


def _leaf_labels(node: Any) -> tuple[str, ...]:
    """Every leaf label under `node`, in order (a `TreeNode`'s own leaf tokens)."""
    if not node.children:
        return (node.label,)
    out: list[str] = []
    for child in node.children:
        out.extend(_leaf_labels(child))
    return tuple(out)


def _real_dataflow_graph(
    tree: Any,
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]] | None:
    """R5 (real): a def-use adjacency plus sequential control-flow edges
    built from `frob.lang`'s actual statement nodes, not a token heuristic.

    Two edge kinds, both real (not proxied):
    - **def-use**: for an `expression_statement > assignment` node, targets
      (children before the `=` leaf) are labeled "def", the right-hand side
      (children after `=`) "use"; every identifier within one statement is
      pairwise-connected (the co-occurrence idea R5's proxy already had,
      now scoped to a real statement boundary instead of a keyword-guessed
      chunk).
    - **control-flow**: a sequencing edge from the last identifier node of
      statement *i* to the first identifier node of statement *i+1* --
      real adjacent-statement execution order, which the old co-occurrence
      proxy had no notion of at all.

    Returns `None` (caller falls back to `_build_dataflow_graph`) when no
    `block` node is found under `tree` (a non-function region, or a body
    with no direct statements) -- an honest "can't build a real graph
    here," not a silent wrong answer.
    """
    block = _find_block(tree)
    if block is None or not block.children:
        return None
    statements = tuple(c for c in block.children if c.label in _STATEMENT_NODE_LABELS)
    if not statements:
        return None

    labels: list[str] = []
    adjacency: list[tuple[int, int]] = []
    prev_last_idx: int | None = None

    for stmt in statements:
        is_assignment = bool(stmt.children) and stmt.children[0].label == "assignment"
        stmt_ids: list[int] = []
        if is_assignment:
            assign = stmt.children[0]
            eq_idx = next(
                (i for i, c in enumerate(assign.children) if c.label == "="), None
            )
            for i, child in enumerate(assign.children):
                if child.label == "=":
                    continue
                role = "def" if (eq_idx is not None and i < eq_idx) else "use"
                for leaf in _leaf_labels(child):
                    if _IDENT_RE.match(leaf) and leaf not in _KEYWORDS:
                        labels.append(role)
                        stmt_ids.append(len(labels) - 1)
        else:
            for leaf in _leaf_labels(stmt):
                if _IDENT_RE.match(leaf) and leaf not in _KEYWORDS:
                    labels.append("use")
                    stmt_ids.append(len(labels) - 1)

        for a in range(len(stmt_ids)):
            for b in range(a + 1, len(stmt_ids)):
                adjacency.append((stmt_ids[a], stmt_ids[b]))
        if prev_last_idx is not None and stmt_ids:
            adjacency.append((prev_last_idx, stmt_ids[0]))
        if stmt_ids:
            prev_last_idx = stmt_ids[-1]

    return tuple(adjacency), tuple(labels)


def _core_symbol_tree(root: Path, record: Any) -> Any | None:
    """Best-effort `frob.lang.symbol_tree` for a snapshot symbol record, or
    `None` on any parse failure (callers fall back to the token proxy)."""
    from frob.lang import symbol_tree

    result = symbol_tree(root / record.id.path, record.span)
    return result.danger_ok if result.is_ok else None


def _apted_similarity_for_pair(
    root: Path, left_record: Any, right_record: Any
) -> float | None:
    """Real tree-edit-distance similarity for a candidate pair, or `None`
    if either side's subtree cannot be recovered (parse failure, or a
    region whose span no longer resolves to a single node -- callers fall
    back to the statement-Levenshtein similarity in that case)."""
    from frob.lang import symbol_tree
    from frob.lang._common import flatten_tree

    left_tree = symbol_tree(root / left_record.id.path, left_record.span)
    right_tree = symbol_tree(root / right_record.id.path, right_record.span)
    if left_tree.is_err or right_tree.is_err:
        _log.debug(
            "find_clones: apted subtree unavailable for %s or %s",
            left_record.id.path,
            right_record.id.path,
        )
        return None
    labels_a, parents_a = flatten_tree(left_tree.danger_ok)
    labels_b, parents_b = flatten_tree(right_tree.danger_ok)
    sim_result = _core.apted_similarity(
        tuple(labels_a), tuple(parents_a), tuple(labels_b), tuple(parents_b)
    )
    if sim_result.is_err:
        return None
    return sim_result.danger_ok


# frob:doc docs/dup.md#public-api
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

        # R5: Weisfeiler-Lehman graph-kernel hash over a def-use/control-
        # flow graph, cached by digest. Prefers the real graph built from
        # frob.lang's statement nodes (`_real_dataflow_graph`); falls back
        # to the token co-occurrence proxy only when the real graph is
        # unavailable (see both functions' docstrings).
        cached_wl = _cache.get_fingerprint(root, digest, _R5_FP_RUNG)
        if cached_wl is not None:
            cache_hits += 1
            wl = cast(int, cached_wl[0])
        else:
            real_graph = None
            body_tree = _core_symbol_tree(root, record)
            if body_tree is not None:
                real_graph = _real_dataflow_graph(body_tree)
            if real_graph is not None:
                adjacency, labels = real_graph
            else:
                stmt_chunks = _split_statements(body_tokens)
                adjacency, labels = _build_dataflow_graph(stmt_chunks)
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
                # Real tree-edit-distance verification (Zhang-Shasha, via
                # frob-core's apted_similarity): the statement-Levenshtein
                # `sim` above already cleared the near-miss floor and picked
                # the region span; this refines the REPORTED similarity to
                # the real subtree-structure metric, which is sensitive to
                # within-statement reordering the flat sequence cannot see
                # (docs/dup.md's "Rung R4" note). Falls back to the
                # statement-Levenshtein `sim` if either side's subtree
                # cannot be recovered (e.g. a non-function region span).
                reported_sim = sim
                cached_apted = _cache.get_verdict(
                    root, d1, d2, _R4_APTED_VERDICT_METHOD, _CORPUS_EPOCH
                )
                if cached_apted is not None:
                    cache_hits += 1
                    reported_sim = cast(float, cached_apted[0])
                else:
                    apted_sim = _apted_similarity_for_pair(
                        root, snapshot.symbols[a], snapshot.symbols[b]
                    )
                    if apted_sim is not None:
                        reported_sim = apted_sim
                        _cache.put_verdict(
                            root,
                            d1,
                            d2,
                            _R4_APTED_VERDICT_METHOD,
                            _CORPUS_EPOCH,
                            (apted_sim, ()),
                            cfg.cache_entries,
                        )
                r4_group.append(
                    ClonePair(
                        left=CloneRegion(ref=a, span=left_span),
                        right=CloneRegion(ref=b, span=right_span),
                        similarity=reported_sim,
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


# frob:doc docs/dup.md#public-api
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


# R7 (opt-in, bounded-SMT): the AST node types `_smt_translate` accepts.
# Deliberately tiny -- straight-line int/bool arithmetic and comparisons
# only, no loops/calls/attribute access. Anything outside this subset is
# Err(SmtUnsupported), never a silent "probably fine."
_SMT_BINOPS = {"Add", "Sub", "Mult", "FloorDiv", "Mod"}
_SMT_CMPOPS = {"Eq", "NotEq", "Lt", "LtE", "Gt", "GtE"}
_SMT_BOOLOPS = {"And", "Or"}


def _smt_translate(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Recursively translate a bounded Python-`ast` expression subtree into
    a Z3 expression over `env` (name -> Z3 const). Raises `ValueError` for
    anything outside `_SMT_BINOPS`/`_SMT_CMPOPS`/`_SMT_BOOLOPS`/literals/
    names/`if`-expressions/`not`/unary-minus -- the caller converts that
    into `Err(SmtUnsupported)`, never silently drops the term.
    """
    import ast as _ast

    if isinstance(node, _ast.Constant) and isinstance(node.value, bool):
        return z3.BoolVal(node.value)
    if isinstance(node, _ast.Constant) and isinstance(node.value, int):
        return z3.IntVal(node.value)
    if isinstance(node, _ast.Name):
        if node.id not in env:
            raise ValueError(f"unbound name {node.id!r}")
        return env[node.id]
    if isinstance(node, _ast.UnaryOp):
        operand = _smt_translate(node.operand, z3, env)
        if isinstance(node.op, _ast.USub):
            return -operand
        if isinstance(node.op, _ast.Not):
            return z3.Not(operand)
        raise ValueError(f"unsupported unary op {type(node.op).__name__}")
    if isinstance(node, _ast.BinOp):
        op_name = type(node.op).__name__
        if op_name not in _SMT_BINOPS:
            raise ValueError(f"unsupported binop {op_name}")
        left = _smt_translate(node.left, z3, env)
        right = _smt_translate(node.right, z3, env)
        return {
            "Add": lambda: left + right,
            "Sub": lambda: left - right,
            "Mult": lambda: left * right,
            "FloorDiv": lambda: left / right,
            "Mod": lambda: left % right,
        }[op_name]()
    if isinstance(node, _ast.BoolOp):
        op_name = type(node.op).__name__
        if op_name not in _SMT_BOOLOPS:
            raise ValueError(f"unsupported boolop {op_name}")
        values = [_smt_translate(v, z3, env) for v in node.values]
        return z3.And(*values) if op_name == "And" else z3.Or(*values)
    is_simple_compare = (
        isinstance(node, _ast.Compare)
        and len(node.ops) == 1
        and len(node.comparators) == 1
    )
    if is_simple_compare:
        op_name = type(node.ops[0]).__name__
        if op_name not in _SMT_CMPOPS:
            raise ValueError(f"unsupported compare op {op_name}")
        left = _smt_translate(node.left, z3, env)
        right = _smt_translate(node.comparators[0], z3, env)
        return {
            "Eq": lambda: left == right,
            "NotEq": lambda: left != right,
            "Lt": lambda: left < right,
            "LtE": lambda: left <= right,
            "Gt": lambda: left > right,
            "GtE": lambda: left >= right,
        }[op_name]()
    if isinstance(node, _ast.IfExp):
        test = _smt_translate(node.test, z3, env)
        body = _smt_translate(node.body, z3, env)
        orelse = _smt_translate(node.orelse, z3, env)
        return z3.If(test, body, orelse)
    raise ValueError(f"unsupported node {type(node).__name__}")


def _smt_function_expr(source: str, z3: Any) -> tuple[Any, list[Any]] | None:
    """Parse `source` (one `def f(...): return <expr>` function) into a Z3
    expression plus its ordered parameter consts, or `None` if it is not a
    single-return, int/bool-annotated, bounded-subset function."""
    import ast as _ast

    tree = _ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], _ast.FunctionDef):
        return None
    fn = tree.body[0]
    if len(fn.body) != 1 or not isinstance(fn.body[0], _ast.Return):
        return None
    if fn.body[0].value is None:
        return None

    env: dict[str, Any] = {}
    params: list[Any] = []
    for arg in fn.args.args:
        ann = getattr(arg.annotation, "id", None)
        if ann == "int":
            const = z3.Int(arg.arg)
        elif ann == "bool":
            const = z3.Bool(arg.arg)
        else:
            return None
        env[arg.arg] = const
        params.append(const)

    try:
        expr = _smt_translate(fn.body[0].value, z3, env)
    except ValueError as exc:
        _log.debug("probe_smt_equivalence: unsupported subset (%s)", exc)
        return None
    return expr, params


# frob:doc docs/dup.md#rung-r7
def probe_smt_equivalence(
    a: str, b: str, snapshot: GraphSnapshot
) -> Result[ProbeVerdict, DupError]:
    """R7 (opt-in, research-frontier per docs/dup.md): bounded-SMT formal
    equivalence for tiny pure int/bool functions, via z3-solver.

    Degrades to `Err(SmtUnavailable)` when `z3-solver` is not installed
    (an optional dependency -- `uv pip install frob[smt]`), and to
    `Err(SmtUnsupported)` for anything outside the bounded subset
    `_smt_translate` accepts (straight-line int/bool arithmetic,
    comparisons, `and`/`or`/`not`, one `if`-expression return -- no loops,
    calls, or attribute access). Unlike R6's observational probing, an
    UNSAT result here is a formal proof of equivalence over the whole
    input domain, not evidence from sampled cases.
    """
    try:
        import z3  # ty: ignore[unresolved-import]  # optional dep, frob[smt]
    except ImportError:
        _log.warning("probe_smt_equivalence: z3-solver not installed")
        return Err(DupError.SmtUnavailable)

    root = Path(snapshot.root)
    a_rec = snapshot.symbols.get(a)
    b_rec = snapshot.symbols.get(b)
    if a_rec is None or b_rec is None:
        return Err(DupError.NotPure)

    fn_a = _load_python_callable(root, a_rec.id.path, a_rec.id.qualname)
    fn_b = _load_python_callable(root, b_rec.id.path, b_rec.id.qualname)
    if fn_a is None or fn_b is None:
        return Err(DupError.SmtUnsupported)

    import inspect
    import textwrap

    try:
        src_a = textwrap.dedent(inspect.getsource(fn_a))
        src_b = textwrap.dedent(inspect.getsource(fn_b))
    except (OSError, TypeError):
        return Err(DupError.SmtUnsupported)

    parsed_a = _smt_function_expr(src_a, z3)
    parsed_b = _smt_function_expr(src_b, z3)
    if parsed_a is None or parsed_b is None:
        return Err(DupError.SmtUnsupported)
    expr_a, params_a = parsed_a
    expr_b, params_b = parsed_b
    if len(params_a) != len(params_b):
        return Err(DupError.SmtUnsupported)
    # Share params_a's consts as both functions' free variables (b's own
    # params were already substituted in when translated with its own
    # env -- rebuild b's expr over a's consts by positional identity).
    solver = z3.Solver()
    subst = list(zip(params_b, params_a, strict=True))
    expr_b_over_a = z3.substitute(expr_b, *subst) if subst else expr_b
    solver.add(expr_a != expr_b_over_a)
    verdict = solver.check()

    if verdict == z3.unsat:
        _log.info("probe_smt_equivalence: %s vs %s -- proved equivalent", a, b)
        return Ok(ProbeVerdict(left=a, right=b, equivalent=True, cases_run=0))
    if verdict == z3.sat:
        model = solver.model()
        counterexample = {
            str(p): str(model.eval(p, model_completion=True)) for p in params_a
        }
        _log.info("probe_smt_equivalence: %s vs %s -- counterexample found", a, b)
        return Ok(
            ProbeVerdict(
                left=a,
                right=b,
                equivalent=False,
                cases_run=1,
                counterexample=counterexample,
            )
        )
    _log.warning("probe_smt_equivalence: %s vs %s -- solver returned unknown", a, b)
    return Err(DupError.SmtUnsupported)


__all__ = [
    "find_clones",
    "probe_equivalence",
    "probe_smt_equivalence",
    "touched_refs",
]
