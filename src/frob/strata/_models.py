"""Kernel data model for strata (docs/strata/kernel.md).

The six primitives every surface construct desugars to (charter law 1),
as frozen pydantic models so a whole `KernelModel` compares, hashes, and
caches by value -- the same identity-of-value contract as `frob.lang`.
The prover (`_facts.py`, `_claims.py`) consumes these and nothing else:
no vocabulary word (cache, secret, deploy) may appear in this module.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError

_log = get_logger(__name__)


# frob:doc docs/strata/kernel.md#data-models
class Lattice(BaseModel):
    """A finite partial order given by covering pairs, e.g. trust or data labels."""

    model_config = ConfigDict(frozen=True)

    name: str
    order: tuple[tuple[str, str], ...]  # (lower, higher) covering pairs

    def elements(self) -> frozenset[str]:
        """Every level named by the covering pairs."""
        # frob:doc docs/strata/kernel.md#data-models
        return frozenset(x for pair in self.order for x in pair)

    def leq(self, low: str, high: str) -> Result[bool, StrataError]:
        """Whether `low <= high` in the reflexive-transitive closure.

        Unknown level names are a model error, not False: a typo in a
        trust level must fail loudly, never silently deny.
        """
        # frob:doc docs/strata/kernel.md#data-models
        known = self.elements()
        for level in (low, high):
            if level not in known:
                _log.warning("lattice %s: unknown level %r", self.name, level)
                return Err(StrataError.UnknownLevel)
        if low == high:
            return Ok(True)
        frontier = {low}
        seen: set[str] = set()
        while frontier:
            current = frontier.pop()
            seen.add(current)
            for lower, higher in self.order:
                if lower == current and higher not in seen:
                    if higher == high:
                        return Ok(True)
                    frontier.add(higher)
        return Ok(False)


# frob:doc docs/strata/kernel.md#lattice-semantics
TRUST = Lattice(
    name="trust",
    order=(("foreign", "authenticated"), ("authenticated", "trusted")),
)

# frob:doc docs/strata/kernel.md#lattice-semantics
LABELS = Lattice(
    name="labels",
    order=(("Public", "Internal"), ("Internal", "Pii"), ("Pii", "Secret")),
)

# Unit table: unit -> (dimension, factor to the dimension's base unit).
_UNITS: dict[str, tuple[str, float]] = {
    "s": ("time", 1.0),
    "ms": ("time", 1e-3),
    "min": ("time", 60.0),
    "h": ("time", 3600.0),
    "d": ("time", 86400.0),
    "B": ("size", 1.0),
    "KiB": ("size", 1024.0),
    "MiB": ("size", 1024.0**2),
    "GiB": ("size", 1024.0**3),
    "/s": ("rate", 1.0),
    "req/s": ("rate", 1.0),
    "tx/s": ("rate", 1.0),
    "/min": ("rate", 1.0 / 60.0),
    "req/min": ("rate", 1.0 / 60.0),
    "%": ("percent", 1.0),
    "": ("scalar", 1.0),
}


# frob:doc docs/strata/kernel.md#data-models
class Quantity(BaseModel):
    """A number with a unit; comparisons across dimensions are errors, not False."""

    model_config = ConfigDict(frozen=True)

    value: float
    unit: str

    def dimension(self) -> Result[str, StrataError]:
        """The unit's dimension (time/size/rate/percent/scalar)."""
        # frob:doc docs/strata/kernel.md#data-models
        entry = _UNITS.get(self.unit)
        if entry is None:
            _log.warning("unknown unit %r", self.unit)
            return Err(StrataError.UnknownUnit)
        return Ok(entry[0])

    def base_value(self) -> Result[float, StrataError]:
        """The value converted to its dimension's base unit."""
        # frob:doc docs/strata/kernel.md#data-models
        entry = _UNITS.get(self.unit)
        if entry is None:
            _log.warning("unknown unit %r", self.unit)
            return Err(StrataError.UnknownUnit)
        return Ok(self.value * entry[1])

    def leq(self, other: Quantity) -> Result[bool, StrataError]:
        """Whether self <= other after conversion to a shared base unit."""
        # frob:doc docs/strata/kernel.md#data-models
        dim_a = self.dimension()
        if dim_a.is_err:
            return Err(dim_a.danger_err)
        dim_b = other.dimension()
        if dim_b.is_err:
            return Err(dim_b.danger_err)
        if dim_a.danger_ok != dim_b.danger_ok:
            _log.warning(
                "unit mismatch: %s%s vs %s%s",
                self.value,
                self.unit,
                other.value,
                other.unit,
            )
            return Err(StrataError.UnitMismatch)
        return Ok(self.base_value().danger_ok <= other.base_value().danger_ok)


