"""REL35x DISTRIBUTED-TRANSACTION-ACROSS-SERVICES unit coverage (T-0655,
`frob.strata._distributed_txn`) -- mirrors `test_txn.py`'s `tmp_path`
real-file convention for proof-against-code (bind_code-backed, so it
needs a real file tree, not just an in-memory `KernelModel`)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import Flow, KernelModel, Node, Waiver
from frob.strata._distributed_txn import (
    REL_MISSING_SAGA,
    REL_UNPROVEN_SAGA,
    check_distributed_txn_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingSaga:
    # frob:tests \
    # tests/unit/strata/test_distributed_txn.py::TestMissingSaga.test_multi_service_wri\
    # te_op_without_saga_fires
    def test_multi_service_write_op_without_saga_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="checkout", trust="trusted"),
                Node(id="inventory_svc", trust="trusted"),
                Node(id="billing_svc", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="checkout", dst="inventory_svc"),
                Flow(id="f2", src="checkout", dst="billing_svc"),
            ),
        )
        result = check_distributed_txn_obligations(model, tmp_path)
        assert result.is_ok
        missing = [v for v in result.danger_ok.violations if v.rule == REL_MISSING_SAGA]
        assert {v.node for v in missing} == {"checkout"}

    # frob:tests \
    # tests/unit/strata/test_distributed_txn.py::TestMissingSaga.test_transaction_attr_\
    # alone_does_not_discharge
    def test_transaction_attr_alone_does_not_discharge(self, tmp_path: Path):
        # Unlike REL300, a bare `transaction` attr does NOT discharge
        # REL350 -- only `saga` does (module docstring).
        model = KernelModel(
            nodes=(
                Node(id="checkout", trust="trusted", attrs=("transaction",)),
                Node(id="inventory_svc", trust="trusted"),
                Node(id="billing_svc", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="checkout", dst="inventory_svc"),
                Flow(id="f2", src="checkout", dst="billing_svc"),
            ),
        )
        result = check_distributed_txn_obligations(model, tmp_path)
        assert result.is_ok
        missing = [v for v in result.danger_ok.violations if v.rule == REL_MISSING_SAGA]
        assert {v.node for v in missing} == {"checkout"}

    # frob:tests \
    # tests/unit/strata/test_distributed_txn.py::TestMissingSaga.test_single_write_and_\
    # discharged_clean
    def test_single_write_and_discharged_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="single_writer", trust="trusted"),
                Node(id="downstream", trust="trusted"),
                Node(id="checkout", trust="trusted", attrs=("saga",)),
                Node(id="inventory_svc", trust="trusted"),
                Node(id="billing_svc", trust="trusted"),
            ),
            flows=(
                Flow(id="f0", src="single_writer", dst="downstream"),
                Flow(id="f1", src="checkout", dst="inventory_svc"),
                Flow(id="f2", src="checkout", dst="billing_svc"),
            ),
        )
        result = check_distributed_txn_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_SAGA
        ]

    # frob:tests \
    # tests/unit/strata/test_distributed_txn.py::TestMissingSaga.test_waiver_discharges\
    # _finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL350",
                            reason="legacy multi-write op, saga tracked in T-9910",
                        ),
                    ),
                ),
                Node(id="inventory_svc", trust="trusted"),
                Node(id="billing_svc", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="checkout", dst="inventory_svc"),
                Flow(id="f2", src="checkout", dst="billing_svc"),
            ),
        )
        result = check_distributed_txn_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_SAGA]
        assert {v.node for v in report.waived if v.rule == REL_MISSING_SAGA} == {
            "checkout"
        }


class TestUnprovenSaga:
    # frob:tests \
    # tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga.test_declared_with_no\
    # _code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def checkout():\n    return commit()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout",
                    trust="trusted",
                    attrs=("saga", "code=src/widget/**"),
                ),
                Node(id="inventory_svc", trust="trusted"),
                Node(id="billing_svc", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="checkout", dst="inventory_svc"),
                Flow(id="f2", src="checkout", dst="billing_svc"),
            ),
        )
        result = check_distributed_txn_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_SAGA
        ]
        assert {v.node for v in violations} == {"checkout"}

    # frob:tests \
    # tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga.test_declared_with_re\
    # al_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def checkout():\n"
            "    try:\n"
            "        commit()\n"
            "    except Failure:\n"
            "        compensate()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="checkout",
                    trust="trusted",
                    attrs=("saga", "code=src/widget/**"),
                ),
                Node(id="inventory_svc", trust="trusted"),
                Node(id="billing_svc", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="checkout", dst="inventory_svc"),
                Flow(id="f2", src="checkout", dst="billing_svc"),
            ),
        )
        result = check_distributed_txn_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_SAGA
        ]

    # frob:tests \
    # tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga.test_declared_with_no\
    # _bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(id="checkout", trust="trusted", attrs=("saga",)),
                Node(id="inventory_svc", trust="trusted"),
                Node(id="billing_svc", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="checkout", dst="inventory_svc"),
                Flow(id="f2", src="checkout", dst="billing_svc"),
            ),
        )
        result = check_distributed_txn_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_SAGA
        ]
