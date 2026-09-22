"""frob.gates._sys_provenance -- SYS116/SYS117 provenance / trust-as-identity
consumer (T-3961's accepted design, implemented under T-4612).

T-3961's design note (parent ticket) investigated existing mechanisms
first (charter law: reuse, never parallel-build) and concluded the two
new surface constructs it needed -- `derived_from:<tag>=<helper>` and
`trust_identity:<tag>` -- reuse the EXISTING `Node.attrs` opaque-attr
slot, the SAME attr-desugar convention `code=`/`pii=`/T-4073's `no_pii`
already use (zero `strata-core` grammar change, zero new `KernelModel`
field). `frob.strata._pii` owns parsing/validating that convention
(`node_derived_from`, `node_trust_identity_tags`, PII005 contradiction);
THIS module is the "SYS10x consumer" half the design's acceptance
criterion 2 asks for -- a structural, declaration-shape-only check
(cheap first step, no taint analysis, per the design note's own
disclosed-deferral posture), kept SEPARATE from `_pii.py` because it is
gate-shaped (produces `frob.gates._models.Violation`), not strata-model-
shaped (produces `PiiViolation`), mirroring how `_sys_selfaudit.py` is
split from `_selfconform.py` for the same reason.

Two rules:
- SYS116 (undeclared provenance): a node `carries` an `identifier.*` PII
  tag with NO matching `derived_from:<tag>=<helper>` attr -- the exact
  F-273 finding (a raw client IP trusted behind a proxy, invisible
  because a wrong IP is still just a string) this whole epic traces to.
  Declaring provenance is opt-in per tag (a `carries` tag with no
  `derived_from` is not itself wrong for every category -- narrowed here
  to `identifier.*` specifically, the category the design note's F-273
  example and T-3961's own body both name, rather than all seven
  `PII_CATEGORIES` at once, to avoid a mass false-positive wave across
  every already-declared `contact`/`financial`/etc. tag this same land
  would otherwise produce).
- SYS117 (trust_identity without carries): a node declares
  `trust_identity:<tag>` for a tag it does NOT also `carries` -- a
  provenance statement about data the node's own model says it does not
  hold is a contradiction, the same deny-by-default shape PII001 takes
  on a malformed declaration.

NOT wired into `frob.gates._sys.sys_gate`'s dispatch or
`frob.gates._waive._KNOWN_GATE_RULES` in this change: both files are
held by an in-progress ticket's lease (T-4212) at implementation time --
disclosed in this ticket's Done report, not silently worked around. This
module's two check functions and `evaluate_provenance` aggregator are
complete, tested, and gate-agnostic (mirrors `_pii.py::evaluate_pii`'s
own "no `src/frob/gates` import" posture even though this module lives
under `gates/` -- it imports only `frob.gates._models.Violation`/
`Severity`, no `_sys.py`/`_waive.py` symbol), ready for a follow-up
ticket to wire in once the lease clears.
"""
# frob:ticket T-4612

from __future__ import annotations

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.strata._models import KernelModel, Node
from frob.strata._pii import node_derived_from, node_pii_tags, node_trust_identity_tags

_log = get_logger(__name__)

#: `frob sys audit` rule id for SYS116 (T-3961) undeclared provenance: a
#: node `carries` an `identifier.*` PII tag with no matching
#: `derived_from:<tag>=<helper>` attr naming the sole legitimate
#: producer -- the F-273 finding this epic traces to.
# frob:doc docs/strata/provenance-trust-identity.md#sys10x-consumer
SYS_UNDECLARED_PROVENANCE = "SYS116"

#: `frob sys audit` rule id for SYS117 (T-3961) trust_identity without a
#: matching `carries` tag: a `trust_identity:<tag>` attr naming a tag the
#: node does not itself `carries` -- a provenance statement about data
#: the node's own model says it does not hold.
# frob:doc docs/strata/provenance-trust-identity.md#sys10x-consumer
SYS_TRUST_IDENTITY_WITHOUT_CARRIES = "SYS117"

_IDENTIFIER_CATEGORY_PREFIX = "identifier."


def _identifier_tags(node: Node) -> tuple[str, ...]:
    """Every `carries` tag on `node` in the `identifier.*` category --
    SYS116's own scope (module docstring: narrowed to avoid a mass
    false-positive wave across every other PII category on this land)."""
    return tuple(
        tag
        for tag in node_pii_tags(node)
        if tag.startswith(_IDENTIFIER_CATEGORY_PREFIX)
    )


