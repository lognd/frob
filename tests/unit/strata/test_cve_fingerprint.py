"""T-0153: `std.cve` fingerprint catalog -- `CveFingerprint`,
`CVE_FINGERPRINTS`, `CVE_FINGERPRINT_VIEWS`, and the CVEFP001 drift-lock
(`check_fingerprint_catalog_drift`), docs/strata/threat.md#cve-
fingerprints-code-level-pattern-catalog-t-0153."""

from __future__ import annotations

import pytest

from frob.strata._cve_fingerprint import (
    CVE_FINGERPRINT_VIEWS,
    CVE_FINGERPRINTS,
    CveFingerprint,
    check_fingerprint_catalog_drift,
    scan_text_for_fingerprints,
)
from frob.strata._threat import (
    CWE_CATALOG,
    CWE_TOP_25_CATALOG,
    QUALITY_CATALOG,
    WeaknessEntry,
)


class TestCatalogShape:
    """Every shipped fingerprint has a non-empty cve/needles tuple and a
    language in the four `frob.vet._capability` scans."""

    # frob:tests src/frob/strata/_cve_fingerprint.py::CVE_FINGERPRINTS kind="unit"
    def test_every_fingerprint_has_at_least_one_cve_citation(self):
        for entry in CVE_FINGERPRINTS:
            assert len(entry.cve) >= 1
            for cve_id in entry.cve:
                assert cve_id.startswith("CVE-")

    # frob:tests src/frob/strata/_cve_fingerprint.py::CVE_FINGERPRINTS kind="unit"
    def test_every_fingerprint_has_at_least_one_needle(self):
        for entry in CVE_FINGERPRINTS:
            assert len(entry.needles) >= 1

    # frob:tests src/frob/strata/_cve_fingerprint.py::CVE_FINGERPRINTS kind="unit"
    def test_every_fingerprint_language_is_a_scanned_bucket(self):
        scanned = {"python", "typescript", "rust", "c-cpp"}
        for entry in CVE_FINGERPRINTS:
            assert entry.language in scanned

    # frob:tests src/frob/strata/_cve_fingerprint.py::CVE_FINGERPRINTS kind="unit"
    def test_fingerprint_ids_are_unique(self):
        ids = [entry.id for entry in CVE_FINGERPRINTS]
        assert len(ids) == len(set(ids))

    # frob:tests src/frob/strata/_cve_fingerprint.py::CVE_FINGERPRINT_VIEWS kind="unit"
    def test_view_membership_matches_the_catalog_exactly(self):
        view = CVE_FINGERPRINT_VIEWS["cve-fingerprint-catalog"]
        assert view == frozenset(entry.id for entry in CVE_FINGERPRINTS)


class TestCatalogDrift:
    """CVEFP001: every fingerprint's `cwe_id` must join a real `WeaknessEntry`
    in the joined std.cwe catalog."""

    # frob:tests src/frob/strata/_cve_fingerprint.py::check_fingerprint_catalog_drift kind="unit"
    def test_default_catalog_is_drift_clean(self):
        result = check_fingerprint_catalog_drift()
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_cve_fingerprint.py::check_fingerprint_catalog_drift kind="unit"
    def test_every_fingerprint_cwe_id_resolves_against_the_joined_catalog(self):
        joined_ids = {
            e.id for e in (*CWE_CATALOG, *CWE_TOP_25_CATALOG, *QUALITY_CATALOG)
        }
        for entry in CVE_FINGERPRINTS:
            assert entry.cwe_id in joined_ids

    # frob:tests src/frob/strata/_cve_fingerprint.py::check_fingerprint_catalog_drift kind="unit"
    def test_unknown_cwe_id_fails_loudly(self):
        bogus = CveFingerprint(
            id="FP-BOGUS-001",
            title="a fingerprint citing a cwe id no catalog carries",
            cve=("CVE-2000-0001",),
            cwe_id="CWE-99999",
            language="python",
            needles=("bogus_needle(",),
            remediation="n/a -- test fixture",
        )
        result = check_fingerprint_catalog_drift(fingerprints=(bogus,))
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "CVEFP001"
        assert violations[0].fingerprint_id == "FP-BOGUS-001"
        assert violations[0].cwe_id == "CWE-99999"

    # frob:tests src/frob/strata/_cve_fingerprint.py::check_fingerprint_catalog_drift kind="unit"
    def test_a_removed_cwe_entry_is_detected_against_a_narrowed_catalog(self):
        # simulate a catalog that no longer carries CWE-78 (the id
        # FP-EXEC-SHELL-001 joins) -- the drift-lock must catch it even
        # though the DEFAULT catalog is clean.
        narrowed: tuple[WeaknessEntry, ...] = tuple(
            e for e in CWE_CATALOG if e.id != "CWE-78"
        )
        result = check_fingerprint_catalog_drift(cwe_catalog=narrowed)
        assert result.is_ok
        flagged = {v.fingerprint_id for v in result.danger_ok}
        assert "FP-EXEC-SHELL-001" in flagged


