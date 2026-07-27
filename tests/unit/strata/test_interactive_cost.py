"""REL31x INTERACTIVE-COST-BOUND-obligation family unit coverage (T-0919,
`frob.strata._interactive_cost`) -- mirrors `test_backpressure.py`'s
`tmp_path` real-file convention for proof-against-code (bind_code-backed,
so it needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._interactive_cost import (
    REL_MISSING_BOUNDED_COST,
    REL_UNPROVEN_BOUNDED_COST,
    check_interactive_cost_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingBoundedCost:
    # frob:tests tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost.test_interactive_node_without_bounded_cost_fires
    def test_interactive_node_without_bounded_cost_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="ticket_done_report", trust="trusted", attrs=("interactive",)),
            ),
        )
        result = check_interactive_cost_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_BOUNDED_COST
        ]
        assert {v.node for v in missing} == {"ticket_done_report"}

    # frob:tests tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost.test_discharged_and_non_interactive_nodes_clean
    def test_discharged_and_non_interactive_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="ticket_done_report",
                    trust="trusted",
                    attrs=("interactive", "bounded_cost"),
                ),
                Node(id="background_job", trust="trusted"),
            ),
        )
        result = check_interactive_cost_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_BOUNDED_COST
        ]

    # frob:tests tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="ticket_done_report",
                    trust="trusted",
                    attrs=("interactive",),
                    waives=(
                        Waiver(
                            rule="REL310",
                            reason="legacy flow, cost bound tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_interactive_cost_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_BOUNDED_COST]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_BOUNDED_COST
        } == {"ticket_done_report"}


class TestUnprovenBoundedCost:
    # frob:tests tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def spawn_twice():\n    a = run_check()\n    b = run_check()\n"
            "    return a, b\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="ticket_done_report",
                    trust="trusted",
                    attrs=("interactive", "bounded_cost", "code=src/widget/**"),
                ),
            ),
        )
        result = check_interactive_cost_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_COST
        ]
        assert {v.node for v in violations} == {"ticket_done_report"}

    # frob:tests tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def spawn_once():\n    shared_spawn = _shared_check_spawn_fn()\n"
            "    return shared_spawn(), shared_spawn()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="ticket_done_report",
                    trust="trusted",
                    attrs=("interactive", "bounded_cost", "code=src/widget/**"),
                ),
            ),
        )
        result = check_interactive_cost_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_COST
        ]

    # frob:tests tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="ticket_done_report",
                    trust="trusted",
                    attrs=("interactive", "bounded_cost"),
                ),
            ),
        )
        result = check_interactive_cost_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_COST
        ]
