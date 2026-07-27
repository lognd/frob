"""REL24x FALLBACK-obligation family unit coverage (T-0643,
`frob.strata._fallback`) -- mirrors `test_circuit_breaker.py`'s `tmp_path`
real-file convention for proof-against-code.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._fallback import (
    REL_MISSING_FALLBACK,
    REL_UNPROVEN_FALLBACK,
    check_fallback_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingFallback:
    # frob:tests \
    # tests/unit/strata/test_fallback.py::TestMissingFallback.test_critical_node_withou\
    # t_fallback_fires
    def test_critical_node_without_fallback_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="payments", trust="untrusted", attrs=("critical",)),),
        )
        result = check_fallback_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_FALLBACK
        ]
        assert {v.node for v in missing} == {"payments"}

    # frob:tests \
    # tests/unit/strata/test_fallback.py::TestMissingFallback.test_discharged_and_non_c\
    # ritical_nodes_clean
    def test_discharged_and_non_critical_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="payments",
                    trust="untrusted",
                    attrs=("critical", "fallback"),
                ),
                Node(id="internal", trust="trusted"),
            ),
        )
        result = check_fallback_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_FALLBACK
        ]

    # frob:tests \
    # tests/unit/strata/test_fallback.py::TestMissingFallback.test_waiver_on_one_node_k\
    # eeps_sibling_node_finding
    def test_waiver_on_one_node_keeps_sibling_node_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="legacy_gateway",
                    trust="untrusted",
                    attrs=("critical",),
                    waives=(
                        Waiver(
                            rule="REL240",
                            reason="legacy gateway, tracked in T-0643-followup",
                        ),
                    ),
                ),
                Node(id="other_gateway", trust="untrusted", attrs=("critical",)),
            ),
        )
        result = check_fallback_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        kept = {v.node for v in report.violations if v.rule == REL_MISSING_FALLBACK}
        waived = {v.node for v in report.waived if v.rule == REL_MISSING_FALLBACK}
        assert kept == {"other_gateway"}
        assert waived == {"legacy_gateway"}


class TestUnprovenFallback:
    # frob:tests \
    # tests/unit/strata/test_fallback.py::TestUnprovenFallback.test_declared_with_no_co\
    # de_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/pay/_client.py", "def call():\n    return remote()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="payments",
                    trust="untrusted",
                    attrs=("critical", "fallback", "code=src/pay/**"),
                ),
            ),
        )
        result = check_fallback_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_FALLBACK
        ]
        assert {v.node for v in violations} == {"payments"}

    # frob:tests \
    # tests/unit/strata/test_fallback.py::TestUnprovenFallback.test_declared_with_real_\
    # code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/pay/_client.py",
            "def call():\n    try:\n        return remote()\n"
            "    except RemoteError:\n        return fallback()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="payments",
                    trust="untrusted",
                    attrs=("critical", "fallback", "code=src/pay/**"),
                ),
            ),
        )
        result = check_fallback_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_FALLBACK
        ]

    # frob:tests \
    # tests/unit/strata/test_fallback.py::TestUnprovenFallback.test_declared_with_no_bo\
    # und_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(id="payments", trust="untrusted", attrs=("critical", "fallback")),
            ),
        )
        result = check_fallback_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_FALLBACK
        ]
