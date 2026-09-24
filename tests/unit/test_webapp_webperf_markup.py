"""frob.webapp._webperf_markup coverage (T-5371): WEBPERF101-106/108
markup-level Core Web Vitals rule-id wiring, one positive + one negative
fixture per rule id under tests/fixtures/webapp/webperf1xx/markup/.

frob:ticket T-5371
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.webapp._detect import FrameworkKind
from frob.webapp._webperf_markup import webperf_markup_findings, websec_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "webperf1xx"
    / "markup"
)

_CASES = [
    ("webperf101_positive", "WEBPERF101", True),
    ("webperf101_negative", "WEBPERF101", False),
    ("webperf102_positive", "WEBPERF102", True),
    ("webperf102_negative", "WEBPERF102", False),
    ("webperf103_positive", "WEBPERF103", True),
    ("webperf103_negative", "WEBPERF103", False),
    ("webperf104_positive", "WEBPERF104", True),
    ("webperf104_negative", "WEBPERF104", False),
    ("webperf105_positive", "WEBPERF105", True),
    ("webperf105_negative", "WEBPERF105", False),
    ("webperf106_positive", "WEBPERF106", True),
    ("webperf106_negative", "WEBPERF106", False),
    ("webperf108_positive", "WEBPERF108", True),
    ("webperf108_negative", "WEBPERF108", False),
]


# frob:tests \
# tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf101_positive-WEBPERF101-True] kind="unit"  # noqa: E501
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_webperf_markup.py::webperf_markup_findings kind="unit"
def test_webperf_markup_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule id's positive fixture plants exactly that rule
    id; the matching negative fixture (dimensions/lazy/srcset/font-display/
    defer/budget/viewport present) fires nothing for that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = webperf_markup_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_webperf_markup.py::webperf_markup_findings kind="unit"
def test_webperf107_never_emitted() -> None:
    """WEBPERF107 (source-maps-in-prod) is deliberately owned by T-5143-3
    -- no fixture directory here should ever produce it, across the whole
    positive-fixture corpus, proving the module truly never emits it."""
    for fixture_dir, _rule, expect_finding in _CASES:
        if not expect_finding:
            continue
        findings = webperf_markup_findings(_FIXTURE_ROOT / fixture_dir)
        assert not any(f.rule == "WEBPERF107" for f in findings), findings


# frob:tests src/frob/webapp/_webperf_markup.py::webperf_markup_findings kind="unit"
def test_webperf_markup_findings_no_framework_short_circuits_via_hook(
    tmp_path: Path,
) -> None:
    """`websec_findings` (the discovery-hook wrapper) skips the scan
    entirely on an empty `frameworks` set, even over a directory that
    would otherwise plant a WEBPERF101 finding -- T-5302's convention."""
    (tmp_path / "index.html").write_text(
        '<html><head><title>t</title></head><body><img src="/a.png"></body></html>\n',
        encoding="utf-8",
    )
    assert websec_findings(tmp_path, frozenset()) == ()


# frob:tests src/frob/webapp/_webperf_markup.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5311's discovery-hook
    convention) turns a WEBPERF101 finding into a `Violation` when handed
    a non-empty `frameworks` set -- same shape every WEBSEC-family sibling
    hook already proves."""
    root = _FIXTURE_ROOT / "webperf101_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.NEXTJS}))
    assert any(v.rule == "WEBPERF101" for v in violations), violations


# frob:tests src/frob/webapp/_webperf_markup.py::websec_findings kind="unit"
@pytest.mark.xfail(
    reason="T-draft-553232aa has not landed yet: _taint_gate's discovery hook "
    "only scans frob.webapp._websec_* modules, so this module's "
    "websec_findings is not yet reachable through the live gate scan -- "
    "see docs/modules/webapp-webperf-markup.md#gate-discovery",
    strict=True,
)
def test_webperf_markup_reachable_via_gate_discovery_end_to_end() -> None:
    """End-to-end control (brief 2026-09-24): once T-draft-553232aa widens
    `_taint_gate._WEBSEC_MODULE_PREFIX`-style discovery to also match
    `_webperf_`, `taint_gate`'s own scan should fold in a WEBPERF101
    finding from this fixture without this module being named anywhere in
    `frob.gates._taint_gate`. Marked xfail(strict=True) so the moment
    discovery is widened, this test starts PASSING and the strict xfail
    itself fails loudly, forcing the marker's removal instead of the gap
    going unnoticed."""
    from frob.gates._taint_gate import taint_gate

    root = _FIXTURE_ROOT / "webperf101_positive"
    violations = taint_gate(root)
    assert any(v.rule == "WEBPERF101" for v in violations), violations
