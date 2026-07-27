"""REL30x TRANSACTIONAL-BOUNDARY-obligation family unit coverage
(T-0650, `frob.strata._txn`) -- mirrors `test_ssot.py`'s `tmp_path`
real-file convention for proof-against-code (bind_code-backed, so it
needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import Flow, KernelModel, Node, Waiver
from frob.strata._txn import (
    REL_MISSING_TXN_BOUNDARY,
    REL_UNPROVEN_TXN_BOUNDARY,
    check_txn_boundary_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingTxnBoundary:
    # frob:tests tests/unit/strata/test_txn.py::TestMissingTxnBoundary.test_multi_store_write_op_without_boundary_fires
    def test_multi_store_write_op_without_boundary_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db", "ledger_db"}), tmp_path
        )
        assert result.is_ok
        missing = [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_TXN_BOUNDARY
        ]
        assert {v.node for v in missing} == {"svc_a"}

    # frob:tests tests/unit/strata/test_txn.py::TestMissingTxnBoundary.test_single_store_write_op_clean
    def test_single_store_write_op_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="orders_db", trust="trusted"),
            ),
            flows=(Flow(id="f_a", src="svc_a", dst="orders_db"),),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db"}), tmp_path
        )
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_TXN_BOUNDARY
        ]

    # frob:tests tests/unit/strata/test_txn.py::TestMissingTxnBoundary.test_transaction_attr_discharges
    def test_transaction_attr_discharges(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted", attrs=("transaction",)),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db", "ledger_db"}), tmp_path
        )
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_TXN_BOUNDARY
        ]

    # frob:tests tests/unit/strata/test_txn.py::TestMissingTxnBoundary.test_saga_attr_discharges
    def test_saga_attr_discharges(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted", attrs=("saga",)),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db", "ledger_db"}), tmp_path
        )
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_TXN_BOUNDARY
        ]

    # frob:tests tests/unit/strata/test_txn.py::TestMissingTxnBoundary.test_empty_store_ids_emits_nothing
    def test_empty_store_ids_emits_nothing(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(model, frozenset(), tmp_path)
        assert result.is_ok
        assert result.danger_ok.violations == ()

    # frob:tests tests/unit/strata/test_txn.py::TestMissingTxnBoundary.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="svc_a",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL300",
                            reason="legacy multi-write op, txn tracked in T-9914",
                        ),
                    ),
                ),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db", "ledger_db"}), tmp_path
        )
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_TXN_BOUNDARY]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_TXN_BOUNDARY
        } == {"svc_a"}


class TestUnprovenTxnBoundary:
    # frob:tests tests/unit/strata/test_txn.py::TestUnprovenTxnBoundary.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def handle():\n    return ok()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="svc_a",
                    trust="trusted",
                    attrs=("transaction", "code=src/widget/**"),
                ),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db", "ledger_db"}), tmp_path
        )
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_TXN_BOUNDARY
        ]
        assert {v.node for v in violations} == {"svc_a"}

    # frob:tests tests/unit/strata/test_txn.py::TestUnprovenTxnBoundary.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def handle():\n    return two_phase_commit()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="svc_a",
                    trust="trusted",
                    attrs=("transaction", "code=src/widget/**"),
                ),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db", "ledger_db"}), tmp_path
        )
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_TXN_BOUNDARY
        ]

    # frob:tests tests/unit/strata/test_txn.py::TestUnprovenTxnBoundary.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted", attrs=("transaction",)),
                Node(id="orders_db", trust="trusted"),
                Node(id="ledger_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_a", dst="ledger_db"),
            ),
        )
        result = check_txn_boundary_obligations(
            model, frozenset({"orders_db", "ledger_db"}), tmp_path
        )
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_TXN_BOUNDARY
        ]
