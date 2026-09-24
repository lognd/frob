"""frob.webapp._seo_crawl coverage (T-5362): SEO121-126 crawl/discovery
config findings, one positive + one negative fixture per rule id under
tests/fixtures/webapp/seo1xx/crawl/.

frob:ticket T-5362
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.webapp._detect import FrameworkKind
from frob.webapp._seo_crawl import seo_crawl_findings, websec_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "seo1xx" / "crawl"
)

_CASES = [
    ("seo121_positive", "SEO121", True),
    ("seo121_negative", "SEO121", False),
    ("seo122_positive", "SEO122", True),
    ("seo122_negative", "SEO122", False),
    ("seo123_positive", "SEO123", True),
    ("seo123_negative", "SEO123", False),
    ("seo124_positive", "SEO124", True),
    ("seo124_negative", "SEO124", False),
    ("seo125_positive", "SEO125", True),
    ("seo125_negative", "SEO125", False),
    ("seo126_positive", "SEO126", True),
    ("seo126_negative", "SEO126", False),
]


# frob:tests src/frob/webapp/_seo_crawl.py::WebsecSeoCrawlFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_seo_crawl.py::seo_crawl_findings kind="unit"
def test_seo_crawl_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture (the config gap closed) fires
    nothing for that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = seo_crawl_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) >= 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_seo_crawl.py::seo_crawl_findings kind="unit"
def test_seo_crawl_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even with no llms.txt present (which
    would otherwise plant a SEO124 finding)."""
    assert seo_crawl_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_seo_crawl.py::websec_findings kind="unit"
def test_websec_findings_emits_violation_when_called_directly() -> None:
    """`websec_findings(root, frameworks)` turns a SEO121 finding into a
    `Violation` when handed a non-empty `frameworks` set, without
    re-running `detect_frameworks` -- called directly (module
    docstring's DISCOVERY section: no live gate discovers this hook
    yet)."""
    root = _FIXTURE_ROOT / "seo121_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "SEO121"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_seo_crawl.py::websec_findings kind="unit"
def test_websec_findings_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a SEO121 finding."""
    root = _FIXTURE_ROOT / "seo121_positive"
    assert websec_findings(root, frozenset()) == ()
