"""REL26x BACKPRESSURE-obligation family unit coverage (T-0646,
`frob.strata._backpressure`) -- mirrors `test_retry.py`'s `tmp_path`
real-file convention for proof-against-code (bind_code-backed, so it
needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._backpressure import (
    REL_MISSING_BOUNDED_INTAKE,
    REL_UNPROVEN_BOUNDED_INTAKE,
    check_backpressure_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingBoundedIntake:
    # frob:tests \
    # tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake.test_queue_node_\
    # without_bounded_intake_fires
    def test_queue_node_without_bounded_intake_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="ingest_queue", trust="trusted", attrs=("queue",)),),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_BOUNDED_INTAKE
        ]
        assert {v.node for v in missing} == {"ingest_queue"}

    # frob:tests \
    # tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake.test_consumer_no\
    # de_without_bounded_intake_fires
    def test_consumer_node_without_bounded_intake_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="worker", trust="trusted", attrs=("consumer",)),),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_BOUNDED_INTAKE
        ]
        assert {v.node for v in missing} == {"worker"}

    # frob:tests \
    # tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake.test_discharged_\
    # and_non_queue_nodes_clean
    def test_discharged_and_non_queue_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "bounded_intake"),
                ),
                Node(id="plain_service", trust="trusted"),
            ),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_BOUNDED_INTAKE
        ]

    # frob:tests \
    # tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake.test_waiver_disc\
    # harges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue",),
                    waives=(
                        Waiver(
                            rule="REL260",
                            reason="legacy queue, bounded intake tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v for v in report.violations if v.rule == REL_MISSING_BOUNDED_INTAKE
        ]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_BOUNDED_INTAKE
        } == {"ingest_queue"}


class TestUnprovenBoundedIntake:
    # frob:tests \
    # tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake.test_declared_w\
    # ith_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def consume():\n    return drain()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "bounded_intake", "code=src/widget/**"),
                ),
            ),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_INTAKE
        ]
        assert {v.node for v in violations} == {"ingest_queue"}

    # frob:tests \
    # tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake.test_declared_w\
    # ith_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "import queue\nq = queue.Queue(maxsize=100)\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "bounded_intake", "code=src/widget/**"),
                ),
            ),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_INTAKE
        ]

    # frob:tests \
    # tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake.test_declared_w\
    # ith_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest_queue",
                    trust="trusted",
                    attrs=("queue", "bounded_intake"),
                ),
            ),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_INTAKE
        ]
