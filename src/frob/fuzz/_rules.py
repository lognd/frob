"""FUZZ001/FUZZ002/FUZZ003: pure gate rules over already-loaded state
(docs/modules/fuzz.md).

These are plain functions, not wired into `frob.gates.run_gates` by this
change -- the coordinator does that wiring. Each takes only data (a
`GraphSnapshot`, the obligation list, and whatever side data its rule
needs) and returns `tuple[Violation, ...]`; none of them perform IO.
"""

from __future__ import annotations

from collections.abc import Mapping

from frob.fuzz._arbitrary import resolve
from frob.fuzz._models import FuzzObligation
from frob.gates._models import Severity, Violation
from frob.graph._models import EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)


def _split_ref(ref: str) -> tuple[str, int]:
    """`(file, line)` for a `path::qualname` ref; line is best-effort 0."""
    path = ref.split("::", 1)[0]
    return path, 0


# frob:doc docs/modules/fuzz.md#public-api
def FUZZ001(  # noqa: N802 - rule-id naming convention shared with frob.gates.invariants
    snapshot: GraphSnapshot, obligations: tuple[FuzzObligation, ...]
) -> tuple[Violation, ...]:
    """A fuzz-obligated function has no `kind="fuzz"` TESTS edge targeting it."""
    # frob:waive PERF003 reason="set comp then a membership-tested loop, not a join"
    fuzz_targets = {
        edge.target
        for edge in snapshot.edges
        if edge.kind == EdgeKind.TESTS and edge.attrs.get("kind") == "fuzz"
    }
    violations: list[Violation] = []
    for ob in obligations:
        if ob.ref in fuzz_targets:
            continue
        file, line = _split_ref(ob.ref)
        _log.debug("FUZZ001: %s (%s) has no fuzz test", ob.ref, ob.reason)
        violations.append(
            Violation(
                rule="FUZZ001",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"FUZZ001: {ob.ref} is fuzz-obligated ({ob.reason}) but has no "
                    f'frob:tests <symref> kind="fuzz" binding'
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/modules/fuzz.md#public-api
def FUZZ002(  # noqa: N802 - rule-id naming convention shared with frob.gates.invariants
    obligations: tuple[FuzzObligation, ...],
    param_types: Mapping[str, tuple[type, ...] | None],
) -> tuple[Violation, ...]:
    """A param type in an obligated signature has no derived/declared/registered
    generator.

    `param_types` maps a `ref` to its non-self parameter types, or `None`
    if the type set could not be introspected (a non-Python target, an
    import failure, or an unresolvable annotation) -- `None` refs are
    skipped rather than flagged, since we cannot distinguish "no generator"
    from "could not check" without a false positive.
    """
    violations: list[Violation] = []
    for ob in obligations:
        types = param_types.get(ob.ref)
        if types is None:
            _log.debug("FUZZ002: %s could not be introspected; skipping", ob.ref)
            continue
        for tp in types:
            if resolve(tp).is_ok:
                continue
            file, line = _split_ref(ob.ref)
            _log.debug("FUZZ002: %s param type %r has no generator", ob.ref, tp)
            violations.append(
                Violation(
                    rule="FUZZ002",
                    severity=Severity.ERROR,
                    file=file,
                    line=line,
                    message=(
                        f"FUZZ002: {ob.ref} has a parameter of type {tp!r} with no "
                        f"generator -- derive it (pydantic BaseModel), declare a "
                        f"__fuzz__() classmethod, or register(tp, strategy) in "
                        f"tests/strategies.py"
                    ),
                )
            )
    return tuple(violations)


# frob:doc docs/modules/fuzz.md#public-api
# frob:waive TEST005 reason="FUZZ003 87.5% branch cover, debt T-0160"
def FUZZ003(  # noqa: N802 - rule-id naming convention shared with frob.gates.invariants
    snapshot: GraphSnapshot,
    obligations: tuple[FuzzObligation, ...],
    stamp: Mapping[str, str] | None,
) -> tuple[Violation, ...]:
    """Fuzz stamp missing or stale (obligated target's body digest moved since the
    last recorded fuzz run)."""
    violations: list[Violation] = []
    recorded = stamp or {}
    for ob in obligations:
        record = snapshot.symbols.get(ob.ref)
        if record is None:
            _log.debug("FUZZ003: %s not in snapshot; skipping", ob.ref)
            continue
        stamped_digest = recorded.get(ob.ref)
        file, line = _split_ref(ob.ref)
        if stamped_digest is None:
            _log.debug("FUZZ003: %s has no fuzz stamp", ob.ref)
            violations.append(
                Violation(
                    rule="FUZZ003",
                    severity=Severity.ERROR,
                    file=file,
                    line=line,
                    message=(
                        f"FUZZ003: {ob.ref} has never been fuzzed; run "
                        f"`frob test --fuzz` to record a stamp"
                    ),
                )
            )
        elif stamped_digest != record.digests.body:
            _log.debug("FUZZ003: %s stamp is stale", ob.ref)
            violations.append(
                Violation(
                    rule="FUZZ003",
                    severity=Severity.ERROR,
                    file=file,
                    line=line,
                    message=(
                        f"FUZZ003: {ob.ref}'s fuzz stamp is stale (body changed since "
                        f"the last `frob test --fuzz` run)"
                    ),
                )
            )
    return tuple(violations)


__all__ = ["FUZZ001", "FUZZ002", "FUZZ003"]
