"""Unit tests for T-3961's provenance/trust-as-identity attrs
(`derived_from:<tag>=<helper>`, `trust_identity:<tag>`) and their two
consumers: `frob.strata._pii`'s PII005 contradiction check and
`frob.gates._sys_provenance`'s SYS116/SYS117 structural checks.

Mirrors `tests/unit/strata/test_pii.py`'s hand-built-`KernelModel`
convention. Each positive control below plants the EXACT finding the
rule exists to catch (T-3961's own F-273 client-ip framing) and asserts
it fires, then asserts the declared-correctly case does not -- the
"declared vs. undeclared" pair `frob.gates._sys_provenance`'s docstring
itself asks for.
"""

from __future__ import annotations

from frob.gates._sys_provenance import (
    SYS_TRUST_IDENTITY_WITHOUT_CARRIES,
    SYS_UNDECLARED_PROVENANCE,
    check_trust_identity_without_carries,
    check_undeclared_provenance,
    evaluate_provenance,
)
from frob.strata._models import KernelModel, Node
from frob.strata._pii import (
    check_pii_derived_from_contradiction,
    node_derived_from,
    node_trust_identity_tags,
)


def _node(node_id: str, trust: str = "trusted", attrs: tuple[str, ...] = ()) -> Node:
    """One `Node` with the given attrs, matching `test_pii.py`'s own
    minimal-fixture convention."""
    return Node(id=node_id, trust=trust, attrs=attrs)


class TestDerivedFromParsing:
    # frob:tests \
    # tests/test_pii_provenance_trust_identity.py::TestDerivedFromParsing.test_node_derived_from_parses_tag_and_helper kind="unit"  # noqa: E501
    def test_node_derived_from_parses_tag_and_helper(self):
        node = _node(
            "gateway",
            attrs=("derived_from:identifier.client_ip=app.net.get_trusted_client_ip",),
        )
        assert node_derived_from(node) == (
            ("identifier.client_ip", "app.net.get_trusted_client_ip"),
        )

    # frob:tests \
    # tests/test_pii_provenance_trust_identity.py::TestDerivedFromParsing.test_node_derived_from_skips_malformed_attr kind="unit"  # noqa: E501
    def test_node_derived_from_skips_malformed_attr(self):
        node = _node("gateway", attrs=("derived_from:no-equals-sign",))
        assert node_derived_from(node) == ()

    # frob:tests \
    # tests/test_pii_provenance_trust_identity.py::TestDerivedFromParsing.test_node_trust_identity_tags_reads_prefixed_attrs kind="unit"  # noqa: E501
    def test_node_trust_identity_tags_reads_prefixed_attrs(self):
        node = _node(
            "gateway",
            attrs=("trust_identity:identifier.client_ip", "other"),
        )
        assert node_trust_identity_tags(node) == ("identifier.client_ip",)


class TestPii005DerivedFromContradiction:
    # frob:tests src/frob/strata/_pii.py::check_pii_derived_from_contradiction \
    # kind="unit"
    def test_conflicting_helpers_on_same_tag_fires_pii005(self):
        node = _node(
            "gateway",
            attrs=(
                "pii=identifier.client_ip",
                "derived_from:identifier.client_ip=app.net.get_trusted_client_ip",
                "derived_from:identifier.client_ip=app.legacy.raw_peer_addr",
            ),
        )
        model = KernelModel(nodes=(node,))
        violations = check_pii_derived_from_contradiction(model)
        assert len(violations) == 1
        assert violations[0].rule == "PII005"
        assert violations[0].target == "gateway"

    # frob:tests src/frob/strata/_pii.py::check_pii_derived_from_contradiction \
    # kind="unit"
    def test_single_helper_does_not_fire_pii005(self):
        node = _node(
            "gateway",
            attrs=(
                "pii=identifier.client_ip",
                "derived_from:identifier.client_ip=app.net.get_trusted_client_ip",
            ),
        )
        model = KernelModel(nodes=(node,))
        assert check_pii_derived_from_contradiction(model) == ()


