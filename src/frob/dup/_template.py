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
# parallel byte-span array `flatten_tree` itself does not carry, plus
# (T-0495) the parallel tree-sitter field-name array (`TreeNode.field`)
# `_is_type_position` reads to classify a rust/c/cpp type-position hole
# that has no wrapper node, only a field name, distinguishing it.
_NodeArrays = tuple[
    tuple[str, ...],
    tuple[int, ...],
    tuple[tuple[int, int], ...],
    tuple[str | None, ...],
]

_HOLE_PREFIX = "$hole_"

# A hole's bound text is reused verbatim as a suggested-signature parameter
# name only when it is a single plain identifier -- never a literal,
# expression, or anything `def f({name}): ...` would not accept syntactically.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# T-0287: real per-grammar wrapper node types a type ANNOTATION sits under
# (verified directly against each grammar's own tree-sitter parse, same
# discipline as `frob.dup._pipeline._BLOCK_LABELS`/`_ASSIGNMENT_LABELS`):
# python wraps a parameter/return/variable annotation in a `type` node
# (`def f(a: int) -> int:` parses `int` as `type -> identifier`); typescript
# wraps the same shape in `type_annotation` (`x: number` parses `number` as
# `type_annotation -> predefined_type`). Rust/c/cpp place the type node as a
# direct, unwrapped sibling distinguished only by tree-sitter FIELD NAME
# (e.g. rust `parameter`'s `type` field) rather than a wrapper label --
# T-0495 closes that gap (see `_TYPE_FIELD_NAMES` below), extending
# `frob.lang.TreeNode` with the field-name info this rule needs.
_TYPE_WRAPPER_LABELS = frozenset({"type", "type_annotation"})

# T-0495: rust/c/cpp place a type node as a direct, unwrapped sibling
# distinguished only by tree-sitter FIELD NAME, never a wrapper label --
# verified directly against each grammar's own parse (docs/modules/dup.md
# #type-hole-classification-t-0287): rust's `parameter` node has a `type`
# field (`fn f(a: i32)` parses `i32` with field name "type" on a bare
# `primitive_type` sibling, next to the `pattern` field holding `a`) and
# its `function_item` node has a SEPARATE `return_type` field for `-> T`
# (rust's grammar does not reuse "type" for the return position, unlike
# c); c's `parameter_declaration`/`function_definition` both expose a
# `type` field directly on the type node for BOTH positions (`int add(int
# a)` parses the first `int` as field "type" on `function_definition`,
# the second as field "type" on `parameter_declaration` -- no separate
# return-type field name); cpp inherits c's grammar shape for this
# construct. Checking the node's OWN field name (not its parent's label)
# closes exactly this gap without disturbing python/typescript, whose
# type node also happens to carry field name "type" on ITS OWN wrapper
# (`_TYPE_WRAPPER_LABELS` already covers that case via the parent-label
# rule; the field-name rule below is a strict addition, not a
# replacement, since python/typescript's hole is the wrapper's unfielded
# inner child, not the wrapper node itself).
_TYPE_FIELD_NAMES = frozenset({"type", "return_type"})


def _is_type_position(
    labels: tuple[str, ...],
    parents: tuple[int, ...],
    fields: tuple[str | None, ...],
    node_idx: int,
) -> bool:
    """True if `node_idx` sits in a type-annotation position in the member
    tree `labels`/`parents`/`fields` came from -- the per-member half of
    T-0287's type-hole classification, extended by T-0495 to also
    recognize a field-name-only type position (rust/c/cpp).

    Two independent rules, either one qualifying: (1) python/typescript's
    shape -- the node's immediate PARENT is a real type-annotation
    wrapper node (`_TYPE_WRAPPER_LABELS`); (2) rust/c/cpp's shape -- the
    node's OWN tree-sitter field name (as seen from its parent) is a type
    field (`_TYPE_FIELD_NAMES`), with no wrapper node at all.
    """
    parent_idx = parents[node_idx]
    if parent_idx >= 0 and labels[parent_idx] in _TYPE_WRAPPER_LABELS:
        return True
    return fields[node_idx] in _TYPE_FIELD_NAMES


def _classify_type_vars(
    hole_node_idx: dict[int, list[int]],
    hole_source_texts: dict[int, list[str]],
    trees: list[_NodeArrays],
) -> dict[int, str]:
    """`{hole_id: type_var_name}` for every hole T-0287 classifies as a TYPE
    hole -- present only when EVERY group member's bound node for that hole
    sits in a type-annotation position (`_is_type_position`); a hole that is
    type-shaped in some members but a plain value in others is the
    "consistency guard" the ticket calls for and is left out of the
    returned mapping entirely (stays an ordinary value hole, never a
    half-right generic).

    Two type holes whose per-member bound-text sequence agrees exactly
    (the same concrete types recur at both positions, in the same member
    order -- e.g. a parameter annotation and the return annotation it
    matches) are assigned the SAME type variable rather than independent
    ones, since they are provably one abstracted type, not two. Names are
    assigned `T0`, `T1`, ... in first-appearance (ascending hole id) order
    so the mapping is deterministic across runs.
    """
    qualifying: list[int] = []
    for hole_id, node_indices in hole_node_idx.items():
        if len(node_indices) != len(trees):
            continue
        if all(
            _is_type_position(trees[m][0], trees[m][1], trees[m][3], node_idx)
            for m, node_idx in enumerate(node_indices)
        ):
            qualifying.append(hole_id)
    qualifying.sort()

    type_var_by_hole: dict[int, str] = {}
    text_seq_to_var: dict[tuple[str, ...], str] = {}
    for hole_id in qualifying:
        text_seq = tuple(hole_source_texts[hole_id])
        var_name = text_seq_to_var.get(text_seq)
        if var_name is None:
            var_name = f"T{len(text_seq_to_var)}"
            text_seq_to_var[text_seq] = var_name
        type_var_by_hole[hole_id] = var_name
    return type_var_by_hole


