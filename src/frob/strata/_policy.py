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

import itertools

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import (
    AtCallRequire,
    ConfineUse,
    Mediate,
    Module,
    PolicyRule,
    ScopeSpec,
)
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
# invariant spec: [INV-030](invariants/INV-030.md)
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


# frob:ticket T-1482
# frob:doc docs/strata/policy.md#refinement-monotonicity-inv-051-t-1482
class PolicyWeakening(BaseModel):
    """One INV-051 finding: `child_id`'s scope is a strict subset of
    `parent_id`'s, but `child_id` re-declares a rule for the same
    target atom (`detail` names it) LESS restrictively than the parent
    already required for every node `child_id` also covers -- exactly
    the "a child may only strengthen an inherited policy, never weaken
    it" property docs/strata/policy.md's refinement-monotonicity
    paragraph states as design intent."""

    model_config = ConfigDict(frozen=True)

    parent_id: str
    child_id: str
    rule_kind: str
    detail: str


def _confine_weakenings(
    parent: CompiledPolicy, child: CompiledPolicy
) -> list[PolicyWeakening]:
    """A child `confine use IDENT to HOME` for an ident the parent also
    confines must keep the SAME home, or narrow it to a sub-path of the
    parent's home (a stricter confinement); moving it to an unrelated or
    broader home is a weakening. An ident the child never re-confines is
    unaffected (inherited unmodified)."""
    parent_homes = {
        rule.ident: rule.home for rule in parent.rules if isinstance(rule, ConfineUse)
    }
    violations: list[PolicyWeakening] = []
    for rule in child.rules:
        if not isinstance(rule, ConfineUse):
            continue
        parent_home = parent_homes.get(rule.ident)
        if parent_home is None:
            continue
        narrowed = rule.home.startswith(parent_home.rstrip("/") + "/")
        if rule.home == parent_home or narrowed:
            continue
        violations.append(
            PolicyWeakening(
                parent_id=parent.id,
                child_id=child.id,
                rule_kind="confine_use",
                detail=(
                    f"parent confines {rule.ident!r} to {parent_home!r} but child "
                    f"re-confines it to {rule.home!r} (not the same or a sub-path)"
                ),
            )
        )
    return violations


def _at_call_require_weakenings(
    parent: CompiledPolicy, child: CompiledPolicy
) -> list[PolicyWeakening]:
    """A child that engages a call the parent already constrains (`at call
    IDENT require arg ...`) must require every arg the parent required for
    that same `IDENT`; dropping one is a weakening. A call the child never
    mentions is unaffected (inherited unmodified)."""
    parent_args: dict[str, set[str]] = {}
    for rule in parent.rules:
        if isinstance(rule, AtCallRequire):
            parent_args.setdefault(rule.ident, set()).add(rule.arg)
    child_args: dict[str, set[str]] = {}
    for rule in child.rules:
        if isinstance(rule, AtCallRequire):
            child_args.setdefault(rule.ident, set()).add(rule.arg)
    # PERF004: sort once over the flattened (ident, arg) pairs instead of
    # calling sorted() once per `ident` in the loop below -- same
    # deterministic per-ident-then-per-arg ordering, one sort instead of N.
    dropped_pairs = [
        (ident, arg)
        for ident, required in parent_args.items()
        if ident in child_args
        for arg in required - child_args[ident]
    ]
    violations: list[PolicyWeakening] = []
    for ident, arg in sorted(dropped_pairs):
        violations.append(
            PolicyWeakening(
                parent_id=parent.id,
                child_id=child.id,
                rule_kind="at_call_require_arg",
                detail=(
                    f"parent requires arg {arg!r} at call {ident!r} but child "
                    f"re-declares at call {ident!r} without it"
                ),
            )
        )
    return violations


def _mediate_weakenings(
    parent: CompiledPolicy, child: CompiledPolicy
) -> list[PolicyWeakening]:
    """A child `mediate IDENT via MEDIATOR` for an ident the parent already
    mediates must name the SAME mediator -- there is no proof-strength
    ordering between two distinct mediators available at TIER-1, so any
    change is flagged rather than silently assumed safe (fail closed).
    An ident the child never re-mediates is unaffected (inherited
    unmodified)."""
    parent_mediators = {
        rule.ident: rule.mediator for rule in parent.rules if isinstance(rule, Mediate)
    }
    violations: list[PolicyWeakening] = []
    for rule in child.rules:
        if not isinstance(rule, Mediate):
            continue
        parent_mediator = parent_mediators.get(rule.ident)
        if parent_mediator is None or parent_mediator == rule.mediator:
            continue
        violations.append(
            PolicyWeakening(
                parent_id=parent.id,
                child_id=child.id,
                rule_kind="mediate",
                detail=(
                    f"parent mediates {rule.ident!r} via {parent_mediator!r} but "
                    f"child re-declares it via {rule.mediator!r} (unproven "
                    f"equivalence)"
                ),
            )
        )
    return violations


