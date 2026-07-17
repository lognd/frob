"""Error vocabulary for the strata kernel (docs/strata/kernel.md).

One closed ErrorSet so the fault space of every kernel operation is
enumerable -- the property `docs/strata/evidence.md` relies on for
exhaustive fault injection.
"""

from __future__ import annotations

from typani.error_set import ErrorSet


# frob:doc docs/strata/kernel.md#data-models
class StrataError(ErrorSet):
    """Everything a kernel-model consumer must be prepared to handle."""

    UnknownLevel = "A lattice level name does not exist in the lattice"
    UnknownUnit = "A quantity uses a unit the kernel does not know"
    UnitMismatch = "Two quantities of different dimensions were compared"
    UnknownReference = "A fact references a node/flow id that is not declared"
    DuplicateId = "Two facts of the same kind share an id"
    MalformedLattice = "A lattice's covering pairs contain a cycle"
