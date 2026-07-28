"""Call-graph substitution/inlining + dataflow-proxy graph helpers (split from
`dup/_pipeline.py`, T-1086).

`touched_refs` (public), private-helper call substitution/inlining feeding
R2+'s calls-inlined comparison, and the R5 def-use/control-dependence graph
builders (both the real `frob.lang`-subtree path and the co-occurrence
fallback proxy) -- see docs/modules/dup.md#pipeline.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from frob.dup import _core
from frob.dup._pipeline._shared import (
    _ASSIGNMENT_LABELS,
    _BLOCK_LABELS,
    _DECLARATOR_LABELS,
    _IDENT_RE,
    _KEYWORDS,
    _FpState,
    _log,
)
from frob.gitio import Diff
from frob.graph._models import GraphSnapshot
from frob.graph.callgraph import CallGraph, build_call_graph, is_symref


# frob:doc docs/modules/dup.md#pipeline
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


def _package_paths(root: Path, path: str) -> tuple[str, ...]:
    """Every language-supported file sitting next to `path` (same directory),
    repo-root-relative POSIX, `path` itself included -- the file set
    `build_call_graph` resolves intra-package private-helper calls over."""
    from frob.lang import supported_extensions

    directory = (root / path).parent
    if not directory.is_dir():
        return (path,)
    exts = supported_extensions()
    found = [
        (directory / name).relative_to(root).as_posix()
        for name in sorted(directory.iterdir())
        if (directory / name).is_file() and (directory / name).suffix.lower() in exts
    ]
    return tuple(found) or (path,)


def _call_graph_for_path(state: _FpState, path: str) -> CallGraph:
    """The (cached) intra-package call graph for `path`'s directory."""
    directory = str(Path(path).parent)
    cached = state.callgraph_by_dir.get(directory)
    if cached is not None:
        return cached
    graph = build_call_graph(state.root, _package_paths(state.root, path))
    state.callgraph_by_dir[directory] = graph
    return graph


def _caller_counts(state: _FpState, path: str, graph: CallGraph) -> dict[str, int]:
    """`{callee_symref: number-of-distinct-callers}` for `graph`, cached per
    directory (T-0288 shared-helper false-positive fix). A callee reached by
    more than one caller is CODE REUSE, not duplication: two unrelated
    functions calling the same private helper must not have that helper's
    body inflate their similarity. See `_substitute_calls`, which refuses to
    inline any callee with a count > 1 here."""
    directory = str(Path(path).parent)
    cached = state.caller_counts_by_dir.get(directory)
    if cached is not None:
        return cached
    counts: dict[str, int] = defaultdict(int)
    for callees in graph.calls.values():
        for callee_symref in set(callees):
            counts[callee_symref] += 1
    state.caller_counts_by_dir[directory] = counts
    return counts


# frob:ticket T-0814
def _is_symref(entry: str) -> bool:
    """True if `entry` looks like a real `path::qualname` call-graph node
    (a `CallGraph.calls` entry), false for a non-symref sentinel such as
    `frob.graph.callgraph.UNRESOLVED_CALLEE` -- every raw `graph.calls`
    consumer here must check this before `split("::", 1)`, which
    IndexErrors/ValueErrors on a bare sentinel with no `::` (T-0814). Thin
    wrapper over `frob.graph.callgraph.is_symref` (extracted T-0861)."""
    return is_symref(entry)


def _callee_name_map(graph: CallGraph, caller_symref: str) -> dict[str, str]:
    """`{short_call_name: callee_symref}` for one caller's recorded PRIVATE
    callees (see `build_call_graph`). Skips any non-symref sentinel entry
    (e.g. `UNRESOLVED_CALLEE`) -- it names no real callee to inline or
    splice (T-0814); downstream consumers (`_splice_call_site`,
    `_callee_tokens`) only ever see values pulled from this map, so
    filtering here protects them too."""
    result: dict[str, str] = {}
    for callee_symref in graph.calls.get(caller_symref, ()):
        if not _is_symref(callee_symref):
            continue
        short = callee_symref.split("::", 1)[1].rsplit(".", 1)[-1]
        result[short] = callee_symref
    return result


def _callee_tokens(state: _FpState, callee_symref: str) -> tuple[str, ...] | None:
    """`callee_symref`'s body tokens, parsing (and caching) its file on first use."""
    callee_path, callee_qualname = callee_symref.split("::", 1)
    if callee_path not in state.tokens_by_path:
        state.tokens_by_path[callee_path] = _parsed_symbols_by_path(
            state.root, callee_path
        )
    return state.tokens_by_path[callee_path].get(callee_qualname)


