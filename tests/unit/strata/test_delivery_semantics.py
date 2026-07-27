"""REL33x DELIVERY-SEMANTICS-obligation family unit coverage (T-0652,
`frob.strata._delivery_semantics`) -- mirrors `test_message_schema.py`'s
`tmp_path` real-file convention for proof-against-code (bind_code-backed,
so it needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._delivery_semantics import (
    REL_MISSING_DELIVERY_SEMANTICS,
    REL_UNPROVEN_DELIVERY_SEMANTICS,
    check_delivery_semantics_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingDeliverySemantics:
    # frob:tests \
    # tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics.test_q\
    # ueue_node_without_delivery_semantics_fires
    def test_queue_node_without_delivery_semantics_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="ingest_queue", trust="trusted", attrs=("queue",)),),
        )
        result = check_delivery_semantics_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_DELIVERY_SEMANTICS
        ]
        assert {v.node for v in missing} == {"ingest_queue"}

    # frob:tests \
    # tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics.test_i\
    # nvalid_delivery_value_fires
    def test_invalid_delivery_value_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "delivery=maybe-once"),
                ),
            ),
        )
        result = check_delivery_semantics_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_DELIVERY_SEMANTICS
        ]
        assert {v.node for v in missing} == {"ingest_queue"}

    # frob:tests \
    # tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics.test_d\
    # ischarged_and_non_queue_nodes_clean
    def test_discharged_and_non_queue_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "delivery=at_least_once"),
                ),
                Node(id="plain_service", trust="trusted"),
            ),
        )
        result = check_delivery_semantics_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_DELIVERY_SEMANTICS
        ]

    # frob:tests \
    # tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics.test_w\
    # aiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue",),
                    waives=(
                        Waiver(
                            rule="REL330",
                            reason="legacy queue, semantics tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_delivery_semantics_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v for v in report.violations if v.rule == REL_MISSING_DELIVERY_SEMANTICS
        ]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_DELIVERY_SEMANTICS
        } == {"ingest_queue"}


class TestUnprovenDeliverySemantics:
    # frob:tests \
    # tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics.test_\
    # declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def consume():\n    return handle()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "delivery=exactly_once", "code=src/widget/**"),
                ),
            ),
        )
        result = check_delivery_semantics_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_DELIVERY_SEMANTICS
        ]
        assert {v.node for v in violations} == {"ingest_queue"}

    # frob:tests \
    # tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics.test_\
    # declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def consume(msg):\n"
            "    key = idempotency_key(msg)\n"
            "    return handle(msg, key)\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "delivery=exactly_once", "code=src/widget/**"),
                ),
            ),
        )
        result = check_delivery_semantics_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_DELIVERY_SEMANTICS
        ]

    # frob:tests \
    # tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics.test_\
    # declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "delivery=at_least_once"),
                ),
            ),
        )
        result = check_delivery_semantics_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_DELIVERY_SEMANTICS
        ]
