## Done report

Fixed strata audit G12: load_repo_benign_capabilities let a consuming
repo excuse ANY capability kind string via frob.toml with just a
reason/caught_by, no allowlist, no load-time verification of whether the
excuse is genuinely a gap. Added a mandatory `family: str | None` field
to BenignCapability (None for the hardcoded DEFAULT_BENIGN_CAPABILITIES
tuple, whose per-entry comments already document by hand which family
each is a no-op for; MANDATORY "security"|"quality" for every
repo-declared [[strata.benign_capabilities]] entry). load_repo_benign_
capabilities now resolves the named family to its catalog
(_family_catalog_for: security -> CWE_CATALOG + CWE_TOP_25_CATALOG,
quality -> QUALITY_CATALOG) and REJECTS (Err(MalformedBenignConfig)) any
entry whose kind is ALREADY classified in the family it names -- that is
not a genuine gap, either a no-op or a mask over an already-known sink.

Counterexample-first, per the ticket's own T-0497-reverted-attempt
warning: the naive fix ("reject any kind cataloged in EITHER family's
union") was NOT reimplemented -- it would have broken the legitimate
T-0017 client_storage case (catalogued security-side, unmapped in
QUALITY_CATALOG). Instead:
- Regression guard: test_client_storage_excused_for_quality_only_stays_
  accepted proves client_storage/family="quality" is still accepted
  (test_repo_declared_excuse_resolves_threat002, the pre-existing
  end-to-end THREAT002 test, updated with the new mandatory family key
  and still green).
- Counterexample: test_client_storage_excused_for_security_family_is_
  rejected proves the SAME kind, claimed for family="security" (where it
  IS classified, CWE-922/312), is now rejected.
- Two more counterexamples with "sql" (classified in BOTH CWE_CATALOG
  AND QUALITY_CATALOG): rejected under family="security" AND under
  family="quality" -- proving illegitimate same-family excuses are
  caught regardless of which family is named.
- test_missing_family_is_malformed / test_unrecognized_family_value_is_
  malformed cover the new mandatory-field and closed-enum validation.

Updated the two frob:doc-anchored docs describing the frob.toml shape
(docs/guides/extending/benign-capabilities.md, docs/strata/threat.md) to
document the mandatory family field, its load-time verification, and the
T-0497-reverted-attempt/T-0511-fix narrative, and expanded the worked
TOML examples to include family/caught_by. No other construction site of
BenignCapability(...) exists outside _threat.py/test_threat.py (grepped).

REL001 did not fire (an optional model field with a default is not
flagged as a public-API break by this repo's release gate) -- no version
bump made.

Filed: none (no out-of-scope work discovered; the docs updates were
in-scope drift from this exact change, added via `frob ticket scope
--add` with a reason each time).

Gates: `uv run frob check --ticket T-0511` clean (0 errors, 98 waived
pre-existing, none new). `frob ticket sweep T-0511` refreshed (PRE001
clean). `pytest tests/unit/strata/test_threat.py -q` and
`tests/unit/strata` full suite both green.

### Changed
```
 .frob-release.json                        |   6 +-
 CHANGELOG.md                              |  16 ++++
 docs/design/registry/weaknesses.yaml      |  25 +++---
 docs/design/security-corpus.md            |  45 +++++-----
 pyproject.toml                            |   2 +-
 src/frob/strata/_cve_fingerprint.py       | 107 +++++++++++++++++++----
 src/frob/strata/_threat.py                |  71 +++++++++++++++
 tests/unit/strata/test_cve_fingerprint.py |  77 ++++++++++++++++
 tests/unit/strata/test_threat.py          |  22 +++++
 tickets.md                                | 140 +++++++++++++++++++++++++++++-
 uv.lock                                   |   2 +-
 11 files changed, 458 insertions(+), 55 deletions(-)
```

### Evidence
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_missing_family_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_unrecognized_family_value_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_excuse_already_classified_in_named_security_family_is_rejected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_excuse_already_classified_in_named_quality_family_is_rejected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_client_storage_excused_for_quality_only_stays_accepted` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_client_storage_excused_for_security_family_is_rejected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_repo_declared_excuse_resolves_threat002` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_declared_entry_is_loaded` (pytest node id, verified passing when recorded)