def _pairwise_weakenings(
    parent: CompiledPolicy, child: CompiledPolicy
) -> list[PolicyWeakening]:
    """Every INV-051 finding between one candidate parent/child scope pair,
    across the three rule forms with a genuine per-atom "same target,
    incompatible re-declaration" shape (`confine use`/`at call ... require
    arg`/`mediate`).

    `forbid call`/`forbid import` are deliberately NOT diffed here: they
    are purely additive prohibitions under the union-of-applicable-
    policies enforcement model docs/strata/policy.md#compilation
    describes -- a child re-declaring `forbid call` with a DIFFERENT
    ident set (e.g. adding a new prohibition unrelated to the parent's)
    can never cause the parent's own prohibitions to stop applying, so
    there is no way for a child to weaken this form by omission. An
    earlier version of this pass compared aggregate ident sets per rule
    kind and flagged exactly that non-case as a false positive (any
    child forbid_call rule not literally re-listing every parent ident
    read as "dropped" it) -- removed once
    `test_no_finding_when_child_never_overlaps_parent_scope` caught it."""
    return [
        *_confine_weakenings(parent, child),
        *_at_call_require_weakenings(parent, child),
        *_mediate_weakenings(parent, child),
    ]


# frob:invariant INV-051
# invariant spec: [INV-051](invariants/INV-051.md)
# frob:doc docs/strata/policy.md#refinement-monotonicity-inv-051-t-1482
# frob:ticket T-1843
# frob:tests tests/unit/strata/test_policy.py::TestRefinementMonotonicity.test_confine_use_broadened_home_detected  # noqa: E501
# frob:tests tests/unit/strata/test_policy.py::TestRefinementMonotonicity.test_at_call_require_dropped_arg_detected  # noqa: E501
# frob:tests tests/unit/strata/test_policy.py::TestRefinementMonotonicity.test_mediate_swapped_mediator_detected  # noqa: E501
# frob:tests tests/unit/strata/test_policy.py::TestRefinementMonotonicity.test_no_finding_when_child_only_strengthens  # noqa: E501
# frob:tests tests/unit/strata/test_policy.py::TestRefinementMonotonicity.test_no_finding_when_child_never_overlaps_parent_scope  # noqa: E501
# frob:tests tests/unit/strata/test_policy.py::TestRefinementMonotonicity.test_forbid_call_never_flagged_even_when_child_narrows  # noqa: E501
def find_policy_weakenings(compiled: CompiledPolicies) -> tuple[PolicyWeakening, ...]:
    """INV-051's refinement-monotonicity diff pass (T-1482): for every pair
    of compiled policies whose scope one strictly contains the other (the
    "parent"/"child" relationship docs/strata/policy.md's refinement
    section describes -- a `component` policy's single node nested inside
    a broader `trust`/`label` policy's node set, or one `trust`/`label`
    threshold nested inside a laxer one), diff every rule form the CHILD
    re-declares for a target the PARENT also constrains, and flag any
    re-declaration that is strictly less restrictive than what the parent
    already required.

    Deliberately does NOT flag a child that never re-declares a given rule
    target at all -- TIER-2 conformance checking enforces the UNION of
    every policy whose scope covers a node (docs/strata/policy.md
    #compilation), so silence from the child is inheritance, not a
    weakening; this pass only has anything to say about an EXPLICIT
    child-side re-declaration for the same target atom.
    """
    # PERF003: generate distinct (parent, child) pairs directly via
    # itertools.permutations instead of a nested loop with an inner `==`
    # self-exclusion check -- structurally excludes self-pairs rather than
    # filtering them out with an equality comparison per candidate.
    violations: list[PolicyWeakening] = []
    for parent, child in itertools.permutations(compiled.policies, 2):
        parent_ids = set(parent.node_ids)
        if not parent_ids:
            continue
        child_ids = set(child.node_ids)
        if not child_ids or not child_ids < parent_ids:
            continue
        violations.extend(_pairwise_weakenings(parent, child))
    return tuple(violations)
