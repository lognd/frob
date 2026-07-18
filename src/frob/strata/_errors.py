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
    ParseFailed = "Source text failed to parse into a strata module"
    RefinementViolation = "A refine block failed a faithfulness check"
    MissingBound = (
        "A required std.infra bound/declaration is missing where no default is "
        "permitted (cache ttl/staleness absent or disagreeing; cdn provider trust "
        "or staleness absent)"
    )
    MissingInvalidation = "A cache has no invalidate_on edge for a mutable source"
    MutableUnbounded = "A cdn declares unlimited staleness over a non-immutable source"
    NegativeQuantity = (
        "A flow age/rate/size is negative; the age-propagation SCC soundness "
        "argument (docs/strata/kernel.md#age-propagation-semantics) requires "
        "every hop weight to be non-negative"
    )
    FrameViolation = (
        "A boundary phase's frame breaks its structural rule (admit/parse "
        "frames declaring entries, or a refuse frame naming a non-append-only "
        "node) -- docs/strata/boundary.md#v0-implementation (T-0069)"
    )
    CrossStoreAtomicity = (
        "An operation's `modifies {} on Err` strong guarantee names an "
        "atomic-via node that is neither the single store holding every Ok-"
        "frame target nor a declared coordinator -- distributed atomicity by "
        "wishful thinking is refused, never silently accepted "
        "(docs/strata/boundary.md#frames-and-failure-atomicity, T-0069)"
    )
    UnratedFlow = (
        "A scenario `scale` rewrite targets a flow with no declared rate; a "
        "surge multiplier on an undeclared rate is meaningless -- deny by "
        "default (docs/strata/kernel.md#scenario, T-0073)"
    )
    UnknownLogClass = (
        "An observe block's log class is not one of the fixed vocabulary "
        "{error_paths, state_transitions, boundary_crossings, crash_events} "
        "(docs/strata/policy.md#packs, T-0070)"
    )
