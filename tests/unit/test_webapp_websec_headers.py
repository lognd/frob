"""frob.webapp._websec_headers coverage: positive and negative controls
for nginx, Caddy, Django, and Express+helmet response-header evidence,
plus the no-evidence ADVISORY case.

frob:ticket T-5325
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.webapp._websec_headers import (
    REQUIRED_HEADERS,
    HeaderSourceKind,
    HeaderStatus,
    WebsecHeadersError,
    lint_response_headers,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec3xx"
)


def _statuses(findings) -> dict[str, HeaderStatus]:
    """Reduce a `lint_response_headers` result to {header: status} for
    easy assertion."""
    return {finding.header: finding.status for finding in findings}


# frob:tests src/frob/webapp/_websec_headers.py::lint_response_headers kind="unit"
# frob:tests src/frob/webapp/_websec_headers.py::HeaderFinding frob:tests \
# src/frob/webapp/_websec_headers.py::HeaderStatus frob:tests \
# src/frob/webapp/_websec_headers.py::HeaderSourceKind \
@pytest.mark.parametrize(
    "fixture_dir,source",
    [
        ("nginx_full", HeaderSourceKind.NGINX),
        ("caddy_full", HeaderSourceKind.CADDY),
        ("django_full", HeaderSourceKind.APP_DJANGO),
    ],
)
def test_full_evidence_all_present(fixture_dir: str, source: HeaderSourceKind):
    """MUST-FIRE: a security surface (nginx.conf/Caddyfile/Django
    settings.py) setting every required header reports all PRESENT via
    the matching `HeaderSourceKind`, one positive control per source."""
    result = lint_response_headers(_FIXTURE_ROOT / fixture_dir)
    assert result.is_ok
    findings = result.danger_ok
    assert len(findings) == len(REQUIRED_HEADERS)
    statuses = _statuses(findings)
    assert all(status == HeaderStatus.PRESENT for status in statuses.values())
    assert all(f.source == source for f in findings)


# frob:tests src/frob/webapp/_websec_headers.py::lint_response_headers kind="unit"
@pytest.mark.parametrize(
    "fixture_dir,missing_header,present_header",
    [
        ("nginx_missing_csp", "Content-Security-Policy", "Strict-Transport-Security"),
        ("caddy_missing_hsts", "Strict-Transport-Security", "X-Frame-Options"),
        ("django_missing_xfo", "X-Frame-Options", "Content-Security-Policy"),
    ],
)
def test_one_missing_header_reports_missing(
    fixture_dir: str, missing_header: str, present_header: str
):
    """Negative control: a security surface lacking exactly one required
    header reports that header MISSING (an actionable ERROR) while the
    rest stay PRESENT, one per source."""
    result = lint_response_headers(_FIXTURE_ROOT / fixture_dir)
    assert result.is_ok
    statuses = _statuses(result.danger_ok)
    assert statuses[missing_header] == HeaderStatus.MISSING
    assert statuses[present_header] == HeaderStatus.PRESENT


# frob:tests src/frob/webapp/_websec_headers.py::lint_response_headers kind="unit"
def test_express_helmet_reports_default_headers_present():
    """MUST-FIRE: a bare `helmet()` call reports helmet's default header
    set (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
    PRESENT via HeaderSourceKind.APP_HELMET; CSP (opt-in, not guessed at)
    is not covered by the default set and reports ADVISORY since no other
    security surface exists in this fixture."""
    result = lint_response_headers(_FIXTURE_ROOT / "express_helmet")
    assert result.is_ok
    statuses = _statuses(result.danger_ok)
    assert statuses["Strict-Transport-Security"] == HeaderStatus.PRESENT
    assert statuses["X-Content-Type-Options"] == HeaderStatus.PRESENT
    assert statuses["X-Frame-Options"] == HeaderStatus.PRESENT
    assert statuses["Referrer-Policy"] == HeaderStatus.PRESENT
    assert statuses["Content-Security-Policy"] == HeaderStatus.MISSING


# frob:tests src/frob/webapp/_websec_headers.py::lint_response_headers kind="unit"
def test_no_evidence_is_advisory_not_error():
    """MUST-FIRE: a repo with no recognized security surface reports every
    header ADVISORY (T-5325 documented CDN-layer gap), never MISSING --
    the owner-directive distinction between "no evidence" and "evidence of
    absence"."""
    result = lint_response_headers(_FIXTURE_ROOT / "no_evidence")
    assert result.is_ok
    findings = result.danger_ok
    assert all(f.status == HeaderStatus.ADVISORY for f in findings)
    assert all(f.source is None for f in findings)


# frob:tests src/frob/webapp/_websec_headers.py::lint_response_headers kind="unit"
# frob:tests src/frob/webapp/_websec_headers.py::WebsecHeadersError
def test_root_not_a_directory_is_err(tmp_path: Path):
    """A root that does not resolve to a directory returns
    Err(ROOT_NOT_A_DIRECTORY) rather than raising."""
    missing = tmp_path / "does-not-exist"
    result = lint_response_headers(missing)
    assert result.is_err
    assert result.danger_err == WebsecHeadersError.ROOT_NOT_A_DIRECTORY
