"""REL32x MESSAGE-SCHEMA-VERSION-obligation family unit coverage (T-0651,
`frob.strata._message_schema`) -- mirrors `test_backpressure.py`'s
`tmp_path` real-file convention for proof-against-code (bind_code-backed,
so it needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._message_schema import (
    REL_MISSING_SCHEMA_VERSION,
    REL_UNPROVEN_SCHEMA_VERSION,
    check_message_schema_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingSchemaVersion:
    # frob:tests tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion.test_event_node_without_schema_version_fires
    def test_event_node_without_schema_version_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="order_placed", trust="trusted", attrs=("event",)),),
        )
        result = check_message_schema_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_SCHEMA_VERSION
        ]
        assert {v.node for v in missing} == {"order_placed"}

    # frob:tests tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion.test_queue_node_without_schema_version_fires
    def test_queue_node_without_schema_version_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="ingest_queue", trust="trusted", attrs=("queue",)),),
        )
        result = check_message_schema_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_SCHEMA_VERSION
        ]
        assert {v.node for v in missing} == {"ingest_queue"}

    # frob:tests tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion.test_discharged_and_non_event_queue_nodes_clean
    def test_discharged_and_non_event_queue_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="order_placed",
                    trust="trusted",
                    attrs=("event", "schema_version"),
                ),
                Node(id="plain_service", trust="trusted"),
            ),
        )
        result = check_message_schema_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_SCHEMA_VERSION
        ]

    # frob:tests tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="order_placed",
                    trust="trusted",
                    attrs=("event",),
                    waives=(
                        Waiver(
                            rule="REL320",
                            reason="legacy event, versioning tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_message_schema_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v for v in report.violations if v.rule == REL_MISSING_SCHEMA_VERSION
        ]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_SCHEMA_VERSION
        } == {"order_placed"}


class TestUnprovenSchemaVersion:
    # frob:tests tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def publish():\n    return emit()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="order_placed",
                    trust="trusted",
                    attrs=("event", "schema_version", "code=src/widget/**"),
                ),
            ),
        )
        result = check_message_schema_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_SCHEMA_VERSION
        ]
        assert {v.node for v in violations} == {"order_placed"}

    # frob:tests tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "schema_version = 3\n\ndef publish(event):\n    return emit(event)\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="order_placed",
                    trust="trusted",
                    attrs=("event", "schema_version", "code=src/widget/**"),
                ),
            ),
        )
        result = check_message_schema_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_SCHEMA_VERSION
        ]

    # frob:tests tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="order_placed",
                    trust="trusted",
                    attrs=("event", "schema_version"),
                ),
            ),
        )
        result = check_message_schema_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_SCHEMA_VERSION
        ]
