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

from pydantic import BaseModel, ConfigDict

from ._models import Quantity


# frob:doc docs/strata/surface.md#parser
class Capacity(BaseModel):
    """The parsed `capacity RATE UNIT replicas MIN..MAX` node property."""

    model_config = ConfigDict(frozen=True)

    rate: Quantity
    replicas_min: int
    replicas_max: int


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