# frob:doc docs/strata/kernel.md#data-models
class Capacity(BaseModel):
    """A node's declared service ability: rate per replica and replica range."""

    model_config = ConfigDict(frozen=True)

    service_rate: Quantity
    replicas_min: int = 1
    replicas_max: int = 1

    @property
    def singleton(self) -> bool:
        """True when the node can never scale past one replica."""
        # frob:doc docs/strata/kernel.md#data-models
        return self.replicas_max == 1


#: Flow attr marking at-least-once delivery; its dst must carry `_IDEMPOTENT`.
#: Shared between `_facts.py` (the ordinary queue-delivery join) and
#: `_crash.py` (the crash-retry join, T-0074) so both paths report the
#: same diagnostic through the same code (charter law -- no duplication).
_AT_LEAST_ONCE = "delivery=at_least_once"
#: Node attr that discharges the at-least-once obligation.
_IDEMPOTENT = "idempotent"


# frob:doc docs/strata/boundary.md#crash-contracts-and-error-totality-adjacent-claims
class CrashContract(BaseModel):
    """A node's `on crash { restart within t; inflight fail retriable within t';
    state recovered from X }` contract (docs/strata/boundary.md, T-0074).

    `restart` is the recovery-time bound (component comes back within
    `t`); `retry` is optional and, when present, means inflight requests
    fail retriable rather than hanging forever -- this is the fact that
    turns every synchronous caller into an at-least-once sender, which is
    exactly the standard delivery-semantics join `_facts.py` already
    checks. `recovers_from` optionally names the node/store state is
    restored from on restart (validated as a real reference downstream,
    `_crash.py`).
    """

    model_config = ConfigDict(frozen=True)

    restart: Quantity
    retry: Quantity | None = None
    recovers_from: str | None = None


# frob:doc docs/strata/kernel.md#scenario
class BreachContract(BaseModel):
    """A node's `on breach { detect within t; revoke within t'; recovers_via X }`
    contract (docs/strata/kernel.md#scenario, T-0076).

    `detect` and `revoke` are the containment SLA: how long a compromise
    of this node may go unnoticed, and how long revoking its credentials
    / access may take once detected -- both mandatory, since a detection
    bound with no revocation bound (or vice versa) is half a containment
    story. `credential_age` optionally bounds how long any credential
    this node holds may live; a credential that outlives the revocation
    window stays valid past containment, which `_breach.py` refuses
    closed the same way the charter refuses any age without an
    invalidation edge. `recovers_via` optionally names the node whose
    path back to this one must be independent of this node's blast
    radius (`_breach.py` auto-generates the `Independent` claim that
    checks it).
    """

    model_config = ConfigDict(frozen=True)

    detect: Quantity
    revoke: Quantity
    credential_age: Quantity | None = None
    recovers_via: str | None = None


# frob:doc docs/strata/surface.md#std-deploy
class CanaryStage(BaseModel):
    """One staged rollout step: promote to `level` after `bake` with no abort.

    `level` is the trust level this stage promotes the deploying node to --
    canary is modeled as staged trust escalation (docs/strata/surface.md
    #std-deploy, T-0083), reusing the existing `SetTrust` scenario rewrite
    rather than inventing a parallel rollout-percentage mechanism.
    `max_error_rate` is an optional abort predicate: an observed error rate
    above this bound at this stage means the rollout does not proceed --
    left opaque (checked by the caller/CI, not the kernel) exactly like
    `Boundary.predicate`, since v0 has no live-metric feed into the prover.
    """

    model_config = ConfigDict(frozen=True)

    level: str
    bake: Quantity
    max_error_rate: Quantity | None = None


