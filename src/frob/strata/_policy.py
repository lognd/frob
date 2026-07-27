"""L4 policy compilation for strata (docs/strata/policy.md).

Resolves each `PolicyDecl`'s semantic scope (component name, or a
trust/label lattice floor) to a concrete set of kernel node ids, producing
a frozen `CompiledPolicies` handoff artifact. This is TIER-1 only: it
never touches source files or runs a tree-sitter query -- that is TIER-2
execution against actual code (phase 4, T-0079/T-0080). `CompiledPolicies`
is exactly the artifact that phase-4 file scanning will consume, and its
rules map onto frob's existing `[policy]` POL machinery at code-binding
time (docs/strata/policy.md#compilation).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import Module, PolicyRule, ScopeSpec
from ._errors import StrataError
from ._models import KernelModel

_log = get_logger(__name__)


# frob:doc docs/strata/policy.md#semantic-scoping
class CompiledPolicy(BaseModel):
    """One policy with its scope resolved to concrete node ids, now (TIER-1)."""

    model_config = ConfigDict(frozen=True)

    id: str
    scope_kind: str
    scope_value: str
    node_ids: tuple[str, ...]  # sorted, resolved against the kernel model
    rules: tuple[PolicyRule, ...]
    enables: tuple[str, ...]


# frob:doc docs/strata/policy.md#compilation
class CompiledPolicies(BaseModel):
    """The whole module's policies, scope-resolved; the phase-4 handoff artifact."""

    model_config = ConfigDict(frozen=True)

    policies: tuple[CompiledPolicy, ...] = ()

    def enabling(self, atom: str) -> tuple[str, ...]:
        """Ids of every compiled policy that declares `enables <atom>`, sorted."""
        # frob:doc docs/strata/policy.md#compilation
        return tuple(sorted(p.id for p in self.policies if atom in p.enables))


def _resolve_scope(
    scope: ScopeSpec, model: KernelModel
) -> Result[tuple[str, ...], StrataError]:
    """Resolve one `ScopeSpec` to sorted node ids; an unknown ref fails closed."""
    if scope.kind == "component":
        if scope.value not in {n.id for n in model.nodes}:
            _log.error("policy scope: component %r is not a declared node", scope.value)
            return Err(StrataError.UnknownReference)
        return Ok((scope.value,))

    if scope.kind == "trust":
        return _resolve_trust_scope(scope.value, model)

    if scope.kind == "label":
        return _resolve_label_scope(scope.value, model)

    # The grammar's SCOPESPEC vocabulary is closed to component/trust/label
    # (strata-core/src/parse.rs::parse_scope_spec); an AST built any other
    # way (e.g. constructed directly rather than parsed) still fails closed
    # here rather than silently resolving to an empty/unscoped policy.
    _log.error("policy scope: unknown scope kind %r", scope.kind)
    return Err(StrataError.UnknownReference)


# frob:invariant INV-030
# frob:tests tests/unit/strata/test_policy.py::TestScopeResolution.test_trust_scope_resolves_via_lattice  # noqa: E501
def _resolve_trust_scope(
    value: str, model: KernelModel
) -> Result[tuple[str, ...], StrataError]:
    """Resolve a `trust`-kind `ScopeSpec` to sorted node ids at/above `value`
    in the trust lattice, for `_resolve_scope`."""
    if value not in model.trust.elements():
        _log.error("policy scope: unknown trust level %r", value)
        return Err(StrataError.UnknownReference)
    ids: list[str] = []
    for node in model.nodes:
        leq = model.trust.leq(value, node.trust)
        if leq.is_err:
            return Err(leq.danger_err)
        if leq.danger_ok:
            ids.append(node.id)
    return Ok(tuple(sorted(ids)))


def _resolve_label_scope(
    value: str, model: KernelModel
) -> Result[tuple[str, ...], StrataError]:
    """Resolve a `label`-kind `ScopeSpec` to sorted node ids at/above `value`
    in the label lattice, for `_resolve_scope`."""
    if value not in model.labels.elements():
        _log.error("policy scope: unknown label level %r", value)
        return Err(StrataError.UnknownReference)
    ids: list[str] = []
    # frob:waive PERF004 reason="sorted() runs once after this loop, not in it"
    for node in model.nodes:
        leq = model.labels.leq(value, node.clearance)
        if leq.is_err:
            return Err(leq.danger_err)
        if leq.danger_ok:
            ids.append(node.id)
    return Ok(tuple(sorted(ids)))


# frob:doc docs/strata/policy.md#compilation
def compile_policies(
    module: Module, kernel_model: KernelModel
) -> Result[CompiledPolicies, StrataError]:
    """Compile every `PolicyDecl` in `module` against `kernel_model`'s scopes.

    WHY: policies attach to model entities, not paths (docs/strata/policy.md
    #semantic-scoping), so scope resolution needs the elaborated
    `KernelModel` (component/trust/label facts), not the surface AST alone.
    Fails closed on any unresolvable scope reference; the TIER-2 execution
    against actual source files -- turning `rules` into tree-sitter queries
    -- is out of scope here (phase 4, T-0079/T-0080).
    """
    compiled: list[CompiledPolicy] = []
    for decl in module.policies:
        resolved = _resolve_scope(decl.scope, kernel_model)
        if resolved.is_err:
            return Err(resolved.danger_err)
        compiled.append(
            CompiledPolicy(
                id=decl.id,
                scope_kind=decl.scope.kind,
                scope_value=decl.scope.value,
                node_ids=resolved.danger_ok,
                rules=decl.rules,
                enables=decl.enables,
            )
        )
    _log.info("compiled %d polic(y/ies) for module %s", len(compiled), module.name)
    return Ok(CompiledPolicies(policies=tuple(compiled)))
