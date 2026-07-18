"""`std.lint` litmus fixture coverage (T-0155, mirroring T-0154's
`test_litmus_pii.py` discipline): the vuln/hardened pair round-trips
through the real `strata_core` parser (`parse_module -> elaborate ->
evaluate_lint`), never a hand-built `KernelModel` for the surface-syntax
half of the proof (that precedent stays in `test_lint.py`'s unit-level
checks)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._lint import evaluate_lint

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestLintVulnLitmus:
    # frob:tests src/frob/strata/_lint.py::evaluate_lint kind="unit"
    def test_vuln_fires_every_rule(self):
        model = _load_model("lint_vuln.strata")
        report = evaluate_lint(model)
        assert report.is_ok
        rules = {v.rule for v in report.danger_ok.violations}
        assert rules == {"LINT001", "LINT002", "LINT003", "LINT004", "LINT005"}

    # frob:tests src/frob/strata/_lint.py::check_lint_rate_limit kind="unit"
    def test_vuln_lint001_names_the_open_flow(self):
        model = _load_model("lint_vuln.strata")
        report = evaluate_lint(model)
        hits = [v for v in report.danger_ok.violations if v.rule == "LINT001"]
        assert len(hits) == 1
        assert hits[0].target == "f_open"

    # frob:tests src/frob/strata/_lint.py::check_lint_surge_capacity_bound kind="unit"
    def test_vuln_lint003_names_the_scenario(self):
        model = _load_model("lint_vuln.strata")
        report = evaluate_lint(model)
        hits = [v for v in report.danger_ok.violations if v.rule == "LINT003"]
        assert len(hits) == 1
        assert hits[0].target == "surge_s"

    # frob:tests src/frob/strata/_lint.py::check_lint_kill_switch kind="unit"
    def test_vuln_lint004_names_the_store(self):
        model = _load_model("lint_vuln.strata")
        report = evaluate_lint(model)
        hits = [v for v in report.danger_ok.violations if v.rule == "LINT004"]
        assert len(hits) == 1
        assert hits[0].target == "store_data"


class TestLintHardenedLitmus:
    # frob:tests src/frob/strata/_lint.py::evaluate_lint kind="unit"
    def test_hardened_discharges_every_fired_obligation(self):
        model = _load_model("lint_hardened.strata")
        report = evaluate_lint(model)
        assert report.is_ok
        assert report.danger_ok.violations == ()
