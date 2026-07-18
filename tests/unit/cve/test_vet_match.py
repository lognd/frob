"""Tests for `frob.vet._cve`: matching dependencies against a local
cvelistV5 mirror and linking CWE ids into the strata threat catalog
(T-0147, docs/modules/vet.md "CVE mirror matching"). Reuses the T-0146
mirror fixtures (`tests/unit/cve/fixtures/mirror`) for the CWE-linkage and
REJECTED-skip cases against a REAL record (Log4Shell); a small synthetic
mirror (`tests/unit/cve/fixtures/vet_mirror`) supplies clean semver ranges
none of the committed real records happen to have, plus its own REJECTED
record, since Log4Shell's own affected[] range is deliberately
`versionType=custom` (uncomparable) end to end.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata._threat import CWE_CATALOG
from frob.vet._cve import (
    CweDisposition,
    MatchStatus,
    link_cwe_ids,
    match_dependencies_against_mirror,
)
from frob.vet._models import Dependency, VetError

_FIXTURES = Path(__file__).parent / "fixtures"
_REAL_MIRROR = _FIXTURES / "mirror"
_SYNTHETIC_MIRROR = _FIXTURES / "vet_mirror"


def test_affected_within_clean_semver_range() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """A dependency version inside `[1.0.0, 2.0.0)` (CVE-2024-1000, the
    synthetic libfoo fixture) is reported AFFECTED with CVSS v4.0
    preferred over the v3.1 metric also present on the same record."""
    deps = (Dependency(ecosystem="pypi", name="libfoo", version="1.5.0"),)
    result = match_dependencies_against_mirror(deps, _SYNTHETIC_MIRROR)
    assert result.is_ok
    matches = [m for m in result.danger_ok if m.cve_id == "CVE-2024-1000"]
    assert len(matches) == 1
    match = matches[0]
    assert match.status is MatchStatus.AFFECTED
    # v4.0 (9.3) preferred over the v3.1 (9.8) metric on the same record
    assert match.cvss_score == 9.3
    assert match.cvss_severity == "CRITICAL"
    assert "libfoo" in match.summary


def test_unaffected_via_less_than_boundary() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """A dependency version exactly at the `lessThan` upper bound is
    excluded from the affected range and matches the explicit unaffected
    point entry instead -- the boundary is exclusive."""
    deps = (Dependency(ecosystem="pypi", name="libfoo", version="2.0.0"),)
    result = match_dependencies_against_mirror(deps, _SYNTHETIC_MIRROR)
    assert result.is_ok
    matches = [m for m in result.danger_ok if m.cve_id == "CVE-2024-1000"]
    assert len(matches) == 1
    assert matches[0].status is MatchStatus.UNAFFECTED


def test_unaffected_via_default_status() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """A version outside every explicit range falls through to
    `defaultStatus=unaffected` on the synthetic fixture."""
    deps = (Dependency(ecosystem="pypi", name="libfoo", version="3.0.0"),)
    result = match_dependencies_against_mirror(deps, _SYNTHETIC_MIRROR)
    assert result.is_ok
    matches = [m for m in result.danger_ok if m.cve_id == "CVE-2024-1000"]
    assert len(matches) == 1
    assert matches[0].status is MatchStatus.UNAFFECTED
    assert "defaultStatus" in matches[0].reason


def test_indeterminate_versiontype_custom_never_silently_unaffected() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """Log4Shell's real record (CVE-2021-44228) uses `versionType=custom`
    with a non-semver `lessThan` -- vacuous-pass doctrine: this MUST be
    reported INDETERMINATE with the reason, never silently downgraded to
    UNAFFECTED just because the range could not be evaluated."""
    deps = (Dependency(ecosystem="maven", name="Apache Log4j2", version="2.14.1"),)
    result = match_dependencies_against_mirror(deps, _REAL_MIRROR)
    assert result.is_ok
    matches = [m for m in result.danger_ok if m.cve_id == "CVE-2021-44228"]
    assert len(matches) == 1
    match = matches[0]
    assert match.status is MatchStatus.INDETERMINATE
    assert "versionType" in match.reason or "custom" in match.reason


def test_indeterminate_default_status_unknown() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """The real curl record (CVE-2023-38545) has two empty (never-
    satisfiable) ranges and no `defaultStatus` -- a version outside both
    is genuinely indeterminate (unknown default), reported loudly rather
    than assumed clean."""
    deps = (Dependency(ecosystem="pypi", name="curl", version="9.0.0"),)
    result = match_dependencies_against_mirror(deps, _REAL_MIRROR)
    assert result.is_ok
    matches = [m for m in result.danger_ok if m.cve_id == "CVE-2023-38545"]
    assert len(matches) == 1
    assert matches[0].status is MatchStatus.INDETERMINATE


def test_rejected_record_skipped_never_matched() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """CVE-2024-1001 (synthetic, REJECTED) affects the same product/
    version as CVE-2024-1000, but must never appear in the match output --
    REJECTED records are skipped with a log line, not matched."""
    deps = (Dependency(ecosystem="pypi", name="libfoo", version="1.5.0"),)
    result = match_dependencies_against_mirror(deps, _SYNTHETIC_MIRROR)
    assert result.is_ok
    cve_ids = {m.cve_id for m in result.danger_ok}
    assert "CVE-2024-1001" not in cve_ids
    assert "CVE-2024-1000" in cve_ids


def test_cwe_linkage_catalog_out_of_scope_and_unmapped() -> None:
    # frob:tests src/frob/vet/_cve.py::link_cwe_ids kind="unit"
    """Log4Shell's real problemTypes carry three CWE ids that land in all
    three dispositions: CWE-502 (cataloged, deserialize/schema_validation
    -- also the ticket's own worked example), CWE-20 (explicitly out of
    scope in `CWE_TOP_25_OUT_OF_SCOPE`), and CWE-400 (in neither table,
    unmapped)."""
    links = link_cwe_ids(("CWE-502", "CWE-400", "CWE-20"))
    by_id = {link.cwe_id: link for link in links}

    assert by_id["CWE-502"].disposition is CweDisposition.CATALOG
    catalog_entry = next(e for e in CWE_CATALOG if e.id == "CWE-502")
    assert by_id["CWE-502"].title == catalog_entry.title
    assert by_id["CWE-502"].mitigation == catalog_entry.mitigation

    assert by_id["CWE-400"].disposition is CweDisposition.UNMAPPED

    assert by_id["CWE-20"].disposition is CweDisposition.OUT_OF_SCOPE
    assert by_id["CWE-20"].reason


def test_log4shell_end_to_end_cwe_linkage_via_mirror() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="integration"
    """End to end over the real mirror: Log4Shell's match carries all
    three CWE dispositions on the `CveMatch.cwe_links` it produces."""
    deps = (Dependency(ecosystem="maven", name="Apache Log4j2", version="2.14.1"),)
    result = match_dependencies_against_mirror(deps, _REAL_MIRROR)
    assert result.is_ok
    match = next(m for m in result.danger_ok if m.cve_id == "CVE-2021-44228")
    dispositions = {link.cwe_id: link.disposition for link in match.cwe_links}
    assert dispositions["CWE-502"] is CweDisposition.CATALOG
    assert dispositions["CWE-20"] is CweDisposition.OUT_OF_SCOPE
    assert dispositions["CWE-400"] is CweDisposition.UNMAPPED


def test_missing_mirror_is_loud_typed_failure() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """A configured mirror path that does not exist is `Err
    (VetError.CveMirrorInvalid)`, never an empty (silently-passing) result
    (vacuous-pass doctrine)."""
    deps = (Dependency(ecosystem="pypi", name="libfoo", version="1.5.0"),)
    result = match_dependencies_against_mirror(
        deps, _FIXTURES / "not-a-real-mirror-dir"
    )
    assert result.is_err
    assert result.danger_err == VetError.CveMirrorInvalid


def test_no_dependencies_still_walks_mirror_cleanly() -> None:
    # frob:tests src/frob/vet/_cve.py::match_dependencies_against_mirror kind="unit"
    """An empty dependency list against a valid mirror is a clean `Ok(())`
    -- distinguishing "nothing to match" from a mirror failure."""
    result = match_dependencies_against_mirror((), _SYNTHETIC_MIRROR)
    assert result.is_ok
    assert result.danger_ok == ()


def test_unconfigured_mirror_is_a_silent_no_op() -> None:
    # frob:tests src/frob/app/vet_runner.py::_cve_matches_for kind="unit"
    """No `[tool.frob].vet_cve_mirror`/`--cve-mirror` at all: `frob vet`
    must not touch `frob.cve` or emit a CVE section -- clean no-op, the
    ONLY case that is silent (a configured-but-bad mirror is loud, see
    `test_missing_mirror_is_loud_typed_failure` above)."""
    from frob.app.config import AppConfig
    from frob.app.vet_runner import _cve_matches_for
    from frob.vet._models import VetReport

    cfg = AppConfig(vet_cve_mirror=None)
    matches = _cve_matches_for(VetReport(), cfg)
    assert matches == ()
