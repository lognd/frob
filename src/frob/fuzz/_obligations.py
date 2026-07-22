"""Which symbols owe a fuzz test, under the configured enforcement mode
(docs/modules/fuzz.md).

`obligations` is pure: it reads only the already-built `GraphSnapshot` and
the `[fuzz]` policy, never the filesystem or the interpreter, so a caller
can compute obligations without importing a single project module.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/fuzz/_obligations.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from frob.fuzz._models import FuzzEnforce, FuzzObligation, FuzzPolicy
from frob.graph._models import EdgeKind, GraphSnapshot, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)


def _invariant_anchored(snapshot: GraphSnapshot) -> tuple[FuzzObligation, ...]:
    """Every symbol carrying an outgoing `frob:invariant` anchor edge."""
    seen: dict[str, str] = {}
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.INVARIANT:
            continue
        if edge.src in seen:
            continue
        seen[edge.src] = f"invariant {edge.target} anchor"
    return tuple(FuzzObligation(ref=ref, reason=reason) for ref, reason in seen.items())


def _public(snapshot: GraphSnapshot) -> tuple[FuzzObligation, ...]:
    """Every public function/method.

    Per-parameter generatability (does every param type actually resolve
    via `frob.fuzz.resolve`) is NOT checked here -- that requires importing
    the target's module, which would make this function impure. FUZZ002
    does that check separately, over the obligations this function returns,
    using a best-effort dynamic import (`frob.fuzz._signatures`).
    """
    obligations: list[FuzzObligation] = []
    for record in snapshot.symbols.values():
        if not record.public or record.kind not in (
            SymbolKind.FUNCTION,
            SymbolKind.METHOD,
        ):
            continue
        obligations.append(FuzzObligation(ref=record.symref, reason="public"))
    return tuple(obligations)


# frob:doc docs/modules/fuzz.md#public-api
def obligations(
    snapshot: GraphSnapshot, policy: FuzzPolicy
) -> tuple[FuzzObligation, ...]:
    """Pure: which symbols owe fuzzing under `policy.enforce`."""
    if policy.enforce == FuzzEnforce.OFF:
        _log.debug("obligations: enforce=off, no obligations")
        return ()
    if policy.enforce == FuzzEnforce.PUBLIC:
        result = _public(snapshot)
    else:
        result = _invariant_anchored(snapshot)
    _log.info(
        "obligations: enforce=%s -> %d obligated symbol(s)",
        policy.enforce.value,
        len(result),
    )
    return result


__all__ = ["obligations"]