# NOTE (T-0288 reviewer reconcile, re: T-0290 reuse): `_substitute_calls`
# bounds its walk the same shape as `frob.graph.callgraph.closure` (depth
# cap, node budget, cycle guard via `visited`), but cannot delegate to
# `closure` directly -- `closure` returns a flat, already-decided BFS order
# of symrefs, whereas this function does interleaved TOKEN splicing:
# which callee to expand next depends on where its call-span sits inside
# the *already-substituted* token stream of its caller, and each splice
# consumes shared `budget` before the next call site is even scanned. That
# requires re-walking token-by-token, not just following a precomputed
# node list. Reusing `closure`'s bounds isn't cheap without changing its
# return shape, so the bounding constants (depth/nodes) are intentionally
# kept independent here; left as a note rather than a forced reuse.
def _substitute_calls(
    state: _FpState,
    path: str,
    caller_symref: str,
    tokens: list[str],
    visited: frozenset[str],
    budget: list[int],
    depth: int,
) -> list[str]:
    """IN-PLACE call-splicing: replace each resolved `name(...)` call span with
    the callee's own (recursively substituted) body tokens.

    Bounded: `depth >= inline_max_depth` or `budget[0] <= 0` stops
    substituting further and returns `tokens` unchanged past that point --
    the documented "fall back to the un-inlined body past the cap"
    behavior. Cycle-guarded via `visited` (a symref already on the current
    call chain is left as an un-substituted call, never re-entered).
    Public callees never appear in `graph.calls` at all (see
    `build_call_graph`), so this walk stops at the public-API boundary
    automatically -- no separate check needed here.

    SHARED-HELPER GUARD (T-0288 false-positive fix): a callee reached by
    more than one caller anywhere in `graph` (`_caller_counts`) is left as
    an opaque, un-substituted call on every side, never inlined. Sharing a
    helper is normal code reuse, not duplication -- inlining it into two
    unrelated callers would make the *shared helper's* body dominate their
    similarity instead of their own (distinct) logic. Only a private
    helper with exactly one caller gets inlined, which is exactly the case
    that matters for split-duplication detection: two differently-named,
    each-singly-called helpers with near-identical bodies still get
    expanded and compared.
    """
    if depth >= state.cfg.inline_max_depth or budget[0] <= 0:
        return tokens
    graph = _call_graph_for_path(state, path)
    name_map = _callee_name_map(graph, caller_symref)
    if not name_map:
        return tokens
    caller_counts = _caller_counts(state, path, graph)
    out: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        # frob:invariant terminates reason="mutually recurses with _substitute_calls only through _splice_call_site, which increments depth and decrements budget[0] on every recursive descent; this call itself is a plain token scan, not a recursive step" measure="state.cfg.inline_max_depth - depth strictly decreases across the mutual-recursion chain, and budget[0] is checked >0 at each entry"  # noqa: E501
        spliced = _splice_call_site(
            state, tokens, i, name_map, visited, caller_counts, budget, depth
        )
        if spliced is not None:
            new_tokens, next_i = spliced
            out.extend(new_tokens)
            i = next_i
            continue
        out.append(tokens[i])
        i += 1
    return out


# frob:ticket T-0361
def _splice_call_site(
    state: _FpState,
    tokens: list[str],
    i: int,
    name_map: dict[str, str],
    visited: frozenset[str],
    caller_counts: dict[str, int],
    budget: list[int],
    depth: int,
) -> tuple[list[str], int] | None:
    """If `tokens[i]` starts a resolvable, inlinable, singly-called `name(...)`
    call site, scan to its matching close-paren and return the callee's
    recursively-substituted body tokens plus the token index just past the
    call; `None` if position `i` is not such a call site (left for the
    caller to append as an ordinary token). Split out of `_substitute_calls`'
    scan loop (T-0361)."""
    n = len(tokens)
    tok = tokens[i]
    if not (
        budget[0] > 0
        and i + 1 < n
        and tokens[i + 1] == "("
        and tok in name_map
        and name_map[tok] not in visited
        and caller_counts.get(name_map[tok], 0) <= 1
    ):
        return None
    callee_symref = name_map[tok]
    j = _matching_paren_end(tokens, i + 2)
    callee_tokens = _callee_tokens(state, callee_symref)
    if not callee_tokens:
        return None
    budget[0] -= 1
    callee_path = callee_symref.split("::", 1)[0]
    # frob:invariant terminates reason="_substitute_calls checks 'depth >= state.cfg.inline_max_depth or budget[0] <= 0' and returns immediately without recursing once either bound is hit; depth+1 is passed here and budget[0] was decremented above" measure="state.cfg.inline_max_depth - depth strictly decreases each recursive descent, bounded below by 0"  # noqa: E501
    substituted = _substitute_calls(
        state,
        callee_path,
        callee_symref,
        list(callee_tokens),
        visited | {callee_symref},
        budget,
        depth + 1,
    )
    return substituted, j