class TestSys116UndeclaredProvenance:
    # frob:tests src/frob/gates/_sys_provenance.py::check_undeclared_provenance \
    # kind="unit"
    # frob:tests src/frob/strata/_pii.py::node_derived_from
    def test_undeclared_helper_fires_sys116(self):
        """Positive control: the F-273 shape -- a node carrying an
        identifier tag with NO derived_from attr at all must fire."""
        node = _node("gateway", attrs=("pii=identifier.client_ip",))
        model = KernelModel(nodes=(node,))
        violations = check_undeclared_provenance(model)
        assert len(violations) == 1
        assert violations[0].rule == SYS_UNDECLARED_PROVENANCE
        assert violations[0].symref == "gateway"

    # frob:tests src/frob/gates/_sys_provenance.py::check_undeclared_provenance \
    # kind="unit"
    # frob:tests src/frob/strata/_pii.py::node_derived_from
    def test_declared_helper_does_not_fire_sys116(self):
        """A tag with a declared derived_from helper must NOT fire."""
        node = _node(
            "gateway",
            attrs=(
                "pii=identifier.client_ip",
                "derived_from:identifier.client_ip=app.net.get_trusted_client_ip",
            ),
        )
        model = KernelModel(nodes=(node,))
        assert check_undeclared_provenance(model) == ()

    # frob:tests src/frob/gates/_sys_provenance.py::check_undeclared_provenance \
    # kind="unit"
    def test_non_identifier_category_is_out_of_sys116_scope(self):
        """SYS116 is narrowed to `identifier.*` (module docstring) -- a
        `contact.*` tag with no derived_from must not fire."""
        node = _node("gateway", attrs=("pii=contact.email",))
        model = KernelModel(nodes=(node,))
        assert check_undeclared_provenance(model) == ()


class TestSys117TrustIdentityWithoutCarries:
    # frob:tests \
    # src/frob/gates/_sys_provenance.py::check_trust_identity_without_carries \
    # kind="unit"
    # frob:tests src/frob/strata/_pii.py::node_trust_identity_tags
    def test_trust_identity_without_carries_fires_sys117(self):
        node = _node("auth", attrs=("trust_identity:identifier.client_ip",))
        model = KernelModel(nodes=(node,))
        violations = check_trust_identity_without_carries(model)
        assert len(violations) == 1
        assert violations[0].rule == SYS_TRUST_IDENTITY_WITHOUT_CARRIES

    # frob:tests \
    # src/frob/gates/_sys_provenance.py::check_trust_identity_without_carries \
    # kind="unit"
    # frob:tests src/frob/strata/_pii.py::node_trust_identity_tags
    def test_trust_identity_with_matching_carries_does_not_fire(self):
        node = _node(
            "auth",
            attrs=("pii=identifier.client_ip", "trust_identity:identifier.client_ip"),
        )
        model = KernelModel(nodes=(node,))
        assert check_trust_identity_without_carries(model) == ()


class TestEvaluateProvenance:
    # frob:tests src/frob/gates/_sys_provenance.py::evaluate_provenance kind="unit"
    def test_evaluate_provenance_merges_both_rules(self):
        node = _node(
            "gateway",
            attrs=("pii=identifier.client_ip", "trust_identity:identifier.other"),
        )
        model = KernelModel(nodes=(node,))
        violations = evaluate_provenance(model)
        rules = {v.rule for v in violations}
        assert rules == {SYS_UNDECLARED_PROVENANCE, SYS_TRUST_IDENTITY_WITHOUT_CARRIES}

    # frob:tests src/frob/gates/_sys_provenance.py::evaluate_provenance kind="unit"
    def test_evaluate_provenance_clean_model_has_no_violations(self):
        node = _node(
            "gateway",
            attrs=(
                "pii=identifier.client_ip",
                "derived_from:identifier.client_ip=app.net.get_trusted_client_ip",
                "trust_identity:identifier.client_ip",
            ),
        )
        model = KernelModel(nodes=(node,))
        assert evaluate_provenance(model) == ()
