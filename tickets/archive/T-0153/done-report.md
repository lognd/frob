## Done report

Changed:
- src/frob/strata/_cve_fingerprint.py (new) -- `CveFingerprint` model,
  `CVE_FINGERPRINTS` (9 entries), `CVE_FINGERPRINT_VIEWS`,
  `FingerprintViolation`, `check_fingerprint_catalog_drift` (CVEFP001)
- src/frob/strata/__init__.py -- exports the five new public symbols above
- src/frob/vet/_capability.py -- `scan_file_fingerprints` (lazy
  `frob.strata` import to break the `_effects.py` <-> `_capability.py`
  import cycle); `_FINGERPRINT_CATALOG_PATH` self-match exclusion added to
  `_is_self_path`
- docs/strata/threat.md -- new "CVE fingerprints: code-level pattern
  catalog (T-0153)" section, `<a id="cve-fingerprints-code-level-pattern-
  catalog-t-0153">` anchor
- docs/modules/vet.md -- `scan_file_fingerprints` added to the Public API
  describes-anchor list and prose list
- tests/unit/strata/test_cve_fingerprint.py (new)
- tests/test_vet.py -- `TestFingerprintScan` class added

Curated set is NINE fingerprints, not the ticket's illustrative "10-15":
every `cve` citation was independently web-searched and verified against a
primary/vendor/NVD source at authoring time (never hand-guessed from
memory) -- CVE-2014-6271 (Shellshock, CWE-78), CVE-2015-9251 (jQuery
cross-domain XSS, CWE-79), CVE-2007-4559 (Python tarfile traversal,
CWE-22), CVE-2017-18342 (PyYAML unsafe load, CWE-502), CVE-2025-32444
(vLLM pickle.loads RCE, CWE-502), CVE-2012-2661 (Rails SQLi, CWE-89,
disclosed cross-ecosystem exemplar), CVE-2021-21973 (VMware vCenter SSRF,
CWE-918, disclosed cross-ecosystem exemplar), CVE-2021-23358
(underscore.js template code injection, CWE-94), CVE-2015-7755 (Juniper
ScreenOS hardcoded backdoor password, CWE-798, disclosed cross-ecosystem
exemplar). Three ticket-suggested classes (TLS verify=False/CWE-295,
weak-hash password storage/CWE-916, XXE/CWE-611) are deliberately NOT
shipped: no `WeaknessEntry` for any of the three CWE ids exists in ANY
catalog tuple, so a fingerprint citing any of them would fail this
ticket's OWN CVEFP001 drift-lock -- disclosed consistently in both the
module docstring and docs/strata/threat.md as a gap needing a
catalog-scoped follow-up ticket, not forced around the drift-lock.
JNDI/Log4Shell-class lookup injection is also omitted: it is Java/JNDI-
specific with no equivalent construct in any of the four languages
`frob.vet._capability` scans (python/typescript/rust/c-cpp), so a
fingerprint for it would be undetectable data, not a real pattern-match
capability.

"Litmus-style fire/discharge fixtures" (ticket text) are NOT `.strata`
kernel-model fixtures: `CveFingerprint` is a source-code substring scan
over real files (`scan_file_fingerprints`), not a `WeaknessEntry`-shaped
kernel precondition with a `may` capability join -- there is no
`_fired_obligations`/THREAT003 discharge concept for a fingerprint to
fire/discharge against. The litmus-equivalent proof implemented instead:
`TestFingerprintScan` in tests/test_vet.py exercises each fingerprint's
needle against a real source snippet (positive: `FP-DESERIALIZE-YAML-001`
matches `yaml.load(...)`; negative: clean source and cross-language
needle-text produce zero matches), and `TestCatalogDrift` in
tests/unit/strata/test_cve_fingerprint.py proves the CVEFP001 drift-lock
fires on an unjoined/removed cwe_id and stays clean against the shipped
catalog. Filed a design finding in docs/strata/threat.md rather than
silently reinterpreting the ticket's fixture-format request.

Evidence: 19 test node ids recorded via `frob ticket evidence T-0153`
(tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape/
TestCatalogDrift, tests/test_vet.py::TestFingerprintScan/
TestScanTreeWithLocalSource, tests/unit/strata/test_audit.py::
TestExhaustiveness -- full list in this ticket's `evidence:` yaml block
above).

