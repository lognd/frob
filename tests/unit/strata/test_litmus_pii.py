"""`std.pii` litmus fixture coverage (T-0154, mirroring T-0145's per-CWE
litmus discipline): the vuln/hardened pair round-trips through the real
`strata_core` parser (`parse_module -> elaborate -> evaluate_pii`), never a
hand-built `KernelModel` for the surface-syntax half of the proof (that
precedent stays in `test_pii.py`'s unit-level checks, e.g. PII001's
malformed-category case, which has no discharge shape to litmus-test).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._pii import evaluate_pii

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestPiiVulnLitmus:
    # frob:tests src/frob/strata/_pii.py::evaluate_pii kind="unit"
    def test_vuln_fires_boundary_retention_and_lint(self):
        model = _load_model("pii_vuln.strata")
        report = evaluate_pii(model)
        assert report.is_ok
        rules = {v.rule for v in report.danger_ok.violations}
        assert rules == {"PII002", "PII003", "PII004"}

    # frob:tests src/frob/strata/_pii.py::check_pii_boundary_protection kind="unit"
    def test_vuln_pii002_names_the_crossing_flow(self):
        model = _load_model("pii_vuln.strata")
        report = evaluate_pii(model)
        pii002 = [v for v in report.danger_ok.violations if v.rule == "PII002"]
        assert len(pii002) == 1
        assert pii002[0].target == "f_collect"

    # frob:tests src/frob/strata/_pii.py::check_pii_retention_erasure kind="unit"
    def test_vuln_pii003_names_the_store(self):
        model = _load_model("pii_vuln.strata")
        report = evaluate_pii(model)
        pii003 = [v for v in report.danger_ok.violations if v.rule == "PII003"]
        assert len(pii003) == 1
        assert pii003[0].target == "store_users"

    # frob:tests src/frob/strata/_pii.py::check_pii_undeclared_flow kind="unit"
    def test_vuln_pii004_names_the_underlabeled_flow(self):
        model = _load_model("pii_vuln.strata")
        report = evaluate_pii(model)
        pii004 = [v for v in report.danger_ok.violations if v.rule == "PII004"]
        assert len(pii004) == 1
        assert pii004[0].target == "f_leak"


class TestPiiHardenedLitmus:
    # frob:tests src/frob/strata/_pii.py::evaluate_pii kind="unit"
    def test_hardened_discharges_every_fired_obligation(self):
        model = _load_model("pii_hardened.strata")
        report = evaluate_pii(model)
        assert report.is_ok
        assert report.danger_ok.violations == ()
