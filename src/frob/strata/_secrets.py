"""std.secrets: credentials as cache-of-authority (docs/strata/kernel.md, T-0082).

A vocabulary is a pure function `surface construct -> kernel facts` (charter
law 1, docs/strata/surface.md#std-secrets); `std.secrets` is that function
for a credential. It adds no kernel primitive: a credential desugars to a
`Node` (the credential itself, at `Secret` clearance) plus `Flow`s and one
`SetEquality` claim, reusing exactly the machinery `std.infra`'s `cache`
already established (`_infra.py::_elaborate_cache`) rather than building a
second age system (docs/strata/kernel.md#age-propagation-semantics, T-0065):

- an **issue** flow (`issued_by -> secret`, `age = lifetime`) is the same
  age-bearing hop a cache's `fill` flow is -- a credential's rotation
  cadence is one more flow declaring an `age`, not a new metric.
- a **revocation** edge (`issued_by -> secret`, `attrs=("revocation",)`) is
  mandatory, mirroring `_infra.py`'s `invalidate_on` requirement exactly:
  "no cache without an invalidation edge" and "no credential without a
  revocation edge" are the same age-collapse rule
  (docs/strata/charter.md, docs/strata/threat.md#compliance). A spec with
  no `revoke` SLA fails closed with `StrataError.MissingRevocation`, never
  a silent default (charter law 2).
- one **reads** flow per authorized `audience` member (`secret -> reader`,
  `label="Secret"`) is the substrate the auto-generated `readers(secret) ==
  audience` claim (`SetEquality`, `_models.py`) closes over -- reusing the
  same forward, barrier-respecting closure `reach` claims already use
  (`_claims.py::_eval_set_equality`), not a bespoke traversal.

Secret-in-logs / secret-in-repo / secret-in-artifact need no code here at
all: those are a `Secret`-labeled flow resting at a node whose `clearance`
is below `Secret`, which `_facts.py::_structural_diagnostics` already
flags for every label (it was written generically for `Pii`, and the
`Public < Internal < Pii < Secret` lattice already puts `Secret` at the
top -- see `tests/unit/strata/test_secrets.py::TestSecretLabelViolations`
for the reused-machinery evidence, not a fork of it).

Deferred surface grammar (T-0132 precedent, tracked as a new ticket,
docs/strata/surface.md#std-secrets): the `.strata` grammar's `secret`
keyword (surface.md line 31, 65, 94-95) is not yet implemented in the
`strata_core` Rust parser, so this module is a Python-API vocabulary only
-- callers build a `SecretSpec` directly (as `_infra.py`'s `CacheDecl`
elaboration is normally reached via `Module.caches`, but nothing stops a
caller from constructing kernel facts by hand). Wiring `secret X issued_by
Y audience [...] lifetime T revoke T'` into the recursive-descent grammar
is out of scope for this ticket (scope is `src/frob/strata/**`, not the
Rust crate) and is filed as T-0134.
# frob:todo T-0134
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_secrets.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._models import (
    Claim,
    Flow,
    Node,
    Quantity,
    SetEquality,
)

_log = get_logger(__name__)

# frob:doc docs/strata/surface.md#std-secrets
#: Data label every std.secrets node/flow carries; the top of the built-in
#: `LABELS` lattice (`_models.py::LABELS`) -- a credential is definitionally
#: the most sensitive payload the lattice knows.
SECRET_LABEL = "Secret"


# frob:doc docs/strata/surface.md#std-secrets
class SecretSpec(BaseModel):
    """The Python-API input to `elaborate_secret`: one credential's declaration.

    Mirrors the surface grammar's planned `secret X issued_by Y audience
    [...] lifetime T revoke T'` shape (docs/strata/surface.md#std-secrets)
    at the AST layer, deferred here to the Python API only -- see the
    module docstring's deferral note (T-0134).
    """

    model_config = ConfigDict(frozen=True)

    id: str
    issued_by: str  # node id of the issuing authority
    audience: tuple[str, ...]  # authorized reader node ids -- the readers() set S
    lifetime: Quantity  # TTL; joins the T-0065 age-propagation machinery
    revoke: Quantity | None = None  # mandatory revocation SLA; None fails closed


# frob:doc docs/strata/surface.md#std-secrets
class SecretExpansion(BaseModel):
    """The `Node`/`Flow`/`Claim` facts one `SecretSpec` desugars to.

    Additive to a caller's existing tuples (unlike `_infra.py`'s
    `InfraExpansion`, nothing here patches an already-built flow), so a
    caller concatenates `nodes`/`flows`/`claims` onto its running model.
    """

    model_config = ConfigDict(frozen=True)

    node: Node
    flows: tuple[Flow, ...]
    claims: tuple[Claim, ...]


def _validate_secret_refs(
    spec: SecretSpec, known: dict[str, Node]
) -> Result[Node, StrataError]:
    """`issued_by` and every `audience` member must resolve; else `UnknownReference`."""
    issuer = known.get(spec.issued_by)
    if issuer is None:
        _log.error(
            "secret %s: issuing authority %r is not declared", spec.id, spec.issued_by
        )
        return Err(StrataError.UnknownReference)
    for reader in spec.audience:
        if reader not in known:
            _log.error("secret %s: audience member %r is not declared", spec.id, reader)
            return Err(StrataError.UnknownReference)
    return Ok(issuer)


def _validate_secret_bounds(spec: SecretSpec) -> Result[Quantity, StrataError]:
    """`revoke` is mandatory (deny by default); `lifetime`/`revoke` must be time.

    No `revoke` SLA fails closed with `StrataError.MissingRevocation` --
    "no credential without a revocation edge", the same rule
    `_infra.py::_elaborate_cache` enforces as `MissingInvalidation`. Returns
    the validated `revoke` `Quantity` (not just `None`) so the caller keeps
    a type-narrowed, non-`None` value rather than re-deriving it from the
    still-`Quantity | None`-typed `spec.revoke`.
    """
    if spec.revoke is None:
        _log.error(
            "secret %s: no revoke SLA declared -- no credential without a "
            "revocation edge (T-0082)",
            spec.id,
        )
        return Err(StrataError.MissingRevocation)
    revoke = spec.revoke
    for field_name, quantity in (("lifetime", spec.lifetime), ("revoke", revoke)):
        checked = _check_time_dimension(spec.id, field_name, quantity)
        if checked.is_err:
            return Err(checked.danger_err)
    return Ok(revoke)


def _check_time_dimension(
    spec_id: str, field_name: str, quantity: Quantity
) -> Result[None, StrataError]:
    """`quantity` must dimension to `"time"`, for `_validate_secret_bounds`'s
    `lifetime`/`revoke` checks."""
    dimension = quantity.dimension()
    if dimension.is_err:
        _log.error(
            "secret %s: %s has unknown unit %r", spec_id, field_name, quantity.unit
        )
        return Err(dimension.danger_err)
    if dimension.danger_ok != "time":
        _log.error(
            "secret %s: %s %s%s is not a time unit",
            spec_id,
            field_name,
            quantity.value,
            quantity.unit,
        )
        return Err(StrataError.UnitMismatch)
    return Ok(None)


def _secret_flows(spec: SecretSpec) -> tuple[Flow, ...]:
    """The issue/revocation/reads flows one `SecretSpec` desugars to.

    Issue carries `age = lifetime` (the same age-bearing hop a cache's
    `fill` flow is); revocation is the mandatory edge validated present by
    `_validate_secret_bounds` before this is ever called; one reads flow
    per `audience` member is the substrate `readers()` closes over.
    """
    return (
        _secret_issue_flow(spec),
        _secret_revoke_flow(spec),
        *_secret_read_flows(spec),
    )


def _secret_issue_flow(spec: SecretSpec) -> Flow:
    """The `issue` flow one `SecretSpec` desugars to, for `_secret_flows`."""
    return Flow(
        id=f"{spec.id}__issue",
        src=spec.issued_by,
        dst=spec.id,
        label=SECRET_LABEL,
        age=spec.lifetime,
        attrs=("issue",),
    )


def _secret_revoke_flow(spec: SecretSpec) -> Flow:
    """The mandatory `revocation` flow one `SecretSpec` desugars to, for
    `_secret_flows`."""
    return Flow(
        id=f"{spec.id}__revoke",
        src=spec.issued_by,
        dst=spec.id,
        label=SECRET_LABEL,
        age=Quantity(value=0.0, unit="s"),
        attrs=("revocation",),
    )


def _secret_read_flows(spec: SecretSpec) -> tuple[Flow, ...]:
    """One `reads` flow per `audience` member, for `_secret_flows`."""
    return tuple(
        Flow(
            id=f"{spec.id}__reads_{reader}",
            src=spec.id,
            dst=reader,
            label=SECRET_LABEL,
            attrs=("reads",),
        )
        for reader in spec.audience
    )


# frob:doc docs/strata/surface.md#std-secrets
def elaborate_secret(
    spec: SecretSpec, known: dict[str, Node]
) -> Result[SecretExpansion, StrataError]:
    """`secret X issued_by Y audience [...] lifetime T revoke T'` -> kernel facts.

    Fails closed (deny by default, docs/strata/surface.md#std-secrets) via
    `_validate_secret_refs` (unknown `issued_by`/`audience`) and
    `_validate_secret_bounds` (missing `revoke` SLA, wrong-dimension
    `lifetime`/`revoke` -- the same dimension-checked pattern
    `_infra.py::_elaborate_store`'s `rpo` uses); only then builds the
    issue/revocation/reads flows (`_secret_flows`) and the auto-generated
    `readers(secret) == audience` claim. The lifetime/rotation bound itself
    is not a separate claim form (charter law 1); a caller wanting
    `age(secret) <= limit` asserts an ordinary AGE `bound` claim with
    `target=spec.id`, which walks the issue flow's declared age exactly
    like any other node's worst-case staleness
    (docs/strata/kernel.md#age-propagation-semantics).
    """
    validated = _validate_and_log_secret(spec, known)
    if validated.is_err:
        return Err(validated.danger_err)
    return Ok(_secret_expansion(spec, validated.danger_ok))


def _validate_and_log_secret(
    spec: SecretSpec, known: dict[str, Node]
) -> Result[Node, StrataError]:
    """Validate `spec`'s refs and bounds, log the elaborated summary, and
    return its resolved issuer -- split out of `elaborate_secret` purely to
    keep that function's body short."""
    refs = _validate_secret_refs(spec, known)
    if refs.is_err:
        return Err(refs.danger_err)
    bounds = _validate_secret_bounds(spec)
    if bounds.is_err:
        return Err(bounds.danger_err)
    revoke = bounds.danger_ok
    _log.info(
        "elaborated secret %s: issuer=%s audience=%d lifetime=%s%s revoke=%s%s",
        spec.id,
        spec.issued_by,
        len(spec.audience),
        spec.lifetime.value,
        spec.lifetime.unit,
        revoke.value,
        revoke.unit,
    )
    return Ok(refs.danger_ok)


def _secret_expansion(spec: SecretSpec, issuer: Node) -> SecretExpansion:
    """Assemble the `SecretExpansion` (node, flows, readers claim) for a
    validated `SecretSpec`, split out of `elaborate_secret` purely to keep
    that function's body short."""
    node = Node(id=spec.id, trust=issuer.trust, clearance=SECRET_LABEL)
    readers_claim = Claim(
        id=f"{spec.id}__readers",
        body=SetEquality(target=spec.id, expected=spec.audience),
    )
    return SecretExpansion(
        node=node, flows=_secret_flows(spec), claims=(readers_claim,)
    )
