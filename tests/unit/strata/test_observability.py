"""REL27x observability+correlation-obligation family unit coverage
(T-0647, `frob.strata._observability`) -- mirrors `test_retry.py`'s
`tmp_path` real-file convention for proof-against-code (bind_code-backed,
so it needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import Boundary, BoundaryDirection, Flow, KernelModel, Node, Waiver
from frob.strata._observability import (
    REL_MISSING_CORRELATION,
    REL_MISSING_OBSERVABILITY,
    REL_UNPROVEN_OBSERVABILITY,
    check_observability_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _boundary(flow_id: str) -> Boundary:
    return Boundary(
        id=f"b_{flow_id}",
        flow_id=flow_id,
        direction=BoundaryDirection.ENDORSE,
        from_level="foreign",
        to_level="authenticated",
    )


class TestMissingObservability:
    # frob:tests tests/unit/strata/test_observability.py::TestMissingObservability.test_boundary_flow_without_observability_fires
    def test_boundary_flow_without_observability_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="edge", trust="foreign"),
                Node(id="api", trust="authenticated"),
            ),
            flows=(Flow(id="f1", src="edge", dst="api"),),
            boundaries=(_boundary("f1"),),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_OBSERVABILITY
        ]
        assert {v.sub_target for v in missing} == {"f1"}
        assert missing[0].node == "edge"

    # frob:tests tests/unit/strata/test_observability.py::TestMissingObservability.test_discharged_and_non_boundary_flows_clean
    def test_discharged_and_non_boundary_flows_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="edge", trust="foreign"),
                Node(id="api", trust="authenticated"),
            ),
            flows=(
                Flow(id="f_ok", src="edge", dst="api", attrs=("observability",)),
                Flow(id="f_no_boundary", src="api", dst="edge"),
            ),
            boundaries=(_boundary("f_ok"),),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_OBSERVABILITY
        ]

    # frob:tests tests/unit/strata/test_observability.py::TestMissingObservability.test_waiver_on_one_flow_keeps_sibling_flow_finding
    def test_waiver_on_one_flow_keeps_sibling_flow_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="edge",
                    trust="foreign",
                    waives=(
                        Waiver(
                            rule="REL270:f_missing",
                            reason="dev-only debug hook, tracked in T-0647",
                        ),
                    ),
                ),
                Node(id="api", trust="authenticated"),
            ),
            flows=(
                Flow(id="f_missing", src="edge", dst="api"),
                Flow(id="f_other", src="edge", dst="api"),
            ),
            boundaries=(_boundary("f_missing"), _boundary("f_other")),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        kept = {
            v.sub_target
            for v in report.violations
            if v.rule == REL_MISSING_OBSERVABILITY
        }
        waived = {
            v.sub_target for v in report.waived if v.rule == REL_MISSING_OBSERVABILITY
        }
        assert kept == {"f_other"}
        assert waived == {"f_missing"}


class TestUnprovenObservability:
    # frob:tests tests/unit/strata/test_observability.py::TestUnprovenObservability.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def call():\n    return remote()\n")
        model = KernelModel(
            nodes=(
                Node(id="edge", trust="foreign", attrs=("code=src/widget/**",)),
                Node(id="api", trust="authenticated"),
            ),
            flows=(Flow(id="f1", src="edge", dst="api", attrs=("observability",)),),
            boundaries=(_boundary("f1"),),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_OBSERVABILITY
        ]
        assert {v.sub_target for v in violations} == {"f1"}

    # frob:tests tests/unit/strata/test_observability.py::TestUnprovenObservability.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "import logging\nlogger = logging.getLogger(__name__)\n"
            "def call():\n    logger.info('called')\n    return remote()\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="edge", trust="foreign", attrs=("code=src/widget/**",)),
                Node(id="api", trust="authenticated"),
            ),
            flows=(Flow(id="f1", src="edge", dst="api", attrs=("observability",)),),
            boundaries=(_boundary("f1"),),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_OBSERVABILITY
        ]

    # frob:tests tests/unit/strata/test_observability.py::TestUnprovenObservability.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(id="edge", trust="foreign"),
                Node(id="api", trust="authenticated"),
            ),
            flows=(Flow(id="f1", src="edge", dst="api", attrs=("observability",)),),
            boundaries=(_boundary("f1"),),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_OBSERVABILITY
        ]


class TestMissingCorrelation:
    # frob:tests tests/unit/strata/test_observability.py::TestMissingCorrelation.test_second_hop_without_correlation_fires
    def test_second_hop_without_correlation_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="trusted"),
                Node(id="api", trust="trusted"),
                Node(id="db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_first", src="web", dst="api"),
                Flow(id="f_second", src="api", dst="db"),
            ),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_CORRELATION
        ]
        assert {v.sub_target for v in violations} == {"f_second"}
        assert violations[0].node == "api"

    # frob:tests tests/unit/strata/test_observability.py::TestMissingCorrelation.test_first_hop_and_discharged_hop_clean
    def test_first_hop_and_discharged_hop_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="trusted"),
                Node(id="api", trust="trusted"),
                Node(id="db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_first", src="web", dst="api"),
                Flow(id="f_second", src="api", dst="db", attrs=("correlation",)),
            ),
        )
        result = check_observability_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_CORRELATION
        ]
