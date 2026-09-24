"""frob.gates._invariant_level -- INVLVL001: an invariant verified below
its paired V-model level (T-3008, T-3004 section 7).

INV001/INV002 (`frob.gates._inv`) already check that a declared invariant
has standing evidence and a code anchor -- but neither checks WHERE that
evidence sits in the V-model's left/right level pairing (T-3004 section
1): a `system-design`-level invariant "verified" only by a
`component-unit-test`-tagged evidence entry passes INV001 today even
though it was never actually exercised at the level it claims. T-3008
gave `Invariant` two new OPTIONAL fields for this (`level`,
`evidence_levels` -- see that class's own docstring); this module is the
enforcement half: INVLVL001 fires when a TAGGED evidence entry's level is
not the invariant's own paired level, and stays silent for any entry left
untagged (schema-only additions never retroactively break an existing
`invariants/*.md` file, same posture VMOD001/MSCLOSE001 take toward a
repo with no vmodel graph of its own yet).

SEVERITY: WARN, matching INV003's own precedent (`docs/modules/gates.md`
note above `### INV003`) -- this is a NEW best-effort family over
optional, not-yet-widely-adopted fields, not a retrofit of every existing
invariant to a hard ERROR gate.
"""

# frob:ticket T-3008

from __future__ import annotations

from frob.gates._models import Severity, Violation
from frob.gates.invariants import INVARIANT_PAIRED_TEST_LEVEL, Invariant
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/gates.md#invlvl001-t-3008
# frob:enforces CHK-GATE-INVLVL001
def invariant_level_gate(invariants: tuple[Invariant, ...]) -> tuple[Violation, ...]:
    """INVLVL001 (WARN): for every invariant declaring a `level`, every
    `evidence_levels`-tagged evidence entry whose declared level is not
    that level's paired test level (`INVARIANT_PAIRED_TEST_LEVEL`).

    Opt-in per invariant AND per evidence entry: an invariant with no
    `level` is never checked (nothing to pair against); an evidence entry
    present in `evidence` but absent from `evidence_levels` is silently
    skipped (untagged, no level claim to verify) -- the same "declaration
    carries the claim, absence is not a violation" posture the V-model
    kernel's own required-attr design takes (docs/strata/vmodel.md's
    T-3044 H3 note)."""
    violations: list[Violation] = []
    for inv in invariants:
        if inv.level is None:
            continue
        paired = INVARIANT_PAIRED_TEST_LEVEL.get(inv.level)
        if paired is None:
            # Unreachable in practice -- load_invariants already refuses
            # an unknown `level` at parse time -- but a defensive skip
            # here is cheaper than a KeyError crashing the whole gate run
            # over one malformed-in-a-new-way file.
            _log.warning(
                "invariant_level_gate: %s declares unknown level %r, skipping",
                inv.id,
                inv.level,
            )
            continue
        for item, tagged_level in inv.evidence_levels.items():
            if tagged_level == paired:
                continue
            _log.debug(
                "INVLVL001: %s declared level %r (paired %r) but evidence %r "
                "is tagged %r",
                inv.id,
                inv.level,
                paired,
                item,
                tagged_level,
            )
            violations.append(
                Violation(
                    rule="INVLVL001",
                    severity=Severity.WARN,
                    file=inv.path,
                    line=0,
                    message=(
                        f"INVLVL001: {inv.id} is declared at level {inv.level!r} "
                        f"(paired test level {paired!r}), but evidence {item!r} "
                        f"is tagged {tagged_level!r} -- verify it at the paired "
                        f"level, or correct the evidence_levels tag"
                    ),
                )
            )
    return tuple(violations)


__all__ = ["invariant_level_gate"]
