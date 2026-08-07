## Done report

Added the 5 missing WeaknessEntry rows (CWE-916/1321/1333/601/1336) to
QUALITY_CATALOG (_threat.py), following CWE-295's own precedent exactly:
family="security", capability_kind=None, no default-view membership,
discharged only via the std.cve fingerprint layer. Added a matching
CveFingerprint per CWE to CVE_FINGERPRINTS (_cve_fingerprint.py):
FP-WEAKHASH-PASSWORD-001 (CVE-2012-3287), FP-PROTO-POLLUTION-001
(CVE-2019-10744), FP-REDOS-REGEX-001 (CVE-2018-11698),
FP-OPEN-REDIRECT-001 (CVE-2014-4021), FP-SSTI-TEMPLATE-001
(CVE-2016-4977) -- all citations already independently verified in
docs/design/security-corpus.md's table 4b, reused here rather than
re-researched. CVE_FINGERPRINTS grew 13 -> 18 entries, all drift-clean
(CVEFP001). Flipped the matching 5 SEC-CVE-FINGERPRINT-CWE-* rows in
docs/design/registry/weaknesses.yaml from disposition: deferred:T-0510
to handled_by:SEC-CVE-FINGERPRINT-001 with cross_refs to the new
fingerprint ids. Updated docs/design/security-corpus.md's section 4/4b
and coverage-summary table to reflect the shipped status (only the
Log4Shell/JNDI class remains a disclosed non-shipped gap).

Counterexample-first: added TestT0510Fingerprints (12 tests) proving
each fingerprint (a) joins its expected cwe_id/language/cve and (b)
actually FIRES its needle on a smelly fixture (weak-hash md5, __proto__
merge, dynamic RegExp, request-driven redirect, render_template_string)
plus one clean-miss counterexample (argon2 hash does not fire
weak-hash). Added a parametrized test in TestQualityFamilies (5 cases)
proving each new WeaknessEntry is catalog-only with no capability_kind
and no view membership, mirroring test_cwe_295_is_cataloged_with_no_
capability_kind_or_view's existing pattern.

Scope was expanded three times beyond the ticket's original three globs,
each via `frob ticket scope --add` with a reason: (1)
docs/design/registry/weaknesses.yaml, since the ticket body explicitly
requires flipping its 5 dispositions; (2) pyproject.toml/CHANGELOG.md/
uv.lock/.frob-release.json for the REL001 public-API version bump this
change requires; (3) the two test files carrying the new evidence.

REL001: public API changed (new WeaknessEntry/CveFingerprint tuple
entries) -- bumped 0.53.0 -> 0.54.0, added a CHANGELOG.md entry, ran
`uv lock` and `frob release stamp`.

Filed: none (no out-of-scope work discovered).

Gates: `uv run frob check --ticket T-0510` clean (0 errors, 97 waived
pre-existing, none new). `frob ticket sweep T-0510` refreshed
(PRE001 clean).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-WEAKHASH-PASSWORD-001]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-PROTO-POLLUTION-001]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-REDOS-REGEX-001]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-OPEN-REDIRECT-001]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-SSTI-TEMPLATE-001]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_all_five_resolve_against_the_default_joined_catalog` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_weakhash_needle_fires_on_smelly_python` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_weakhash_needle_does_not_fire_on_clean_python` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_proto_pollution_needle_fires_on_smelly_typescript` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_redos_needle_fires_on_smelly_typescript` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_open_redirect_needle_fires_on_smelly_python` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_ssti_needle_fires_on_smelly_python` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-916]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-1321]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-1333]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-601]` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-1336]` (pytest node id, verified passing when recorded)