# frob:ticket T-0361
def _matching_paren_end(tokens: list[str], open_idx: int) -> int:
    """Token index just past the `)` matching the `(` already consumed at
    `open_idx - 1` (i.e. `open_idx` is the first token INSIDE the call's
    parens), scanning for nested parens; split out of `_splice_call_site`'s
    paren-depth scan (T-0361)."""
    n = len(tokens)
    paren_depth = 1
    j = open_idx
    while j < n and paren_depth > 0:
        if tokens[j] == "(":
            paren_depth += 1
        elif tokens[j] == ")":
            paren_depth -= 1
        j += 1
    return j


def _inline_private_calls(
    state: _FpState, symref: str, body_tokens: tuple[str, ...]
) -> tuple[str, ...]:
    """Splice bounded call-graph-closure PRIVATE-helper bodies into `body_tokens`.

    Triage-only: reported spans continue to point at the real helper
    definitions (`ClonePair.region` is built from `SymbolRecord.span`, never
    touched here) -- this only changes what gets hashed/compared. Falls
    back to `body_tokens` unchanged when inlining is disabled or the
    symbol has no private callees.
    """
    if not state.cfg.inline_calls:
        return body_tokens
    path = symref.split("::", 1)[0]
    budget = [state.cfg.inline_max_nodes]
    substituted = _substitute_calls(
        state, path, symref, list(body_tokens), frozenset({symref}), budget, depth=0
    )
    return tuple(substituted)


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
        _add_chunk_nodes(chunk, nodes, adjacency)
    return tuple(adjacency), tuple(nodes)


def _add_chunk_nodes(
    chunk: tuple[str, ...], nodes: list[str], adjacency: list[tuple[int, int]]
) -> None:
    """Append one statement chunk's identifier nodes (def/use) plus their
    pairwise co-occurrence edges to the running graph (R5 fallback proxy)."""
    chunk_node_ids: list[int] = []
    for i, tok in enumerate(chunk):
        if not (_IDENT_RE.match(tok) and tok not in _KEYWORDS):
            continue
        is_def = i + 1 < len(chunk) and chunk[i + 1] == "="
        nodes.append("def" if is_def else "use")
        chunk_node_ids.append(len(nodes) - 1)
    _add_clique_edges(chunk_node_ids, adjacency)


def _add_clique_edges(node_ids: list[int], adjacency: list[tuple[int, int]]) -> None:
    """Add every pairwise edge among `node_ids` (a co-occurrence clique)."""
    for a in range(len(node_ids)):
        for b in range(a + 1, len(node_ids)):
            adjacency.append((node_ids[a], node_ids[b]))


