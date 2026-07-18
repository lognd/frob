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
    MissingTimeout = (
        "A flow into a node with an `on crash` contract has no declared "
        "timeout -- the no-hang check: every synchronous caller of a "
        "crashable component must declare a timeout, never silently block "
        "forever (docs/strata/boundary.md"
        "#crash-contracts-and-error-totality-adjacent-claims, T-0074)"
    )
    IncompatibleTimeout = (
        "A flow's declared timeout is shorter than its crashable destination's "
        "restart+retry bound -- the caller would give up before recovery can "
        "plausibly complete, which is the same silent-hang class the no-hang "
        "check exists to kill (docs/strata/boundary.md"
        "#crash-contracts-and-error-totality-adjacent-claims, T-0074)"
    )
    IncompatibleContainmentBound = (
        "A breach contract's detection SLA exceeds its revocation bound, or a "
        "declared credential_age outlives the revocation window -- containment "
        "must complete before the credential's own lifetime runs out, and "
        "detection must land before revocation, else the compromise persists "
        "past its own contract (docs/strata/kernel.md#scenario, T-0076)"
    )
    MissingRevocation = (
        "A credential (std.secrets) has no revocation edge -- the same "
        "deny-by-default rule as MissingInvalidation: credential revocation "
        "and cache invalidation are the same age-collapse rule "
        "(docs/strata/kernel.md#age-propagation-semantics, T-0082) -- no "
        "credential without a revocation edge, no cache without an "
        "invalidate_on edge"
    )
    AmbiguousCodeBinding = (
        "A source file matches the `code=` glob of more than one node -- "
        "tier-2 code binding requires a partition, since two-way binding "
        "(charter law 5) needs exactly one node to attest for any given file "
        "(docs/strata/surface.md#code-binding-tier-2-v0-implementation, T-0078)"
    )
    MissingEndorsement = (
        "A deploy contract's endorsement_chain names a boundary id that is "
        "not declared in the model -- an upstream endorsement chain that "
        "points nowhere is a dangling promise, not a silently accepted one "
        "(docs/strata/surface.md#std-deploy, T-0083)"
    )
    IncompatibleEndorsement = (
        "A deploy contract's endorsement_chain names a boundary whose "
        "direction is not endorse -- only an endorse boundary raises "
        "integrity, so a declassify (or any other) boundary cannot stand in "
        "for the review/build/admit endorsement a deploy requires "
        "(docs/strata/surface.md#std-deploy, T-0083)"
    )
    NativeExtensionUnavailable = (
        "The strata_core native extension is not installed (a standalone "
        "`uv tool install frob` with no natives) -- .strata parsing and "
        "kernel-fact propagation degrade to this typed error instead of "
        "crashing with an unhandled ImportError, matching frob.lang's "
        "guarded-import pattern (T-0133, T-0134)"
    )
