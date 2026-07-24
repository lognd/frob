"""REL29x SINGLE-SOURCE-OF-TRUTH-obligation family unit coverage
(T-0649, `frob.strata._ssot`) -- mirrors `test_retry.py`'s `tmp_path`
real-file convention for proof-against-code (bind_code-backed, so it
needs a real file tree, not just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import Flow, KernelModel, Node, Waiver
from frob.strata._ssot import (
    REL_MISSING_OWNER,
    REL_UNPROVEN_OWNER,
    check_ssot_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingOwner:
    # frob:tests tests/unit/strata/test_ssot.py::TestMissingOwner.test_multi_writer_store_without_owner_fires
    def test_multi_writer_store_without_owner_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="orders_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        missing = [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_OWNER
        ]
        assert {v.node for v in missing} == {"orders_db"}

    # frob:tests tests/unit/strata/test_ssot.py::TestMissingOwner.test_single_writer_store_clean
    def test_single_writer_store_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="orders_db", trust="trusted"),
            ),
            flows=(Flow(id="f_a", src="svc_a", dst="orders_db"),),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_OWNER
        ]

    # frob:tests tests/unit/strata/test_ssot.py::TestMissingOwner.test_owner_attr_discharges
    def test_owner_attr_discharges(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="orders_db", trust="trusted", attrs=("owner",)),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_OWNER
        ]

    # frob:tests tests/unit/strata/test_ssot.py::TestMissingOwner.test_reconciliation_attr_discharges
    def test_reconciliation_attr_discharges(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="orders_db", trust="trusted", attrs=("reconciliation",)),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_MISSING_OWNER
        ]

    # frob:tests tests/unit/strata/test_ssot.py::TestMissingOwner.test_empty_store_ids_emits_nothing
    def test_empty_store_ids_emits_nothing(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="orders_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset(), tmp_path)
        assert result.is_ok
        assert result.danger_ok.violations == ()

    # frob:tests tests/unit/strata/test_ssot.py::TestMissingOwner.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(
                    id="orders_db",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL290",
                            reason="legacy shared store, owner tracked in T-9913",
                        ),
                    ),
                ),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_OWNER]
        assert {v.node for v in report.waived if v.rule == REL_MISSING_OWNER} == {
            "orders_db"
        }


class TestUnprovenOwner:
    # frob:tests tests/unit/strata/test_ssot.py::TestUnprovenOwner.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def handle():\n    return ok()\n")
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(
                    id="orders_db",
                    trust="trusted",
                    attrs=("owner", "code=src/widget/**"),
                ),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_OWNER
        ]
        assert {v.node for v in violations} == {"orders_db"}

    # frob:tests tests/unit/strata/test_ssot.py::TestUnprovenOwner.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def handle():\n    return single_writer_lock()\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(
                    id="orders_db",
                    trust="trusted",
                    attrs=("owner", "code=src/widget/**"),
                ),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_OWNER
        ]

    # frob:tests tests/unit/strata/test_ssot.py::TestUnprovenOwner.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="orders_db", trust="trusted", attrs=("owner",)),
            ),
            flows=(
                Flow(id="f_a", src="svc_a", dst="orders_db"),
                Flow(id="f_b", src="svc_b", dst="orders_db"),
            ),
        )
        result = check_ssot_obligations(model, frozenset({"orders_db"}), tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_OWNER
        ]
