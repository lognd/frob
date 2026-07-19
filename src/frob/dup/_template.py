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
"""

from __future__ import annotations

from pathlib import Path

from frob.dup import _core
from frob.dup._models import CloneBinding, ClonePair, CloneRegion, CloneTemplate
from frob.logging import get_logger

_log = get_logger(__name__)

_NodeArrays = tuple[tuple[str, ...], tuple[int, ...]]


# frob:doc docs/modules/dup.md#clone-template
def _region_tree(root: Path, region: CloneRegion) -> _NodeArrays | None:
    """`(labels, parents)` node arrays for `region`'s subtree, or `None` otherwise.

    Same recovery path `_pipeline._apted_similarity_for_pair` uses
    (`frob.lang.symbol_tree` + `_common.flatten_tree`), applied to a
    `CloneRegion` directly rather than a `RawSymbol` record pair.
    """
    from frob.lang import symbol_tree
    from frob.lang._common import flatten_tree

    path = region.ref.split("::", 1)[0]
    tree_result = symbol_tree(root / path, region.span)
    if tree_result.is_err:
        _log.debug("build_group_template: symbol_tree unavailable for %s", region.ref)
        return None
    labels, parents = flatten_tree(tree_result.danger_ok)
    return tuple(labels), tuple(parents)


def _children_of(parents: tuple[int, ...], index: int) -> list[int]:
    """Indices of `index`'s direct children in a `(labels, parents)` node array."""
    return [i for i, p in enumerate(parents) if p == index]


# frob:doc docs/modules/dup.md#clone-template
def _render_subtree(
    labels: tuple[str, ...], parents: tuple[int, ...], index: int
) -> str:
    """Compact `label(child, child, ...)` rendering of the subtree rooted at `index`.

    A structural skeleton over node-type labels, not literal source text --
    `frob.lang.TreeNode` carries no source span/text (see `CloneBinding`'s
    docstring for why this is an explicit, documented approximation).
    """
    children = _children_of(parents, index)
    if not children:
        return labels[index]
    rendered = ", ".join(_render_subtree(labels, parents, c) for c in children)
    return f"{labels[index]}({rendered})"


def _render_skeleton(labels: tuple[str, ...], parents: tuple[int, ...]) -> str:
    """Pretty-printed template text: shared nodes plus `$hole_N` at each divergence."""
    if not labels:
        return ""
    return _render_subtree(labels, parents, 0)


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

    Returns `None` (never raises) when any member's subtree cannot be
    recovered, `frob_core` is unavailable, or the hole-ceiling sanity check
    trips at any fold step -- callers report the plain `pairs` with no
    template in that case.
    """
    members = _distinct_members(pairs)
    if len(members) < 2:
        return None

    trees: list[_NodeArrays] = []
    for region in members:
        tree = _region_tree(root, region)
        if tree is None:
            return None
        trees.append(tree)

    running_labels, running_parents = trees[0]
    for labels, parents in trees[1:]:
        fold_result = _core.anti_unify(running_labels, running_parents, labels, parents)
        if fold_result.is_err:
            _log.debug(
                "build_group_template: fold refused (%s)", fold_result.danger_err
            )
            return None
        folded = fold_result.danger_ok
        running_labels, running_parents = folded.labels, folded.parents

    bindings: list[tuple[CloneBinding, ...]] = []
    for region, (labels, parents) in zip(members, trees, strict=True):
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
                    source_text=_render_subtree(labels, parents, node_idx),
                )
                for hole_id, node_idx in member_template.bindings_b
            )
        )

    holes = tuple(sorted({binding.hole for group in bindings for binding in group}))
    suggested_signature = "def _extracted({}): ...".format(
        ", ".join(f"hole_{h}" for h in holes)
    )
    return CloneTemplate(
        skeleton_text=_render_skeleton(running_labels, running_parents),
        holes=holes,
        bindings=tuple(bindings),
        suggested_signature=suggested_signature,
    )


__all__ = ["build_group_template"]