# frob:doc docs/strata/surface.md#std-deploy
class DeployContract(BaseModel):
    """A node's `on deploy { canary { ... }; endorsed_by X; rollback within t }`
    contract (docs/strata/surface.md#std-deploy, T-0083).

    `stages` is the canary schedule, evaluated in declaration order as one
    staged-trust-escalation scenario per stage. `endorsement_chain` names
    the upstream `Boundary` ids (review/build/admit) an artifact must have
    already crossed before this node may deploy it -- validated to exist
    and to be `endorse`-directed, else the contract fails closed
    (`_deploy.py`, crash-contract precedent T-0074). `rollback_budget`
    bounds how long reverting a bad deploy may take; desugars to an
    auto-generated bounded-recovery scenario (node loss, the same
    `RemoveNode` rewrite `on crash` uses) so a rollback is checked exactly
    like any other total-loss counterfactual, never a parallel evaluator.
    """

    model_config = ConfigDict(frozen=True)

    stages: tuple[CanaryStage, ...]
    endorsement_chain: tuple[str, ...]
    rollback_budget: Quantity


# frob:doc docs/strata/kernel.md#data-models
class Node(BaseModel):
    """A place that holds state or runs computation (component, store, principal...)."""

    model_config = ConfigDict(frozen=True)

    id: str
    trust: str
    clearance: str = "Secret"  # max data label allowed to rest here
    may: tuple[str, ...] = ()  # capability atoms, e.g. "net.out:stripe.com"
    attrs: tuple[str, ...] = ()  # opaque node attributes, e.g. "idempotent"
    capacity: Capacity | None = None
    residence: str | None = None  # host/zone/region atom for scenario rewrites
    crash: CrashContract | None = None  # `on crash { ... }` contract, T-0074
    breach: BreachContract | None = None  # `on breach { ... }` contract, T-0076
    deploy: DeployContract | None = None  # `on deploy { ... }` contract, T-0083


# frob:doc docs/strata/kernel.md#data-models
class Outcome(StrEnum):
    """The outcome axis a conditional flow may be predicated on."""

    OK = "ok"
    ERR = "err"


# frob:doc docs/strata/kernel.md#data-models
class FlowCondition(BaseModel):
    """The kernel's one graph extension: a flow gated on outcome or phase."""

    model_config = ConfigDict(frozen=True)

    outcome: Outcome | None = None
    phase: str | None = None


# frob:doc docs/strata/kernel.md#data-models
class Flow(BaseModel):
    """Directed movement of anything between two nodes, label and metrics attached."""

    model_config = ConfigDict(frozen=True)

    id: str
    src: str
    dst: str
    label: str = "Public"  # payload data label
    rate: Quantity | None = None
    age: Quantity | None = None  # staleness this hop adds along a read path
    size: Quantity | None = None
    transport: tuple[str, ...] = ()  # e.g. "tls>=1.3", "aead"
    attrs: tuple[str, ...] = ()  # e.g. "delivery=at_least_once"
    condition: FlowCondition | None = None
    timeout: Quantity | None = None  # caller's declared timeout, T-0074 no-hang check


# frob:doc docs/strata/kernel.md#data-models
class BoundaryDirection(StrEnum):
    """Endorse raises integrity of a flow; declassify lowers its confidentiality."""

    ENDORSE = "endorse"
    DECLASSIFY = "declassify"


# frob:doc docs/strata/kernel.md#data-models
class Boundary(BaseModel):
    """The only legal site of label/trust change, attached to exactly one flow."""

    model_config = ConfigDict(frozen=True)

    id: str
    flow_id: str
    direction: BoundaryDirection
    from_level: str
    to_level: str
    predicate: str = ""  # opaque justification, e.g. "jwt_verified"
    obligations: tuple[str, ...] = ()  # evidence refs discharged in tier 3


# frob:doc docs/strata/kernel.md#data-models
class Metric(StrEnum):
    """The propagated quantities a bound may constrain."""

    AGE = "age"
    RATE = "rate"
    LATENCY = "latency"
    SIZE = "size"
    UTILIZATION = "utilization"


# frob:doc docs/strata/kernel.md#data-models
class NoFlow(BaseModel):
    """Claim body: no influence path from src to dst survives the closure."""

    model_config = ConfigDict(frozen=True)

    src: str
    dst: str


# frob:doc docs/strata/kernel.md#data-models
class Reach(BaseModel):
    """Claim body: a required path from src to dst exists (audit, revocation...)."""

    model_config = ConfigDict(frozen=True)

    src: str
    dst: str


# frob:doc docs/strata/kernel.md#data-models
class BoundClaim(BaseModel):
    """Claim body: a propagated metric at target stays within limit."""

    model_config = ConfigDict(frozen=True)

    metric: Metric
    target: str  # node or flow id
    limit: Quantity


