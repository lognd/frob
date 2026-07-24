"""REL23x CIRCUIT-BREAKER-obligation family unit coverage (T-0642,
`frob.strata._circuit_breaker`) -- mirrors `test_retry.py`'s `tmp_path`
real-file convention for proof-against-code (bind_code-backed, so it
needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._circuit_breaker import (
    REL_MISSING_CIRCUIT_BREAKER,
    REL_UNPROVEN_CIRCUIT_BREAKER,
    check_circuit_breaker_obligations,
    is_critical_dependency,
    is_external_dependency,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestPredicates:
    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestPredicates.test_is_external_dependency
    def test_is_external_dependency(self):
        assert is_external_dependency(("external",))
        assert not is_external_dependency(("critical",))

    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestPredicates.test_is_critical_dependency
    def test_is_critical_dependency(self):
        assert is_critical_dependency(("critical",))
        assert not is_critical_dependency(("external",))


class TestMissingCircuitBreaker:
    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker.test_external_node_without_circuit_breaker_fires
    def test_external_node_without_circuit_breaker_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(Node(id="payments", trust="untrusted", attrs=("external",)),),
        )
        result = check_circuit_breaker_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_CIRCUIT_BREAKER
        ]
        assert {v.node for v in missing} == {"payments"}

    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker.test_discharged_and_non_external_nodes_clean
    def test_discharged_and_non_external_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="payments",
                    trust="untrusted",
                    attrs=("external", "circuit_breaker"),
                ),
                Node(id="internal", trust="trusted"),
            ),
        )
        result = check_circuit_breaker_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_CIRCUIT_BREAKER
        ]

    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker.test_waiver_on_one_node_keeps_sibling_node_finding
    def test_waiver_on_one_node_keeps_sibling_node_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="legacy_gateway",
                    trust="untrusted",
                    attrs=("external",),
                    waives=(
                        Waiver(
                            rule="REL230",
                            reason="legacy gateway, tracked in T-0642-followup",
                        ),
                    ),
                ),
                Node(id="other_gateway", trust="untrusted", attrs=("external",)),
            ),
        )
        result = check_circuit_breaker_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        kept = {
            v.node for v in report.violations if v.rule == REL_MISSING_CIRCUIT_BREAKER
        }
        waived = {
            v.node for v in report.waived if v.rule == REL_MISSING_CIRCUIT_BREAKER
        }
        assert kept == {"other_gateway"}
        assert waived == {"legacy_gateway"}


class TestUnprovenCircuitBreaker:
    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/pay/_client.py", "def call():\n    return remote()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="payments",
                    trust="untrusted",
                    attrs=("external", "circuit_breaker", "code=src/pay/**"),
                ),
            ),
        )
        result = check_circuit_breaker_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_CIRCUIT_BREAKER
        ]
        assert {v.node for v in violations} == {"payments"}

    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/pay/_client.py",
            "breaker = CircuitBreaker(fail_max=5)\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="payments",
                    trust="untrusted",
                    attrs=("external", "circuit_breaker", "code=src/pay/**"),
                ),
            ),
        )
        result = check_circuit_breaker_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_CIRCUIT_BREAKER
        ]

    # frob:tests tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="payments",
                    trust="untrusted",
                    attrs=("external", "circuit_breaker"),
                ),
            ),
        )
        result = check_circuit_breaker_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_CIRCUIT_BREAKER
        ]
