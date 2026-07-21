"""Reverse-templating report: anti-unify a clone group into one readable
skeleton plus per-hole bindings (docs/modules/dup.md's "Reverse-templating
report" section; docs/modules/dup-sota-survey.md sec 4 design sketch).

Consumes only what T-0194's `anti_unify` kernel and `frob.lang.symbol_tree`
already produce -- no new detection, a synthesis stage over existing
`ClonePair`s. Never raises: every failure path (subtree unrecoverable,
`frob_core` missing, hole-ceiling sanity trip) returns `None` so a caller
falls back to the plain pairs with no template, per the survey's "Err back
to a plain ClonePair report with no template rather than emitting noise"
rule.

`CloneTemplate.skeleton_text` and `CloneBinding.source_text` render the
literal source characters (T-0327's `TreeNode.span` byte offsets sliced
against the original file), not a structural `label(child, ...)` skeleton
-- T-0481 closes the gap `TreeNode.span` was added for.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from frob.dup import _core
from frob.dup._models import CloneBinding, ClonePair, CloneRegion, CloneTemplate
from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.lang import TreeNode

_log = get_logger(__name__)

# labels/parents (the shape `frob_core.anti_unify` consumes) plus the
# parallel byte-span array `flatten_tree` itself does not carry.
_NodeArrays = tuple[tuple[str, ...], tuple[int, ...], tuple[tuple[int, int], ...]]

_HOLE_PREFIX = "$hole_"

# A hole's bound text is reused verbatim as a suggested-signature parameter
# name only when it is a single plain identifier -- never a literal,
# expression, or anything `def f({name}): ...` would not accept syntactically.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _flatten_with_spans(node: "TreeNode") -> _NodeArrays:
    """`(labels, parents, spans)` preorder arrays for a `frob.lang.TreeNode`.

    Same preorder walk as `frob.lang._common.flatten_tree`, plus the
    parallel `span` (byte offsets) array that module does not expose --
    kept local to this module since only reverse-templating needs spans
    (docs/modules/lang.md's `TreeNode.span` docstring).
    """
    labels: list[str] = []
    parents: list[int] = []
    spans: list[tuple[int, int]] = []

    def walk(n: "TreeNode", parent_idx: int) -> None:
        my_idx = len(labels)
        labels.append(n.label)
        parents.append(parent_idx)
        spans.append(n.span)
        for child in n.children:
            walk(child, my_idx)

    walk(node, -1)
    return tuple(labels), tuple(parents), tuple(spans)


def _region_tree(root: Path, region: CloneRegion) -> _NodeArrays | None:
    """`(labels, parents, spans)` node arrays for `region`'s subtree, or `None`.

    Same recovery path `_pipeline._apted_similarity_for_pair` uses
    (`frob.lang.symbol_tree`), flattened locally with `_flatten_with_spans`
    (rather than `frob.lang._common.flatten_tree`) so the byte-span array
    survives for literal source-text rendering.
    """
    from frob.lang import symbol_tree

    path = region.ref.split("::", 1)[0]
    tree_result = symbol_tree(root / path, region.span)
    if tree_result.is_err:
        _log.debug("build_group_template: symbol_tree unavailable for %s", region.ref)
        return None
    return _flatten_with_spans(tree_result.danger_ok)


def _region_source(root: Path, region: CloneRegion) -> bytes | None:
    """Raw file bytes backing `region`, or `None` if the file cannot be read.

    Spans are byte offsets into this exact content -- slicing must happen
    on bytes, then decode, not on a decoded `str` (offsets would drift on
    any multi-byte character).
    """
    path = region.ref.split("::", 1)[0]
    try:
        return (root / path).read_bytes()
    except OSError as exc:
        _log.debug(
            "build_group_template: cannot read source for %s (%s)", region.ref, exc
        )
        return None


def _children_of(parents: tuple[int, ...], index: int) -> list[int]:
    """Indices of `index`'s direct children in a `(labels, parents)` node array."""
    return [i for i, p in enumerate(parents) if p == index]


def _literal_text(source: bytes, span: tuple[int, int]) -> str:
    """Decode `source`'s exact byte slice for `span`, tolerating stale offsets."""
    return source[span[0] : span[1]].decode("utf-8", errors="replace")


def _render_literal(
    t_labels: tuple[str, ...],
    t_parents: tuple[int, ...],
    t_idx: int,
    m_parents: tuple[int, ...],
    m_spans: tuple[tuple[int, int], ...],
    m_idx: int,
    source: bytes,
) -> str:
    """Literal source-text rendering of template node `t_idx`, walked in lockstep
    against member node `m_idx` -- exact original characters, holes spliced in
    as `$hole_N` placeholders.

    Relies on `build_group_template`'s documented invariant that the folded
    template's shared (non-hole) nodes match every member's tree exactly, so
    a non-hole template node and its lockstep member node always have the
    same child count/order and can be walked together. A hole stops descent
    immediately (matching `anti_unify`'s own stop-at-hole behavior) and
    renders as its placeholder rather than the member's concrete text --
    `CloneBinding.source_text` is where that concrete text is reported.
    """
    label = t_labels[t_idx]
    if label.startswith(_HOLE_PREFIX):
        return label
    t_children = _children_of(t_parents, t_idx)
    full_span = m_spans[m_idx]
    if not t_children:
        return _literal_text(source, full_span)
    m_children = _children_of(m_parents, m_idx)
    pieces: list[str] = []
    cursor = full_span[0]
    # frob:invariant terminates reason="t_child ranges over children of t_idx in a `(labels, parents)` node array built from a real (acyclic, finite) folded template, so each t_child is a proper descendant of t_idx, never t_idx itself" measure="the subtree rooted at t_idx has strictly fewer nodes than the subtree rooted at its parent; bounded below by a single leaf node"  # noqa: E501
    for t_child, m_child in zip(t_children, m_children, strict=True):
        child_span = m_spans[m_child]
        pieces.append(_literal_text(source, (cursor, child_span[0])))
        pieces.append(
            _render_literal(
                t_labels, t_parents, t_child, m_parents, m_spans, m_child, source
            )
        )
        cursor = child_span[1]
    pieces.append(_literal_text(source, (cursor, full_span[1])))
    return "".join(pieces)


def _member_key(region: CloneRegion) -> tuple[str, tuple[int, int]]:
    """Identity of a clone-group member for dedup: `(ref, span)`."""
    return region.ref, region.span


def _distinct_members(pairs: tuple[ClonePair, ...]) -> list[CloneRegion]:
    """Every distinct `CloneRegion` referenced across `pairs`, first-seen order."""
    seen: dict[tuple[str, tuple[int, int]], CloneRegion] = {}
    for pair in pairs:
        for region in (pair.left, pair.right):
            seen.setdefault(_member_key(region), region)
    return list(seen.values())


def _hole_param_name(hole: int, bindings: tuple[tuple[CloneBinding, ...], ...]) -> str:
    """Suggested-signature parameter name for `hole`: the shared identifier text
    when every member's bound source agrees on one plain identifier (the
    survey's "reuse the identifier when both instances agree on a name"
    nicety), else the positional `hole_N` fallback.
    """
    texts = {
        binding.source_text
        for group in bindings
        for binding in group
        if binding.hole == hole
    }
    if len(texts) == 1:
        (text,) = texts
        if _IDENTIFIER_RE.match(text):
            return text
    return f"hole_{hole}"


# frob:doc docs/modules/dup.md#clone-template
def build_group_template(
    root: Path, pairs: tuple[ClonePair, ...]
) -> CloneTemplate | None:
    """Anti-unify a clone group's members into one shared skeleton + per-hole bindings.

    Folds Plotkin lgg incrementally across every distinct member found in
    `pairs` (member_0 lgg member_1, then that result lgg member_2, ...) so a
    group with more than two members still gets one shared template, not
    just a pairwise one -- the fold works because `anti_unify`'s `$hole_N`
    placeholder labels never coincide with a real node label, so folding a
    hole against real structure keeps it a hole. Per-member bindings are
    then recovered by re-anti-unifying the final folded template against
    each member individually: the folded template's shared nodes match
    that member's tree exactly (they came from structure every member
    shares) and its hole positions are visited in the same deterministic
    preorder order every time, so hole ids line up identically across all
    members without threading state through the fold.

    `skeleton_text` and `CloneBinding.source_text` render literal source
    characters, sliced from `TreeNode.span` byte offsets (T-0327/T-0481),
    not a structural `label(child, ...)` approximation.

    Returns `None` (never raises) when any member's subtree or source text
    cannot be recovered, `frob_core` is unavailable, or the hole-ceiling
    sanity check trips at any fold step -- callers report the plain `pairs`
    with no template in that case.
    """
    members = _distinct_members(pairs)
    if len(members) < 2:
        return None

    trees: list[_NodeArrays] = []
    sources: list[bytes] = []
    for region in members:
        tree = _region_tree(root, region)
        if tree is None:
            return None
        source = _region_source(root, region)
        if source is None:
            return None
        trees.append(tree)
        sources.append(source)

    running_labels, running_parents, _running_spans = trees[0]
    for labels, parents, _spans in trees[1:]:
        fold_result = _core.anti_unify(running_labels, running_parents, labels, parents)
        if fold_result.is_err:
            _log.debug(
                "build_group_template: fold refused (%s)", fold_result.danger_err
            )
            return None
        folded = fold_result.danger_ok
        running_labels, running_parents = folded.labels, folded.parents

    bindings: list[tuple[CloneBinding, ...]] = []
    for region, (labels, parents, spans), source in zip(
        members, trees, sources, strict=True
    ):
        member_result = _core.anti_unify(
            running_labels, running_parents, labels, parents
        )
        if member_result.is_err:
            _log.debug(
                "build_group_template: per-member re-derive refused (%s)",
                member_result.danger_err,
            )
            return None
        member_template = member_result.danger_ok
        bindings.append(
            tuple(
                CloneBinding(
                    hole=hole_id,
                    region=region,
                    source_text=_literal_text(source, spans[node_idx]),
                )
                for hole_id, node_idx in member_template.bindings_b
            )
        )

    _, skeleton_parents, skeleton_spans = trees[0]
    skeleton_text = (
        _render_literal(
            running_labels,
            running_parents,
            0,
            skeleton_parents,
            skeleton_spans,
            0,
            sources[0],
        )
        if running_labels
        else ""
    )

    # frob:waive PERF004 reason="runs once after the members loop, not per iteration"
    holes = tuple(sorted({binding.hole for group in bindings for binding in group}))
    frozen_bindings = tuple(bindings)
    suggested_signature = "def _extracted({}): ...".format(
        ", ".join(_hole_param_name(h, frozen_bindings) for h in holes)
    )
    return CloneTemplate(
        skeleton_text=skeleton_text,
        holes=holes,
        bindings=frozen_bindings,
        suggested_signature=suggested_signature,
    )


__all__ = ["build_group_template"]
