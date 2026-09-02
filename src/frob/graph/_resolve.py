"""Symbol reference resolution over a built `GraphSnapshot` (T-3411).

A leaf module: depends only on `frob.graph._models`, never on
`frob.graph.__init__`'s build-graph pipeline. This lets `frob.graph.lock`
import `resolve` here instead of back through the package `__init__`,
collapsing the `frob.graph` <-> `frob.graph.lock` import cycle (T-0362's
bottom-of-file ordering workaround is no longer needed). `resolve` is
re-exported from `frob.graph.__init__` to preserve its public surface.
"""

from __future__ import annotations

from typani import Err, Ok
from typani.result import Result

from frob.graph._models import GraphError, GraphSnapshot, SymbolRecord
from frob.logging import get_logger

__all__ = ["resolve"]

_log = get_logger(__name__)


# frob:doc docs/modules/graph.md#public-api
# frob:ticket T-0402
# frob:ticket T-3411
# frob:tests tests/test_graph.py::TestResolve.test_exact_qualname_wins_over_suffix_match
# frob:tests tests/test_graph.py::TestResolve.test_ambiguous_suffix_match
def resolve(snapshot: GraphSnapshot, ref: str) -> Result[SymbolRecord, GraphError]:
    """Resolve `ref`: exact `path::qualname`, else a unique qualname match,
    else a unique `.suffix` match.

    G10 (T-0402): exact-qualname and loose-suffix candidates used to be
    merged into one pool before counting, so a top-level `foo` and any
    `X.foo` collided into `AmbiguousSymbol` even though the bare `qualname
    == ref` hit was unambiguous on its own, and a `.suffix` hit could win
    over an exact qualname match that existed elsewhere in the pool. Exact
    qualname matches are now checked -- and count towards ambiguity --
    strictly before suffix matches are even considered.
    """
    exact = snapshot.symbols.get(ref)
    if exact is not None:
        return Ok(exact)

    qualname_matches = [
        record for record in snapshot.symbols.values() if record.id.qualname == ref
    ]
    if len(qualname_matches) == 1:
        return Ok(qualname_matches[0])
    if len(qualname_matches) > 1:
        _log.warning(
            "resolve(%r): ambiguous, %d qualname matches", ref, len(qualname_matches)
        )
        return Err(GraphError.AmbiguousSymbol)

    suffix = f".{ref}"
    suffix_matches = [
        record
        for record in snapshot.symbols.values()
        if record.id.qualname.endswith(suffix)
    ]
    if len(suffix_matches) == 1:
        return Ok(suffix_matches[0])
    if len(suffix_matches) > 1:
        _log.warning(
            "resolve(%r): ambiguous, %d suffix matches", ref, len(suffix_matches)
        )
        return Err(GraphError.AmbiguousSymbol)
    _log.debug("resolve(%r): no match", ref)
    return Err(GraphError.UnknownSymbol)
