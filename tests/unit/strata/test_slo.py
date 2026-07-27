"""REL28x golden-signal-SLO-obligation family unit coverage (T-0648,
`frob.strata._slo`) -- mirrors `test_retry.py`'s `tmp_path` real-file
convention for proof-against-code (bind_code-backed, so it needs a real
file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._slo import (
    REL_MISSING_SLO,
    REL_UNPROVEN_SLO,
    check_slo_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingSlo:
    # frob:tests \
    # tests/unit/strata/test_slo.py::TestMissingSlo.test_service_node_without_slo_fires
    def test_service_node_without_slo_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="checkout_svc", trust="trusted", attrs=("service",)),),
        )
        result = check_slo_obligations(model, tmp_path)
        assert result.is_ok
        missing = [v for v in result.danger_ok.violations if v.rule == REL_MISSING_SLO]
        assert {v.node for v in missing} == {"checkout_svc"}

    # frob:tests \
    # tests/unit/strata/test_slo.py::TestMissingSlo.test_only_slo_or_only_error_budget_\
    # still_fires
    def test_only_slo_or_only_error_budget_still_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="half_a", trust="trusted", attrs=("service", "slo")),
                Node(id="half_b", trust="trusted", attrs=("unit", "error_budget")),
            ),
        )
        result = check_slo_obligations(model, tmp_path)
        assert result.is_ok
        missing = {
            v.node for v in result.danger_ok.violations if v.rule == REL_MISSING_SLO
        }
        assert missing == {"half_a", "half_b"}

    # frob:tests \
    # tests/unit/strata/test_slo.py::TestMissingSlo.test_discharged_and_non_service_nod\
    # es_clean
    def test_discharged_and_non_service_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout_svc",
                    trust="trusted",
                    attrs=("service", "slo", "error_budget"),
                ),
                Node(id="plain_lib", trust="trusted"),
            ),
        )
        result = check_slo_obligations(model, tmp_path)
        assert result.is_ok
        assert not [v for v in result.danger_ok.violations if v.rule == REL_MISSING_SLO]

    # frob:tests \
    # tests/unit/strata/test_slo.py::TestMissingSlo.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout_svc",
                    trust="trusted",
                    attrs=("service",),
                    waives=(
                        Waiver(
                            rule="REL280",
                            reason="legacy service, SLO tracked in T-9912",
                        ),
                    ),
                ),
            ),
        )
        result = check_slo_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_SLO]
        assert {v.node for v in report.waived if v.rule == REL_MISSING_SLO} == {
            "checkout_svc"
        }


class TestUnprovenSlo:
    # frob:tests \
    # tests/unit/strata/test_slo.py::TestUnprovenSlo.test_declared_with_no_code_evidenc\
    # e_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def handle():\n    return ok()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout_svc",
                    trust="trusted",
                    attrs=("service", "slo", "error_budget", "code=src/widget/**"),
                ),
            ),
        )
        result = check_slo_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_SLO
        ]
        assert {v.node for v in violations} == {"checkout_svc"}

    # frob:tests \
    # tests/unit/strata/test_slo.py::TestUnprovenSlo.test_declared_with_real_code_evide\
    # nce_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "ERROR_BUDGET = 0.001\ndef handle():\n    return ok()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout_svc",
                    trust="trusted",
                    attrs=("service", "slo", "error_budget", "code=src/widget/**"),
                ),
            ),
        )
        result = check_slo_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_SLO
        ]

    # frob:tests \
    # tests/unit/strata/test_slo.py::TestUnprovenSlo.test_declared_with_no_bound_code_i\
    # s_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout_svc",
                    trust="trusted",
                    attrs=("service", "slo", "error_budget"),
                ),
            ),
        )
        result = check_slo_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_SLO
        ]
