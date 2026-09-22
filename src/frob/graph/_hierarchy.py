"""frob.graph._hierarchy -- generic parent/child descendants-of-any-depth
walk (T-3032, kernel decoupling: shared graph concerns).

MEASURED DUPLICATION this closes: the exact same parent/child adjacency
build plus any-depth BFS walk existed independently, hand-rolled, in TWO
places at filing time -- `frob.gates._milestone._children_by_parent`/
`_descendants_of` (MILE002's "OPEN descendant at any depth" check) and
`frob.tickets._evidence._open_descendant_ids` (the T-0715 done-transition
guard). Both modules' own docstrings already disclosed the duplication
("same walk shape `_open_descendant_ids` uses for its own open-descendant
check, kept as a local helper rather than importing that private one") --
this module is the fix: ONE generic, id-based implementation both callers
now delegate to, so there is exactly one BFS to get right, not two that
can drift apart.

Deliberately id-based (`Hashable`, not `Ticket`-typed): this is the
"parent/child hierarchy and ancestor walk" concern
`docs/design/ticket-strata-shared-graph-inventory.md` names as LIKELY
SHARED with strata (strata's own node hierarchies need the identical
any-depth descendants walk over a different node type entirely) -- a
generic function over ids is the shape a second, non-ticket consumer can
actually reuse without importing `frob.tickets.Ticket`.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from typing import TypeVar

from frob.logging import get_logger

_log = get_logger(__name__)

_Id = TypeVar("_Id", bound=Hashable)


# frob:doc docs/modules/graph.md#hierarchy-t-3032
def children_by_parent_id(
    items: Iterable[tuple[_Id, _Id | None]],
) -> dict[_Id, list[_Id]]:
    """`{parent_id: [direct child id, ...]}` over `items` (each a
    `(own_id, parent_id)` pair) -- the adjacency map `descendant_ids`
    walks. An item with `parent_id=None` (a root) contributes no entry
    keyed by itself here; it only ever appears as a VALUE if some other
    item names it as `parent_id`."""
    children: dict[_Id, list[_Id]] = {}
    for own_id, parent_id in items:
        if parent_id is not None:
            children.setdefault(parent_id, []).append(own_id)
    _log.debug(
        "children_by_parent_id: built adjacency for %d parent id(s)", len(children)
    )
    return children


# frob:doc docs/modules/graph.md#hierarchy-t-3032
def descendant_ids(root_id: _Id, children_of: Mapping[_Id, list[_Id]]) -> list[_Id]:
    """Every id reachable from `root_id` via `children_of`
    (`children_by_parent_id`'s output), at ANY depth, each visited
    exactly once. `root_id` itself is never included. Iterative
    frontier walk (no recursion, so no call-stack depth limit on a deep
    hierarchy) -- traversal order is not contractually meaningful to
    callers, only set membership and each-visited-once is."""
    frontier = [root_id]
    seen = {root_id}
    descendants: list[_Id] = []
    while frontier:
        current = frontier.pop()
        for child_id in children_of.get(current, ()):
            if child_id in seen:
                continue
            seen.add(child_id)
            descendants.append(child_id)
            frontier.append(child_id)
    return descendants