Filed: none -- the disclosed gaps above (CWE-295/CWE-916/CWE-611 catalog
entries; Log4Shell-class fingerprint) are documented in-repo rather than
filed as new tickets, since closing them requires a catalog-scoped
decision (adding `WeaknessEntry` rows) out of this ticket's own scope
(`src/frob/strata/**` includes `_threat.py`, but widening `CWE_CATALOG`/
`QUALITY_CATALOG` itself is a separate, catalog-owning decision this
ticket's scope note did not request); coordinator files these serially,
not this ticket.

### Fix round (reviewer REJECT -> addressed)

Round 1 reviewer verdict: catalog/model/drift-lock logic, docs, self-match
exclusion, import-cycle handling, and all 9 CVE citations verified solid,
but REJECTED on one real gap -- `scan_file_fingerprints` was wired as a
detector but never CALLED by the real `frob vet` pipeline
(`_scan_source` only aggregated `scan_directory_capabilities`/
`decode_to_exec_signal`), so a dependency containing e.g.
`yaml.load(data)` produced zero fingerprint signal in
`PackageVerdict`/`Violation` output; `check_fingerprint_catalog_drift`
also ran test-only, with no operational path mirroring THREAT002/003's
`evaluate_exhaustiveness` wiring; and the module docstring named CWE-916
in a sentence without it appearing in the cut-class list above it.

Addressed:
1. `frob.vet._capability.scan_directory_fingerprints` (new) -- the
   aggregation sibling of `scan_directory_capabilities`, same walk/
   test-path/self-path exclusion shape. Called from `_scan.py::
   _scan_source` (extending T-0153's scope to include
   `src/frob/vet/_scan.py`, recorded in `scope:` above -- required to
   wire the call site the ticket's own text asked for, a cascading
   scope-by-necessity consequence, not silently absorbed). A match now
   surfaces a `VET006` `Violation` and a `"cve-fingerprint"` signal
   persisted onto the stored `PackageVerdict`. Proven end to end via
   `tests/test_vet.py::TestScanTreeWithLocalSource::
   test_scan_tree_surfaces_a_cve_fingerprint_finding` -- a real `uv.lock`
   + on-disk `.venv/lib/*/site-packages/` dependency source through the
   REAL `scan_tree` pipeline, not a direct `scan_file_fingerprints`
   import -- asserting a `VET006` violation citing the matched
   fingerprint id AND the `"cve-fingerprint"` signal on the returned
   `PackageVerdict`.
2. `frob.strata._audit.evaluate_exhaustiveness` now runs
   `check_fingerprint_catalog_drift` every call under a fixed
   `"cve-fingerprint:catalog"` pseudo-view (model-independent -- mirrors
   `_pii_gaps`'s fixed `"pii:model"` view precedent exactly, since a
   catalog-join property has no per-model baseline-view concept), so
   `frob sys audit` fails closed on a drifted `cwe_id` the same way
   THREAT001-003 already do. Proven by
   `tests/unit/strata/test_audit.py::TestExhaustiveness::
   test_cve_fingerprint_catalog_checked_every_call` (asserts
   `"cve-fingerprint:catalog"` in `views_checked` and zero
   `family="cve-fingerprint"` gaps against the shipped, drift-clean
   catalog -- the drift-DETECTION logic itself stays covered by
   `test_cve_fingerprint.py::TestCatalogDrift`, this test proves only
   that the operational path calls it).
3. Reconciled the CWE-916 docstring/list mismatch: both the module
   docstring and docs/strata/threat.md now list all THREE deliberately
   cut classes together (CWE-295, CWE-916, CWE-611) consistently, instead
   of naming CWE-916 in one sentence without it appearing in the cut list
   above.

Gates: `uv run frob check --ticket T-0153` clean of ticket-attributable
findings after both fix rounds (COV001 doc edge on
`CVE_FINGERPRINT_VIEWS`; PERF004 sort-in-loop waived in
`scan_file_fingerprints`; PERF001 waived in the new `scan_tree`-level
test; SCOPE001 resolved by extending `scope:` to include
`src/frob/vet/_scan.py`; TEST001 resolved by adding
`scan_directory_fingerprints` unit tests; ruff-check/ruff-format/ty all
clean). Remaining `frob check` output after the round-2 fix (TEST006 no
coverage stamp; COV003 on unrelated ticket T-0168's evidence, picked up
by the main merge) is campaign-wide/pre-existing, not attributable to
this ticket's diff. `uv run frob test --base main`: touched=49, selected
python suite exit=0 (4.84s), including the full `tests/test_vet.py`,
`tests/unit/strata/test_cve_fingerprint.py`, and
`tests/unit/strata/test_audit.py`.