# frob:doc docs/strata/kernel.md#claim-forms-and-their-decision-procedures
class Independent(BaseModel):
    """Claim body: the src->dst path shares no node with avoid's reach closure.

    `independent(p, n)` (docs/strata/kernel.md#claim-forms-and-their-
    decision-procedures): recovery-path independence for a breach --
    `avoid` is typically the compromised node itself, so the claim is
    "the path a recovery mechanism takes to reach back into this node
    touches nothing this node's own compromise could already reach."
    """

    model_config = ConfigDict(frozen=True)

    src: str
    dst: str
    avoid: str


# frob:doc docs/strata/kernel.md#claim-forms-and-their-decision-procedures
class SetEquality(BaseModel):
    """Claim body: `readers(target) == expected`, an exact-set closure equality.

    `readers(x) == S` (docs/strata/kernel.md#claim-forms-and-their-decision-
    procedures): the forward influence closure from `target` (through
    barriers, same traversal `reach` uses) must equal `expected` exactly --
    not a subset, not a superset. Reserved for `std.secrets` (T-0082): a
    credential's authorized reader set is declared once and the closure
    engine, not a human, proves nobody extra can reach it and nobody
    declared is unreachable.
    """

    model_config = ConfigDict(frozen=True)

    target: str
    expected: tuple[str, ...]


ClaimBody = NoFlow | Reach | BoundClaim | Independent | SetEquality


# frob:doc docs/strata/kernel.md#data-models
class Rung(StrEnum):
    """The evidence ladder (docs/strata/evidence.md); order is L1 < ... < L5."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"


# frob:doc docs/strata/kernel.md#data-models
class Claim(BaseModel):
    """An assert (must be proved) or assume (owned, expiring TCB entry)."""

    model_config = ConfigDict(frozen=True)

    id: str
    body: ClaimBody
    assumed: bool = False
    required_rung: Rung = Rung.L5
    owner: str | None = None
    review: str | None = None  # ISO date; overdue assumes are gate failures


# frob:doc docs/strata/kernel.md#data-models
class RemoveNode(BaseModel):
    """Scenario rewrite: the node (or everything at a residence) is gone."""

    model_config = ConfigDict(frozen=True)

    node_id: str


# frob:doc docs/strata/kernel.md#data-models
class ScaleRate(BaseModel):
    """Scenario rewrite: multiply a flow's rate (surge, retry storm)."""

    model_config = ConfigDict(frozen=True)

    flow_id: str
    factor: float


# frob:doc docs/strata/kernel.md#data-models
class SetTrust(BaseModel):
    """Scenario rewrite: reassign a node's trust level (compromise)."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    level: str


Rewrite = RemoveNode | ScaleRate | SetTrust


# frob:doc docs/strata/kernel.md#data-models
class Scenario(BaseModel):
    """A named counterfactual rewrite under which nested claims are re-checked."""

    model_config = ConfigDict(frozen=True)

    id: str
    rewrites: tuple[Rewrite, ...]
    claims: tuple[Claim, ...]


# frob:doc docs/strata/kernel.md#data-models
class KernelModel(BaseModel):
    """The whole elaborated design: every fact the prover is allowed to see."""

    model_config = ConfigDict(frozen=True)

    nodes: tuple[Node, ...] = ()
    flows: tuple[Flow, ...] = ()
    boundaries: tuple[Boundary, ...] = ()
    claims: tuple[Claim, ...] = ()
    scenarios: tuple[Scenario, ...] = ()
    trust: Lattice = TRUST
    labels: Lattice = LABELS


# frob:doc docs/strata/kernel.md#data-models
class Verdict(StrEnum):
    """How a claim closed: proved, evidenced, assumed, or refuted (law 3)."""

    PROVED = "proved"
    EVIDENCED = "evidenced"
    ASSUMED = "assumed"
    REFUTED = "refuted"


# frob:doc docs/strata/kernel.md#data-models
class Quantifier(StrEnum):
    """The strength a verdict carries; exists may never pose as forall (law 4)."""

    FORALL = "forall"
    EXISTS = "exists"


# frob:doc docs/strata/kernel.md#data-models
class ClaimResult(BaseModel):
    """One claim's verdict, quantifier, and -- when refuted -- its counterexample."""

    model_config = ConfigDict(frozen=True)

    claim_id: str
    verdict: Verdict
    quantifier: Quantifier
    counterexample: tuple[str, ...] = ()  # path of node/flow ids
    detail: str = ""