class TestXxeFingerprint:
    """T-0189 (T-0153 review follow-up): `FP-XXE-PARSE-001` joins the new
    CWE-611 `WeaknessEntry` (`_threat.py`) -- previously refused by
    CVEFP001 since no CWE-611 catalog entry existed
    (docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-
    t-0153)."""

    # frob:tests src/frob/strata/_cve_fingerprint.py::CVE_FINGERPRINTS kind="unit"
    def test_fp_xxe_parse_001_exists_and_joins_cwe_611(self):
        entry = next((e for e in CVE_FINGERPRINTS if e.id == "FP-XXE-PARSE-001"), None)
        assert entry is not None
        assert entry.cwe_id == "CWE-611"
        assert entry.language == "python"
        assert entry.cve == ("CVE-2013-1665",)

    # frob:tests src/frob/strata/_cve_fingerprint.py::check_fingerprint_catalog_drift kind="unit"
    def test_fp_xxe_parse_001_resolves_against_the_default_joined_catalog(self):
        result = check_fingerprint_catalog_drift()
        assert result.is_ok
        flagged = {v.fingerprint_id for v in result.danger_ok}
        assert "FP-XXE-PARSE-001" not in flagged


# frob:ticket T-0510
class TestT0510Fingerprints:
    """T-0510: the five previously disclosed-gap fingerprints (weak-hash,
    prototype pollution, ReDoS, open redirect, SSTI) each join a NEW
    `WeaknessEntry` this ticket also added to `QUALITY_CATALOG` --
    counterexample-first: prove each joins its cwe_id AND actually fires
    on its own needle (not just data-shape correct)."""

    _EXPECTED = {
        "FP-WEAKHASH-PASSWORD-001": ("CWE-916", "python", "CVE-2012-3287"),
        "FP-PROTO-POLLUTION-001": ("CWE-1321", "typescript", "CVE-2019-10744"),
        "FP-REDOS-REGEX-001": ("CWE-1333", "typescript", "CVE-2018-11698"),
        "FP-OPEN-REDIRECT-001": ("CWE-601", "python", "CVE-2014-4021"),
        "FP-SSTI-TEMPLATE-001": ("CWE-1336", "python", "CVE-2016-4977"),
    }

    # frob:tests src/frob/strata/_cve_fingerprint.py::CVE_FINGERPRINTS kind="unit"
    @pytest.mark.parametrize("fingerprint_id", list(_EXPECTED))
    def test_entry_exists_and_joins_expected_cwe(self, fingerprint_id: str):
        expected_cwe, expected_language, expected_cve = self._EXPECTED[fingerprint_id]
        entry = next((e for e in CVE_FINGERPRINTS if e.id == fingerprint_id), None)
        assert entry is not None
        assert entry.cwe_id == expected_cwe
        assert entry.language == expected_language
        assert entry.cve == (expected_cve,)

    # frob:tests src/frob/strata/_cve_fingerprint.py::check_fingerprint_catalog_drift kind="unit"
    def test_all_five_resolve_against_the_default_joined_catalog(self):
        result = check_fingerprint_catalog_drift()
        assert result.is_ok
        flagged = {v.fingerprint_id for v in result.danger_ok}
        assert flagged.isdisjoint(self._EXPECTED)

    # frob:tests src/frob/strata/_cve_fingerprint.py::scan_text_for_fingerprints kind="unit"
    def test_weakhash_needle_fires_on_smelly_python(self):
        hits = scan_text_for_fingerprints(
            "digest = hashlib.md5(password.encode()).hexdigest()", "python"
        )
        assert any(h.fingerprint_id == "FP-WEAKHASH-PASSWORD-001" for h in hits)

    # frob:tests src/frob/strata/_cve_fingerprint.py::scan_text_for_fingerprints kind="unit"
    def test_weakhash_needle_does_not_fire_on_clean_python(self):
        hits = scan_text_for_fingerprints("digest = argon2.hash(password)", "python")
        assert not any(h.fingerprint_id == "FP-WEAKHASH-PASSWORD-001" for h in hits)

    # frob:tests src/frob/strata/_cve_fingerprint.py::scan_text_for_fingerprints kind="unit"
    def test_proto_pollution_needle_fires_on_smelly_typescript(self):
        hits = scan_text_for_fingerprints(
            'merged[key] = obj["__proto__"];', "typescript"
        )
        assert any(h.fingerprint_id == "FP-PROTO-POLLUTION-001" for h in hits)

    # frob:tests src/frob/strata/_cve_fingerprint.py::scan_text_for_fingerprints kind="unit"
    def test_redos_needle_fires_on_smelly_typescript(self):
        hits = scan_text_for_fingerprints(
            "const re = new RegExp(userInput);", "typescript"
        )
        assert any(h.fingerprint_id == "FP-REDOS-REGEX-001" for h in hits)

    # frob:tests src/frob/strata/_cve_fingerprint.py::scan_text_for_fingerprints kind="unit"
    def test_open_redirect_needle_fires_on_smelly_python(self):
        hits = scan_text_for_fingerprints(
            "return redirect(request.GET.get('next'))", "python"
        )
        assert any(h.fingerprint_id == "FP-OPEN-REDIRECT-001" for h in hits)

    # frob:tests src/frob/strata/_cve_fingerprint.py::scan_text_for_fingerprints kind="unit"
    def test_ssti_needle_fires_on_smelly_python(self):
        hits = scan_text_for_fingerprints(
            "return render_template_string(user_supplied)", "python"
        )
        assert any(h.fingerprint_id == "FP-SSTI-TEMPLATE-001" for h in hits)