def _flatten_with_spans(node: "TreeNode") -> _NodeArrays:
    """`(labels, parents, spans, fields)` preorder arrays for a
    `frob.lang.TreeNode`.

    Same preorder walk as `frob.lang._common.flatten_tree`, plus the
    parallel `span` (byte offsets) array that module does not expose --
    kept local to this module since only reverse-templating needs spans
    (docs/modules/lang.md's `TreeNode.span` docstring) -- and (T-0495)
    the parallel `field` (tree-sitter field name) array `_is_type_position`
    reads to classify a rust/c/cpp type-position hole.
    """
    labels: list[str] = []
    parents: list[int] = []
    spans: list[tuple[int, int]] = []
    fields: list[str | None] = []

    def walk(n: "TreeNode", parent_idx: int) -> None:
        my_idx = len(labels)
        labels.append(n.label)
        parents.append(parent_idx)
        spans.append(n.span)
        fields.append(n.field)
        for child in n.children:
            walk(child, my_idx)

    walk(node, -1)
    return tuple(labels), tuple(parents), tuple(spans), tuple(fields)


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
    type_var_by_hole: dict[int, str] | None = None,
) -> str:
    """Literal source-text rendering of template node `t_idx`, walked in lockstep
    against member node `m_idx` -- exact original characters, holes spliced in
    as `$hole_N` placeholders, or (T-0287) the classified type-variable name
    (e.g. `T0`) for a hole `type_var_by_hole` names.

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
        if type_var_by_hole is not None:
            hole_id = int(label[len(_HOLE_PREFIX) :])
            type_var = type_var_by_hole.get(hole_id)
            if type_var is not None:
                return type_var
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
                t_labels,
                t_parents,
                t_child,
                m_parents,
                m_spans,
                m_child,
                source,
                type_var_by_hole,
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

    running_labels, running_parents, _running_spans, _running_fields = trees[0]
    for labels, parents, _spans, _fields in trees[1:]:
        fold_result = _core.anti_unify(running_labels, running_parents, labels, parents)
        if fold_result.is_err:
            _log.debug(
                "build_group_template: fold refused (%s)", fold_result.danger_err
            )
            return None
        folded = fold_result.danger_ok
        running_labels, running_parents = folded.labels, folded.parents

    bindings: list[tuple[CloneBinding, ...]] = []
    # T-0287: per-hole (node index, bound source text) across every member,
    # in member order -- `_classify_type_vars` needs the whole cross-member
    # view of a hole before it can classify it, so this is collected
    # alongside `bindings` in the same loop rather than re-derived later.
    hole_node_idx: dict[int, list[int]] = {}
    hole_source_texts: dict[int, list[str]] = {}
    for region, (labels, parents, spans, _fields), source in zip(
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
        member_bindings: list[CloneBinding] = []
        for hole_id, node_idx in member_template.bindings_b:
            source_text = _literal_text(source, spans[node_idx])
            member_bindings.append(
                CloneBinding(hole=hole_id, region=region, source_text=source_text)
            )
            hole_node_idx.setdefault(hole_id, []).append(node_idx)
            hole_source_texts.setdefault(hole_id, []).append(source_text)
        bindings.append(tuple(member_bindings))

    # T-0287: classify each hole as a shared type variable or a plain value
    # hole (see `_classify_type_vars`), then re-stamp every `CloneBinding`
    # with its resolved `type_var` -- done as a second pass since
    # classification needs every member's binding for a hole collected
    # first, not just the member being visited.
    type_var_by_hole = _classify_type_vars(hole_node_idx, hole_source_texts, trees)
    if type_var_by_hole:
        bindings = [
            tuple(
                binding.model_copy(
                    update={"type_var": type_var_by_hole.get(binding.hole)}
                )
                for binding in group
            )
            for group in bindings
        ]

    _, skeleton_parents, skeleton_spans, _skeleton_fields = trees[0]
    skeleton_text = (
        _render_literal(
            running_labels,
            running_parents,
            0,
            skeleton_parents,
            skeleton_spans,
            0,
            sources[0],
            type_var_by_hole,
        )
        if running_labels
        else ""
    )

    # frob:waive PERF004 reason="runs once after the members loop, not per iteration"
    holes = tuple(sorted({binding.hole for group in bindings for binding in group}))
    frozen_bindings = tuple(bindings)
    value_holes = [h for h in holes if h not in type_var_by_hole]
    suggested_signature = "def _extracted({}): ...".format(
        ", ".join(_hole_param_name(h, frozen_bindings) for h in value_holes)
    )
    type_params = tuple(
        sorted(set(type_var_by_hole.values()), key=lambda t: int(t[1:]))
    )
    if type_params:
        preamble = "".join(f'{t} = TypeVar("{t}")\n' for t in type_params)
        suggested_signature = preamble + suggested_signature
    return CloneTemplate(
        skeleton_text=skeleton_text,
        holes=holes,
        bindings=frozen_bindings,
        suggested_signature=suggested_signature,
        type_params=type_params,
    )


__all__ = ["build_group_template"]
