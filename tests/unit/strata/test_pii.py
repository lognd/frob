"""Unit tests for `std.pii`: first-class personal-data modeling and flow
proofs (T-0154, docs/strata/threat.md#compliance).

The hand-built-`KernelModel` half of the proof, mirroring `test_compliance.
py`'s own convention; the surface-syntax half (parse -> elaborate ->
evaluate_pii) lives in `test_litmus_pii.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.strata import Claim, Flow, KernelModel, Node, NoFlow, elaborate, parse_module
from frob.strata._pii import (
    PII_CATEGORIES,
    check_pii_boundary_protection,
    check_pii_catalog,
    check_pii_retention_erasure,
    check_pii_undeclared_flow,
    evaluate_pii,
    node_carries_pii,
    node_pii_tags,
)


def _node(node_id: str, trust: str, attrs: tuple[str, ...] = ()) -> Node:
    return Node(id=node_id, trust=trust, attrs=attrs)


class TestPiiTagHelpers:
    # frob:tests src/frob/strata/_pii.py::node_pii_tags kind="unit"
    def test_node_pii_tags_reads_pii_prefixed_attrs(self):
        node = _node("store", "trusted", attrs=("pii=identifier.email", "other"))
        assert node_pii_tags(node) == ("identifier.email",)

    # frob:tests src/frob/strata/_pii.py::node_carries_pii kind="unit"
    def test_node_carries_pii_false_with_no_pii_attrs(self):
        node = _node("store", "trusted", attrs=("engine=postgres",))
        assert node_carries_pii(node) is False

    # frob:tests src/frob/strata/_pii.py::node_carries_pii kind="unit"
    def test_node_carries_pii_true_with_a_pii_attr(self):
        node = _node("store", "trusted", attrs=("pii=health.diagnosis",))
        assert node_carries_pii(node) is True

    def test_categories_match_the_ticket_body_seven(self):
        assert PII_CATEGORIES == frozenset(
            {
                "identifier",
                "contact",
                "financial",
                "health",
                "biometric",
                "behavioral",
                "credentials",
            }
        )


class TestPiiCatalog:
    # frob:tests src/frob/strata/_pii.py::check_pii_catalog kind="unit"
    def test_valid_category_is_clean(self):
        model = KernelModel(
            nodes=(_node("store", "trusted", attrs=("pii=identifier.email",)),)
        )
        assert check_pii_catalog(model) == ()

    # frob:tests src/frob/strata/_pii.py::check_pii_catalog kind="unit"
    def test_unknown_category_is_pii001(self):
        model = KernelModel(
            nodes=(_node("store", "trusted", attrs=("pii=nonsense.field",)),)
        )
        violations = check_pii_catalog(model)
        assert len(violations) == 1
        assert violations[0].rule == "PII001"
        assert violations[0].target == "store"

    # frob:tests src/frob/strata/_pii.py::check_pii_catalog kind="unit"
    def test_tag_with_no_category_separator_is_pii001(self):
        model = KernelModel(nodes=(_node("store", "trusted", attrs=("pii=email",)),))
        violations = check_pii_catalog(model)
        assert len(violations) == 1
        assert violations[0].rule == "PII001"


class TestPiiBoundaryProtection:
    # frob:tests src/frob/strata/_pii.py::check_pii_boundary_protection kind="unit"
    def test_same_trust_flow_does_not_fire(self):
        model = KernelModel(
            nodes=(
                _node("a", "trusted", attrs=("pii=identifier.email",)),
                _node("b", "trusted"),
            ),
            flows=(Flow(id="f", src="a", dst="b", label="Pii"),),
        )
        assert check_pii_boundary_protection(model) == ()

    # frob:tests src/frob/strata/_pii.py::check_pii_boundary_protection kind="unit"
    def test_crossing_trust_with_no_pii_is_clean(self):
        model = KernelModel(
            nodes=(_node("a", "foreign"), _node("b", "trusted")),
            flows=(Flow(id="f", src="a", dst="b", label="Public"),),
        )
        assert check_pii_boundary_protection(model) == ()

    # frob:tests src/frob/strata/_pii.py::check_pii_boundary_protection kind="unit"
    def test_crossing_trust_into_pii_store_fires_pii002(self):
        model = KernelModel(
            nodes=(
                _node("client", "foreign"),
                _node("store", "trusted", attrs=("pii=identifier.email",)),
            ),
            flows=(Flow(id="f_collect", src="client", dst="store", label="Pii"),),
        )
        violations = check_pii_boundary_protection(model)
        assert len(violations) == 1
        assert violations[0].rule == "PII002"
        assert violations[0].target == "f_collect"

    # frob:tests src/frob/strata/_pii.py::check_pii_boundary_protection kind="unit"
    def test_assumed_claim_with_owner_and_review_discharges(self):
        model = KernelModel(
            nodes=(
                _node("client", "foreign"),
                _node("store", "trusted", attrs=("pii=identifier.email",)),
            ),
            flows=(Flow(id="f_collect", src="client", dst="store", label="Pii"),),
            claims=(
                Claim(
                    id="pii:PROTECTION:f_collect",
                    body=NoFlow(src="client", dst="store"),
                    assumed=True,
                    owner="logan",
                    review="2027-01-01",
                ),
            ),
        )
        assert check_pii_boundary_protection(model) == ()

    # frob:tests src/frob/strata/_pii.py::check_pii_boundary_protection kind="unit"
    def test_assumed_claim_missing_owner_is_still_a_violation(self):
        model = KernelModel(
            nodes=(
                _node("client", "foreign"),
                _node("store", "trusted", attrs=("pii=identifier.email",)),
            ),
            flows=(Flow(id="f_collect", src="client", dst="store", label="Pii"),),
            claims=(
                Claim(
                    id="pii:PROTECTION:f_collect",
                    body=NoFlow(src="client", dst="store"),
                    assumed=True,
                    review="2027-01-01",
                ),
            ),
        )
        violations = check_pii_boundary_protection(model)
        assert len(violations) == 1
        assert violations[0].rule == "PII002"
        assert violations[0].target == "pii:PROTECTION:f_collect"


class TestPiiRetentionErasure:
    # frob:tests src/frob/strata/_pii.py::check_pii_retention_erasure kind="unit"
    def test_no_pii_no_finding(self):
        model = KernelModel(nodes=(_node("store", "trusted"),))
        assert check_pii_retention_erasure(model) == ()

    # frob:tests src/frob/strata/_pii.py::check_pii_retention_erasure kind="unit"
    def test_pii_with_no_retention_or_erasure_fires_pii003(self):
        model = KernelModel(
            nodes=(_node("store", "trusted", attrs=("pii=identifier.email",)),)
        )
        violations = check_pii_retention_erasure(model)
        assert len(violations) == 1
        assert violations[0].rule == "PII003"
        assert violations[0].target == "store"

    # frob:tests src/frob/strata/_pii.py::check_pii_retention_erasure kind="unit"
    def test_declared_retention_discharges(self):
        model = KernelModel(
            nodes=(
                _node(
                    "store",
                    "trusted",
                    attrs=("pii=identifier.email", "retention=90d"),
                ),
            )
        )
        assert check_pii_retention_erasure(model) == ()

    # frob:tests src/frob/strata/_pii.py::check_pii_retention_erasure kind="unit"
    def test_revocation_edge_discharges(self):
        model = KernelModel(
            nodes=(
                _node("store", "trusted", attrs=("pii=identifier.email",)),
                _node("eraser", "trusted"),
            ),
            flows=(
                Flow(id="f_erase", src="eraser", dst="store", attrs=("revocation",)),
            ),
        )
        assert check_pii_retention_erasure(model) == ()


class TestPiiUndeclaredFlow:
    # frob:tests src/frob/strata/_pii.py::check_pii_undeclared_flow kind="unit"
    def test_matching_label_is_clean(self):
        model = KernelModel(
            nodes=(
                _node("store", "trusted", attrs=("pii=identifier.email",)),
                _node("sink", "trusted"),
            ),
            flows=(Flow(id="f", src="store", dst="sink", label="Pii"),),
        )
        assert check_pii_undeclared_flow(model) == ()

    # frob:tests src/frob/strata/_pii.py::check_pii_undeclared_flow kind="unit"
    def test_underlabeled_flow_fires_pii004(self):
        model = KernelModel(
            nodes=(
                _node("store", "trusted", attrs=("pii=identifier.email",)),
                _node("sink", "trusted"),
            ),
            flows=(Flow(id="f_leak", src="store", dst="sink", label="Public"),),
        )
        violations = check_pii_undeclared_flow(model)
        assert len(violations) == 1
        assert violations[0].rule == "PII004"
        assert violations[0].target == "f_leak"

    # frob:tests src/frob/strata/_pii.py::check_pii_undeclared_flow kind="unit"
    def test_secret_label_is_at_or_above_pii_and_is_clean(self):
        model = KernelModel(
            nodes=(
                _node("store", "trusted", attrs=("pii=identifier.email",)),
                _node("sink", "trusted"),
            ),
            flows=(Flow(id="f", src="store", dst="sink", label="Secret"),),
        )
        assert check_pii_undeclared_flow(model) == ()


class TestEvaluatePii:
    # frob:tests src/frob/strata/_pii.py::evaluate_pii kind="unit"
    def test_clean_model_is_ok_and_empty(self):
        model = KernelModel(nodes=(_node("a", "trusted"),))
        result = evaluate_pii(model)
        assert result.is_ok
        assert result.danger_ok.violations == ()

    # frob:tests src/frob/strata/_pii.py::evaluate_pii kind="unit"
    def test_joins_every_check(self):
        model = KernelModel(
            nodes=(
                _node("client", "foreign"),
                _node("store", "trusted", attrs=("pii=nonsense.field",)),
            ),
            flows=(Flow(id="f_collect", src="client", dst="store", label="Pii"),),
        )
        result = evaluate_pii(model)
        assert result.is_ok
        rules = {v.rule for v in result.danger_ok.violations}
        assert "PII001" in rules  # malformed category
        assert "PII002" in rules  # boundary crossing, no protection
        assert "PII003" in rules  # no retention/erasure


class TestFrobSelfModelPiiPosture:
    """T-0154 self-model requirement: frob's own PII posture, declared
    EXPLICITLY, not left to silently fall out of `design/frob.strata`
    happening to have no `carries` statements. `docs/strata/threat.md`
    #compliance`'s own precedent for the zero case is `OutOfScopeRegulation`
    (mandatory owner+review on every exclusion) -- there is no `carries`
    equivalent to *not* write, since `carries` is additive-only (no
    kernel-level "explicitly zero PII" declaration exists), so the
    explicit half of the proof is this locked assertion: frob's own
    design, real tree, DOES carry zero PII beyond git author metadata
    (name/email in commit history, which is process/VCS metadata, not
    modeled application data -- outside `design/frob.strata`'s scope
    entirely, same as it is outside every other node's `attrs`)."""

    # frob:tests design/frob.strata kind="integration"
    def test_frob_design_declares_zero_pii(self):
        """`design/frob.strata` -- frob's own architecture -- carries no
        `pii=` attrs on any node: frob processes design/ticket/code text,
        not personal data, beyond git author name/email already recorded
        by git itself (outside this model's scope). Proving this is an
        explicit, checked assertion, not a silent absence (T-0154 ticket
        body: "proving the zero case counts and must be explicit, not
        silent") -- this test fails loudly the moment a future `carries`
        statement is added to any node/store here, forcing that addition
        to also justify itself against `evaluate_pii`."""
        pytest.importorskip("strata_core")
        root = Path(__file__).resolve().parents[3]
        text = (root / "design" / "frob.strata").read_text(encoding="utf-8")
        module = parse_module(text)
        assert module.is_ok, f"design/frob.strata failed to parse: {module.err}"
        model = elaborate(module.danger_ok)
        assert model.is_ok, f"design/frob.strata failed to elaborate: {model.err}"
        for node in model.danger_ok.nodes:
            assert not node_carries_pii(node), (
                f"design/frob.strata: node {node.id} unexpectedly carries pii "
                f"{node_pii_tags(node)} -- frob's PII posture is declared zero; "
                "either this is wrong (frob really does model PII now, update "
                "this test's expectation deliberately) or the carries statement "
                "should not be there"
            )

    # frob:tests src/frob/strata/_pii.py::evaluate_pii kind="integration"
    def test_frob_design_pii_audit_is_clean(self):
        """The zero-PII posture also means `evaluate_pii` proves clean over
        frob's own design -- redundant with `test_frob_design_declares_zero_
        pii` in the zero-tags case, but this is the assertion that stays
        meaningful once frob's posture ever legitimately changes to
        non-zero (at which point PII002/003/004 must still all discharge)."""
        pytest.importorskip("strata_core")
        root = Path(__file__).resolve().parents[3]
        text = (root / "design" / "frob.strata").read_text(encoding="utf-8")
        model = elaborate(parse_module(text).danger_ok).danger_ok
        result = evaluate_pii(model)
        assert result.is_ok
        assert result.danger_ok.violations == ()