# frob:doc docs/strata/provenance-trust-identity.md#sys10x-consumer
#   tests/test_pii_provenance_trust_identity.py::TestSys116UndeclaredProvenance.test_undeclared_helper_fires_sys116  # noqa: E501
#   tests/test_pii_provenance_trust_identity.py::TestSys116UndeclaredProvenance.test_declared_helper_does_not_fire_sys116  # noqa: E501
#   tests/test_pii_provenance_trust_identity.py::TestSys116UndeclaredProvenance.test_non_identifier_category_is_out_of_sys116_scope  # noqa: E501
def check_undeclared_provenance(model: KernelModel) -> tuple[Violation, ...]:
    """SYS116: every `identifier.*` `carries` tag on a node has exactly
    one `derived_from:<tag>=<helper>` attr naming its sole legitimate
    producer. Zero is a finding (module docstring); two-or-more with
    different helpers is a SEPARATE finding, `frob.strata._pii`'s own
    PII005 (one home per charter law -- not re-detected here)."""
    violations: list[Violation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        declared_tags = {tag for tag, _helper in node_derived_from(node)}
        for tag in _identifier_tags(node):
            if tag in declared_tags:
                continue
            _log.warning(
                "sys_provenance: SYS116 node %s carries %r with no derived_from",
                node.id,
                tag,
            )
            violations.append(
                Violation(
                    rule=SYS_UNDECLARED_PROVENANCE,
                    severity=Severity.ERROR,
                    file="design",
                    line=1,
                    message=f"node {node.id} carries {tag!r} with no "
                    f"derived_from:{tag}=<helper> attr naming its sole "
                    "legitimate producer",
                    symref=node.id,
                )
            )
    return tuple(violations)


# frob:doc docs/strata/provenance-trust-identity.md#sys10x-consumer
#   tests/test_pii_provenance_trust_identity.py::TestSys117TrustIdentityWithoutCarries.test_trust_identity_without_carries_fires_sys117  # noqa: E501
#   tests/test_pii_provenance_trust_identity.py::TestSys117TrustIdentityWithoutCarries.test_trust_identity_with_matching_carries_does_not_fire  # noqa: E501
def check_trust_identity_without_carries(model: KernelModel) -> tuple[Violation, ...]:
    """SYS117: every `trust_identity:<tag>` attr on a node names a tag the
    SAME node also declares via `carries` -- a node cannot be authorized
    to treat a value as trusted identity under a tag its own model says
    it does not hold (module docstring)."""
    violations: list[Violation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        carried = set(node_pii_tags(node))
        for tag in node_trust_identity_tags(node):
            if tag in carried:
                continue
            _log.warning(
                "sys_provenance: SYS117 node %s declares trust_identity:%s "
                "with no matching carries tag",
                node.id,
                tag,
            )
            violations.append(
                Violation(
                    rule=SYS_TRUST_IDENTITY_WITHOUT_CARRIES,
                    severity=Severity.ERROR,
                    file="design",
                    line=1,
                    message=f"node {node.id} declares trust_identity:{tag} "
                    f"but does not carries {tag!r}",
                    symref=node.id,
                )
            )
    return tuple(violations)


# frob:doc docs/strata/provenance-trust-identity.md#sys10x-consumer
#   tests/test_pii_provenance_trust_identity.py::TestEvaluateProvenance.test_evaluate_provenance_merges_both_rules  # noqa: E501
#   tests/test_pii_provenance_trust_identity.py::TestEvaluateProvenance.test_evaluate_provenance_clean_model_has_no_violations  # noqa: E501
def evaluate_provenance(model: KernelModel) -> tuple[Violation, ...]:
    """SYS116 + SYS117 over `model`, in rule-then-node order -- the
    gate-agnostic entrypoint a future `_sys.py::sys_gate` wiring calls
    (module docstring: not wired yet, lease-blocked)."""
    all_violations = (
        *check_undeclared_provenance(model),
        *check_trust_identity_without_carries(model),
    )
    _log.info(
        "sys_provenance: evaluated %d node(s) -> %d violation(s)",
        len(model.nodes),
        len(all_violations),
    )
    return all_violations


__all__ = [
    "SYS_TRUST_IDENTITY_WITHOUT_CARRIES",
    "SYS_UNDECLARED_PROVENANCE",
    "check_trust_identity_without_carries",
    "check_undeclared_provenance",
    "evaluate_provenance",
]
