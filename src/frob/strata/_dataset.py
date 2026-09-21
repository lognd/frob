"""`std.dataset`: fine-grained sub-store data-region modeling (T-3964,
F-177, T-3942 item 3 / T-3919 item 5).

INVESTIGATED FIRST (T-0150 round-1 lesson, the same discipline T-3961's
sibling design note names): today `store` desugars to an ordinary
`Node` at elaborate time (no separate kernel `Store` class exists --
grepped `_models.py`, confirmed) and `carries()` (`_pii.py`) already
reads its tags PER-NODE, not globally -- so a fine-grained record
already CAN declare `carries()` independent of a coarser store's own
declaration TODAY, with zero new code, simply by being its own `Node`.
The design note's own body over-states the gap slightly: what is
actually missing is not "carries() can't be scoped independently" (it
already is, per-node) but a STRUCTURAL LINK from a fine-grained data
region back to the coarser store that contains it (so a scanner/gate
can tell "this is a sub-region of that store", not an unrelated node),
plus an `append_only` declaration a gate can observe.

Both are modeled as plain `Node.attrs` entries (charter law 1: no new
kernel primitive), the SAME attr-desugar convention `pii=`/`code=`/
T-3961's `derived_from:`/`trust_identity:` already use -- ZERO
`strata-core` grammar change (no new `dataset` keyword; an existing
`node` declaration IS a dataset the moment it carries a `parent_store=`
attr):

- `parent_store=<node-id>`: names the store `Node` this dataset is a
  sub-region of. A dataset's own `carries()`/`may`/etc. are already
  independent by construction (it is its own `Node`) -- this attr only
  adds the CONTAINMENT fact a gate can join against.
- `append_only`: a bare flag (mirrors T-3961's `no_pii`/`trust_identity`
  bare-and-keyed attr convention) declaring this dataset/node append-only.

Two structural checks (SYS118, the next free id after SYS100-117 across
every currently in-flight rule claim -- T-4113's SYS114/SYS115 and
T-4612's SYS116/SYS117 are both held-for-landing but not yet on `main`/
`dev` at implementation time, so this module's own consumer picks the
id one past the highest one any in-flight ticket has claimed):

- SYS118 (dangling parent_store reference): a `parent_store=<id>` attr
  naming a node id that does not exist anywhere in the model -- a typo'd
  or stale reference, deny-by-default the same shape SYS101/SYS113 take
  on a broken structural reference.
"""
# frob:ticket T-3964

from __future__ import annotations

from frob.logging import get_logger

from ._models import KernelModel, Node

_log = get_logger(__name__)

#: Node attr key a `parent_store=<node-id>` containment statement uses
#: (T-3964's accepted design): names the store `Node` this dataset is a
#: fine-grained sub-region of. Private -- see `node_parent_store`'s own
#: `frob:doc` anchor for the public-surface documentation this backs.
_PARENT_STORE_PREFIX = "parent_store="

#: Node attr a dataset/node declares to mark itself append-only (T-3964's
#: accepted design), the same bare-flag convention T-3961's
#: `trust_identity`/T-4073's `no_pii` already use. Private -- see
#: `node_is_append_only`'s own `frob:doc` anchor.
_APPEND_ONLY_ATTR = "append_only"


# frob:doc docs/strata/dataset-construct.md#parent_store
# frob:tests tests/test_dataset_construct.py::TestDatasetAttrParsing.test_node_parent_store_parses_attr  # noqa: E501
def node_parent_store(node: Node) -> str | None:
    """The `parent_store=<node-id>` this dataset `node` declares, or
    `None` if it declares none (i.e. `node` is not a dataset sub-region
    of any store)."""
    for attr in node.attrs:
        if attr.startswith(_PARENT_STORE_PREFIX):
            return attr[len(_PARENT_STORE_PREFIX) :]
    return None


# frob:doc docs/strata/dataset-construct.md#parent_store
# frob:tests tests/test_dataset_construct.py::TestDatasetAttrParsing.test_node_is_dataset_true_with_parent_store  # noqa: E501
def node_is_dataset(node: Node) -> bool:
    """Whether `node` declares a `parent_store=` attr at all -- the
    marker that this `Node` is a dataset sub-region (module docstring:
    an existing `node` declaration IS a dataset the moment it carries
    this attr, no separate keyword)."""
    return node_parent_store(node) is not None


# frob:doc docs/strata/dataset-construct.md#append_only
# frob:tests tests/test_dataset_construct.py::TestDatasetAttrParsing.test_node_is_append_only_true  # noqa: E501
def node_is_append_only(node: Node) -> bool:
    """Whether `node` declares the bare `append_only` attr."""
    return _APPEND_ONLY_ATTR in node.attrs


# frob:doc docs/strata/dataset-construct.md#sys118-dangling-parent_store-reference
# frob:enforces CHK-GATE-SYS118
# frob:tests tests/test_dataset_construct.py::TestSys118DanglingParentStore.test_dangling_parent_store_fires_sys118  # noqa: E501
def check_dangling_parent_store(model: KernelModel) -> tuple[str, ...]:
    """SYS118: every `parent_store=<id>` attr names a node id that
    actually exists in `model` -- deny-by-default on a typo'd or stale
    reference, the same structural-reference shape SYS101/SYS113 take.

    Returns human-readable finding strings (kept dependency-free of any
    `Violation`/`PiiViolation` model -- callers, e.g. a future gate
    consumer, wrap these as needed; mirrors how `_pii.py`'s checks stay
    strata-model-shaped rather than gate-shaped)."""
    node_ids = {n.id for n in model.nodes}
    findings: list[str] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        parent = node_parent_store(node)
        if parent is None or parent in node_ids:
            continue
        _log.warning(
            "dataset: SYS118 node %s declares parent_store=%r, which does not exist",
            node.id,
            parent,
        )
        findings.append(
            f"node {node.id} declares parent_store={parent!r}, which does "
            "not exist in this model"
        )
    return tuple(findings)


__all__ = [
    "check_dangling_parent_store",
    "node_is_append_only",
    "node_is_dataset",
    "node_parent_store",
]
