"""REL2xx TIMEOUT-obligation family litmus + unit coverage (T-0640,
`frob.strata._reliability`) -- mirrors `test_contention.py`'s real
`strata_core` parse -> elaborate round-trip discipline for the REL200
missing-timeout/waiver shapes, plus `test_selfconform.py`'s `tmp_path`
real-file convention for REL201's proof-against-code (bind_code-backed,
so it needs a real file tree, not just a parsed `.strata` fixture).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Module, Node, elaborate, parse_module
from frob.strata._reliability import (
    REL_MISSING_TIMEOUT,
    REL_UNPROVEN_TIMEOUT,
    check_reliability_timeouts,
)

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load(filename: str) -> tuple[Module, KernelModel]:
    """Parse+elaborate one `.strata` fixture under `litmus/`."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    model = elaborate(module).danger_ok
    return module, model


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingTimeout:
    # frob:tests tests/unit/strata/test_reliability.py::TestMissingTimeout.test_flow_without_timeout_fires
    def test_flow_without_timeout_fires(self, tmp_path: Path):
        _module, model = _load("reliability_timeout_missing_vuln.strata")
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        missing = [v for v in report.violations if v.rule == REL_MISSING_TIMEOUT]
        sub_targets = {v.sub_target for v in missing}
        assert sub_targets == {"f_missing"}
        assert all(v.node == "caller" for v in missing)
        # f_ok (declares `attr timeout;`) must not spuriously fire.
        assert "f_ok" not in sub_targets

    # frob:tests tests/unit/strata/test_reliability.py::TestMissingTimeout.test_discharged_and_exempt_flows_clean
    def test_discharged_and_exempt_flows_clean(self, tmp_path: Path):
        _module, model = _load("reliability_timeout_clean.strata")
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_TIMEOUT]

    # frob:tests tests/unit/strata/test_reliability.py::TestMissingTimeout.test_waiver_on_one_flow_keeps_sibling_flow_finding
    def test_waiver_on_one_flow_keeps_sibling_flow_finding(self, tmp_path: Path):
        _module, model = _load("reliability_timeout_waived.strata")
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        kept = {v.sub_target for v in report.violations if v.rule == REL_MISSING_TIMEOUT}
        waived = {v.sub_target for v in report.waived if v.rule == REL_MISSING_TIMEOUT}
        assert kept == {"f_other"}
        assert waived == {"f_missing"}


class TestUnprovenTimeout:
    """REL201 proof-against-code needs a real file tree bound via
    `bind_code` -- a parsed `.strata` fixture alone cannot exercise it, so
    these build a `KernelModel` directly (the `test_selfconform.py`/
    `test_crash.py` precedent) against `tmp_path`."""

    # frob:tests tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_declared_timeout_with_no_code_evidence_fires
    def test_declared_timeout_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def call():\n    return remote()\n")
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted", attrs=("code=src/widget/**",)),
                Node(id="worker", trust="trusted"),
            ),
            flows=(
                {
                    "id": "f1",
                    "src": "caller",
                    "dst": "worker",
                    "attrs": ("timeout",),
                },
            ),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]
        assert {v.sub_target for v in violations} == {"f1"}
        assert violations[0].node == "caller"

    # frob:tests tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_declared_timeout_with_real_code_evidence_discharges
    def test_declared_timeout_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def call():\n    return remote(timeout=30)\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted", attrs=("code=src/widget/**",)),
                Node(id="worker", trust="trusted"),
            ),
            flows=(
                {
                    "id": "f1",
                    "src": "caller",
                    "dst": "worker",
                    "attrs": ("timeout",),
                },
            ),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]

    # frob:tests tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        # caller declares no `code=` glob at all -- REL201 cannot check it,
        # so it must stay silent rather than guess at a violation.
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted"),
            ),
            flows=(
                {
                    "id": "f1",
                    "src": "caller",
                    "dst": "worker",
                    "attrs": ("timeout",),
                },
            ),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]