def _find_block(node: Any) -> Any | None:
    """Depth-first search for the first function-body statement container
    under `node`, across every `_BLOCK_LABELS` grammar (T-0196: was
    Python-only `"block"`; `frob.lang.symbol_tree` labels mirror each
    grammar's own tree-sitter node `type` verbatim, so python/rust both use
    `"block"` but typescript/tsx use `"statement_block"` and c/cpp use
    `"compound_statement"` -- verified against each grammar's real parse
    tree, not assumed)."""
    if node.label in _BLOCK_LABELS:
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
    Covers every grammar `_BLOCK_LABELS` names (python, rust, typescript/
    tsx, c, cpp -- T-0196), not Python only.

    See `_statement_sequence_graph` for the def-use/control-flow edge rules.
    Every direct child of the body-statement container (`_find_block`'s
    match) is a statement (`frob.lang.export_tree` mirrors each grammar's
    own tree-sitter shape as-is and does not wrap simple statements --
    `assignment`, bare `call`, etc. -- in an `expression_statement` node
    for python; T-0117 found the opposite assumption silently dropped every
    assignment statement, collapsing unrelated functions to identical
    single-node graphs and WL-hash-colliding them). No filtering by
    statement-type label is needed or correct here.

    Returns `None` (caller falls back to `_build_dataflow_graph`) when no
    `_BLOCK_LABELS` node is found under `tree` (a non-function region, a
    body with no direct statements, or a grammar not yet listed in
    `_BLOCK_LABELS`) -- an honest "can't build a real graph here," not a
    silent wrong answer.
    """
    block = _find_block(tree)
    if block is None or not block.children:
        return None
    statements = block.children
    if not statements:
        return None
    return _statement_sequence_graph(statements)


def _statement_sequence_graph(
    statements: list[Any],
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]]:
    """Def-use cliques per statement plus sequencing edges between them, in order.

    Two edge kinds, both real (not proxied): **def-use** -- for an
    `assignment` node (bare or `expression_statement`-wrapped), targets
    (children before the `=` leaf) are labeled "def", the right-hand side
    "use", and every identifier within one statement is pairwise-connected;
    **control-flow** -- a sequencing edge from the last identifier node of
    statement *i* to the first identifier node of statement *i+1*, real
    adjacent-statement execution order the old co-occurrence proxy lacked.
    """
    labels: list[str] = []
    adjacency: list[tuple[int, int]] = []
    prev_last_idx: int | None = None

    for stmt in statements:
        stmt_ids = _statement_ids(stmt, labels)
        _add_clique_edges(stmt_ids, adjacency)
        if prev_last_idx is not None and stmt_ids:
            adjacency.append((prev_last_idx, stmt_ids[0]))
        if stmt_ids:
            prev_last_idx = stmt_ids[-1]

    return tuple(adjacency), tuple(labels)


def _labeled_ids(leaves: tuple[str, ...], role: str, labels: list[str]) -> list[int]:
    """Append `role` for each identifier leaf, returning the new node indices."""
    ids: list[int] = []
    for leaf in leaves:
        if _IDENT_RE.match(leaf) and leaf not in _KEYWORDS:
            labels.append(role)
            ids.append(len(labels) - 1)
    return ids


def _eq_index(children: list[Any]) -> int | None:
    """Index of the `=` leaf among an assignment node's children, or None."""
    for i, c in enumerate(children):
        if c.label == "=":
            return i
    return None


def _assignment_ids(assign: Any, labels: list[str]) -> list[int]:
    """Node ids for an assignment-shaped node (`_ASSIGNMENT_LABELS`):
    pre-`=` children are "def", the rest "use". Grammar-agnostic once the
    node has a direct `=` leaf child -- verified true for every label in
    `_ASSIGNMENT_LABELS`/`_DECLARATOR_LABELS` against each grammar's real
    parse tree."""
    eq_idx = _eq_index(assign.children)
    ids: list[int] = []
    for i, child in enumerate(assign.children):
        if child.label == "=":
            continue
        role = "def" if (eq_idx is not None and i < eq_idx) else "use"
        ids += _labeled_ids(_leaf_labels(child), role, labels)
    return ids


def _find_child_label(node: Any, wanted: frozenset[str]) -> Any | None:
    """First direct child of `node` whose label is in `wanted`, or None."""
    for child in node.children:
        if child.label in wanted:
            return child
    return None


def _statement_ids(stmt: Any, labels: list[str]) -> list[int]:
    """Node ids (with def/use labels appended to `labels`) for one statement.

    Three shapes, all real per-grammar node structure (T-0196, verified
    against each grammar's actual parse tree, not assumed):
    - `_ASSIGNMENT_LABELS` (python `assignment`, c/cpp/typescript
      `assignment_expression`, rust `let_declaration`) is handled whether
      it's the statement itself or wrapped one level under
      `expression_statement` (kept for robustness against other
      tree-sitter grammar builds that do wrap it).
    - `_DECLARATOR_LABELS` (typescript `variable_declarator` under a
      `lexical_declaration`/`variable_declaration` wrapper, c/cpp
      `init_declarator` under a `declaration` wrapper) carries the real
      `=` one level below the statement node -- descend into the first
      matching child rather than flattening the wrapper to one "use"
      clique.
    - Anything else (a bare expression statement, a control-flow header
      with no top-level assignment) falls back to "every identifier in
      this statement is a use" -- the same conservative default the
      original Python-only version used.
    """
    if stmt.label in _ASSIGNMENT_LABELS:
        return _assignment_ids(stmt, labels)
    if stmt.children and stmt.children[0].label in _ASSIGNMENT_LABELS:
        return _assignment_ids(stmt.children[0], labels)
    declarator = _find_child_label(stmt, _DECLARATOR_LABELS)
    if declarator is not None:
        return _assignment_ids(declarator, labels)
    return _labeled_ids(_leaf_labels(stmt), "use", labels)


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
    sim_result = _core._apted_similarity(
        tuple(labels_a), tuple(parents_a), tuple(labels_b), tuple(parents_b)
    )
    if sim_result.is_err:
        return None
    return sim_result.danger_ok
