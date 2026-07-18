"""Surface AST for strata (docs/strata/surface.md).

Frozen pydantic models mirroring the JSON shape emitted by the Rust
parser (`strata_core.parse_source`, docs/strata/surface.md#parser). These
are structurally close to the kernel models in `_models.py` but are a
distinct layer: the AST is what the parser produced from source text; the
kernel model (`_models.py`) is what the elaborator (T-0060) will turn it
into. Keeping them separate means the parser never has to know a kernel
invariant, and the kernel never has to know source syntax.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, model_validator

from ._models import Quantity


# frob:doc docs/strata/surface.md#parser
class Capacity(BaseModel):
    """The parsed `capacity RATE UNIT replicas MIN..MAX` node property."""

    model_config = ConfigDict(frozen=True)

    rate: Quantity
    replicas_min: int
    replicas_max: int


# frob:doc docs/strata/boundary.md#v0-implementation
class ObserveDecl(BaseModel):
    """A parsed `observe { log CLASSLIST; to IDENT }` node property (T-0070)."""

    model_config = ConfigDict(frozen=True)

    log: tuple[str, ...] = ()
    to: str


# frob:doc docs/strata/surface.md#parser
class NodeDecl(BaseModel):
    """A parsed `node` statement, one entry in a `Module`."""

    model_config = ConfigDict(frozen=True)

    id: str
    trust: str
    is_abstract: bool = False
    clearance: str = "Secret"
    attrs: tuple[str, ...] = ()
    capacity: Capacity | None = None
    residence: str | None = None
    errors_total: bool = False
    panics_contained_by: str | None = None
    observe: ObserveDecl | None = None


# frob:doc docs/strata/surface.md#parser
class FlowDecl(BaseModel):
    """A parsed `flow` statement, one entry in a `Module`."""

    model_config = ConfigDict(frozen=True)

    id: str
    src: str
    dst: str
    label: str = "Public"
    age: Quantity | None = None
    rate: Quantity | None = None
    size: Quantity | None = None
    attrs: tuple[str, ...] = ()
    transport: tuple[str, ...] = ()


# frob:doc docs/strata/boundary.md#v0-implementation
class AdmitPhase(BaseModel):
    """A parsed `admit { rate_limit ...; max_size ... }` boundary phase block."""

    model_config = ConfigDict(frozen=True)

    rate_limit: Quantity | None = None
    max_size: Quantity | None = None


# frob:doc docs/strata/boundary.md#v0-implementation
class ParsePhase(BaseModel):
    """A parsed `parse { time ...; frame { ... } }` boundary phase block.

    `frame` is grammar-open (unlike `judge`'s fixed-empty block) so the
    elaborator's "admit/parse frames must be empty" rule
    (docs/strata/boundary.md#v0-implementation) has an actual violation to
    catch rather than being vacuously true by grammar shape alone.
    """

    model_config = ConfigDict(frozen=True)

    time: str | None = None
    frame: tuple[str, ...] = ()


# frob:doc docs/strata/boundary.md#v0-implementation
class EffectPhase(BaseModel):
    """A parsed `effect { frame { ... } }` boundary phase block."""

    model_config = ConfigDict(frozen=True)

    frame: tuple[str, ...] = ()


# frob:doc docs/strata/boundary.md#v0-implementation
class RecordPhase(BaseModel):
    """A parsed `record { audit to IDENT }` boundary phase block."""

    model_config = ConfigDict(frozen=True)

    audit_to: str


# frob:doc docs/strata/boundary.md#v0-implementation
class RefusePhase(BaseModel):
    """A parsed `refuse { respond IDENT; frame { ... }? }` boundary phase block."""

    model_config = ConfigDict(frozen=True)

    respond: str
    frame: tuple[str, ...] = ()


# frob:doc docs/strata/boundary.md#v0-implementation
class PhaseBlock(BaseModel):
    """The parsed six-phase block attached to a `boundary` statement (T-0069).

    Each phase is optional at the AST layer -- the parser accepts any
    subset -- but the elaborator may require particular combinations; this
    model only mirrors parser output, it enforces nothing.
    """

    model_config = ConfigDict(frozen=True)

    admit: AdmitPhase | None = None
    parse: ParsePhase | None = None
    judge: bool = False
    effect: EffectPhase | None = None
    record: RecordPhase | None = None
    refuse: RefusePhase | None = None


# frob:doc docs/strata/surface.md#parser
class BoundaryDecl(BaseModel):
    """A parsed `boundary` statement, one entry in a `Module`."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str  # "endorse" | "declassify"
    flow_id: str
    from_level: str
    to_level: str
    predicate: str = ""
    phases: PhaseBlock | None = None


# frob:doc docs/strata/boundary.md#v0-implementation
class OperationDecl(BaseModel):
    """A parsed `operation ID on IDENT { modifies ... atomic via ... }` statement."""

    model_config = ConfigDict(frozen=True)

    id: str
    on: str
    modifies_ok: tuple[str, ...] = ()
    modifies_err: tuple[str, ...] = ()
    atomic_via: str


# frob:doc docs/strata/surface.md#parser
class ClaimDecl(BaseModel):
    """A parsed `assert`/`assume` statement, one entry in a `Module`."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str  # "noflow" | "reach" | "bound"
    src: str | None = None
    dst: str | None = None
    metric: str | None = None
    target: str | None = None
    limit: Quantity | None = None
    assumed: bool = False
    owner: str | None = None
    review: str | None = None


# frob:doc docs/strata/kernel.md#scenario
class RemoveDecl(BaseModel):
    """A parsed `remove IDENT` scenario rewrite: the node (and its edges) is gone."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["remove"] = "remove"
    node_id: str


# frob:doc docs/strata/kernel.md#scenario
class ScaleDecl(BaseModel):
    """A parsed `scale IDENT by NUM` scenario rewrite: multiply a flow's rate."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["scale"] = "scale"
    flow_id: str
    factor: float


# frob:doc docs/strata/kernel.md#scenario
class TrustDecl(BaseModel):
    """A parsed `trust IDENT := IDENT` scenario rewrite: reassign a node's trust."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["trust"] = "trust"
    node_id: str
    level: str


#: The typed union of syntactic scenario rewrite forms (docs/strata/kernel.md#scenario).
RewriteDecl = RemoveDecl | ScaleDecl | TrustDecl


# frob:doc docs/strata/kernel.md#scenario
class ScenarioDecl(BaseModel):
    """A parsed `scenario ID { rewrite* claim* }` statement, one entry in a `Module`."""

    model_config = ConfigDict(frozen=True)

    id: str
    rewrites: tuple[RewriteDecl, ...] = ()
    claims: tuple[ClaimDecl, ...] = ()


# frob:doc docs/strata/surface.md#parser
class RefineDecl(BaseModel):
    """A parsed `refine X into { ... binds ... }` statement, one entry in a `Module`."""

    model_config = ConfigDict(frozen=True)

    target: str
    nodes: tuple[NodeDecl, ...] = ()
    flows: tuple[FlowDecl, ...] = ()
    bind_to: str


# frob:doc docs/strata/surface.md#std-infra
class StoreDecl(BaseModel):
    """A parsed `store` statement (std.infra): a node with engine/durability markers."""

    model_config = ConfigDict(frozen=True)

    id: str
    trust: str
    clearance: str = "Secret"
    attrs: tuple[str, ...] = ()
    capacity: Capacity | None = None
    residence: str | None = None
    engine: str | None = None
    immutable: bool = False
    append_only: bool = False
    rpo: Quantity | None = None


# frob:doc docs/strata/surface.md#std-infra
class CacheDecl(BaseModel):
    """A parsed `cache X of Y` statement (std.infra): a derived view over `of`."""

    model_config = ConfigDict(frozen=True)

    id: str
    of: str
    keyed_by: str | None = None
    ttl: Quantity | None = None
    staleness: Quantity | None = None
    hit: float | None = None
    policy: str | None = None
    invalidate_on: tuple[str, ...] = ()


# frob:doc docs/strata/surface.md#std-infra
class QueueDecl(BaseModel):
    """A parsed `queue` statement (std.infra): carries delivery/ordering semantics."""

    model_config = ConfigDict(frozen=True)

    id: str
    delivery: str | None = None
    ordering: str | None = None
    attrs: tuple[str, ...] = ()
    clearance: str | None = None


# frob:doc docs/strata/surface.md#std-infra
class CdnDecl(BaseModel):
    """A parsed `cdn X of Y` statement (std.infra): a fronting cache with a provider."""

    model_config = ConfigDict(frozen=True)

    id: str
    of: str
    provider: str | None = None
    provider_trust: str | None = None
    staleness: Quantity | None = None
    staleness_unlimited: bool = False
    hit: float | None = None
    tls_terminates_at_provider: bool = False


# frob:doc docs/strata/surface.md#std-infra
class BalancerDecl(BaseModel):
    """A parsed `balancer` statement (std.infra): a routing policy node."""

    model_config = ConfigDict(frozen=True)

    id: str
    policy: str | None = None
    sticky: bool = False


# frob:doc docs/strata/policy.md#semantic-scoping
class ScopeSpec(BaseModel):
    """A policy's semantic scope: a component name, or a trust/label lattice floor."""

    model_config = ConfigDict(frozen=True)

    kind: str  # "component" | "trust" | "label" -- closed by the grammar
    value: str


# frob:doc docs/strata/policy.md#the-five-forms
class ForbidCall(BaseModel):
    """A parsed `forbid call IDENTLIST` policy rule (prohibition form)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["forbid_call"] = "forbid_call"
    idents: tuple[str, ...]


# frob:doc docs/strata/policy.md#the-five-forms
class ForbidImport(BaseModel):
    """A parsed `forbid import IDENTLIST` policy rule (prohibition form)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["forbid_import"] = "forbid_import"
    idents: tuple[str, ...]


# frob:doc docs/strata/policy.md#the-five-forms
class ConfineUse(BaseModel):
    """A parsed `confine use IDENT to STRING` policy rule (confinement form)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["confine_use"] = "confine_use"
    ident: str
    home: str


# frob:doc docs/strata/policy.md#the-five-forms
class AtCallRequire(BaseModel):
    """A parsed `at call IDENT require arg IDENT` rule (obligation-at-site form)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["at_call_require_arg"] = "at_call_require_arg"
    ident: str
    arg: str


# frob:doc docs/strata/policy.md#the-five-forms
class Mediate(BaseModel):
    """A parsed `mediate IDENT via STRING` policy rule (chokepoint form)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["mediate"] = "mediate"
    ident: str
    mediator: str


#: The typed union of syntactic policy_rule forms compiled by `_policy.py`;
#: `enables`/`rationale` are policy-level metadata, not patterns, and are
#: split out of the raw rule list before this union ever sees it (below).
PolicyRule = ForbidCall | ForbidImport | ConfineUse | AtCallRequire | Mediate


# frob:doc docs/strata/policy.md#semantic-scoping
class PolicyDecl(BaseModel):
    """A parsed `policy ID on SCOPESPEC { ... }` statement, one entry in a `Module`."""

    model_config = ConfigDict(frozen=True)

    id: str
    scope: ScopeSpec
    rules: tuple[PolicyRule, ...] = ()
    enables: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _split_meta_rules(cls, data: object) -> object:
        """Pull `enables`/`rationale` entries out of the parser's raw rule list.

        WHY: the surface grammar treats `enables`/`rationale` as ordinary
        policy_rule alternatives so they can be interleaved with the
        pattern rules in source order (docs/strata/policy.md#the-five-
        forms), but semantically they are policy metadata rather than
        compiled patterns. This is the single place that performs the
        split, before the typed `PolicyRule` union ever sees the list --
        keeping every downstream consumer (`_policy.py`) working with an
        already-separated `rules`/`enables`/`rationale` shape.
        """
        if not isinstance(data, dict):
            return data
        payload = cast("dict[str, Any]", data)
        raw_rules = payload.get("rules")
        if not isinstance(raw_rules, list):
            return data
        rules: list[Any] = []
        enables: list[Any] = list(payload.get("enables") or ())
        rationale: list[Any] = list(payload.get("rationale") or ())
        for entry in raw_rules:
            entry_kind = entry.get("kind") if isinstance(entry, dict) else None
            if entry_kind == "enables":
                enables.append(entry["atom"])
            elif entry_kind == "rationale":
                rationale.append(entry["text"])
            else:
                rules.append(entry)
        return {
            **payload,
            "rules": rules,
            "enables": tuple(enables),
            "rationale": tuple(rationale),
        }


# frob:doc docs/strata/surface.md#parser
class Module(BaseModel):
    """A whole parsed source file: exactly the shape the Rust parser emits."""

    model_config = ConfigDict(frozen=True)

    name: str
    nodes: tuple[NodeDecl, ...] = ()
    flows: tuple[FlowDecl, ...] = ()
    boundaries: tuple[BoundaryDecl, ...] = ()
    claims: tuple[ClaimDecl, ...] = ()
    refines: tuple[RefineDecl, ...] = ()
    stores: tuple[StoreDecl, ...] = ()
    caches: tuple[CacheDecl, ...] = ()
    queues: tuple[QueueDecl, ...] = ()
    cdns: tuple[CdnDecl, ...] = ()
    balancers: tuple[BalancerDecl, ...] = ()
    policies: tuple[PolicyDecl, ...] = ()
    operations: tuple[OperationDecl, ...] = ()
    scenarios: tuple[ScenarioDecl, ...] = ()
