## Done report

Changed:
- `src/frob/strata/_threat.py`: `CWE_CATALOG` gains a `CWE-611` (Improper
  Restriction of XML External Entity Reference) `WeaknessEntry`
  (`capability_kind=None`, a parser-configuration precondition -- the
  same citation-only shape CWE-22/CWE-352/CWE-798 already use;
  `mitigation="external_entity_disabled"`, `rung=Rung.L4`).
- `src/frob/strata/_cve_fingerprint.py`: `CVE_FINGERPRINTS` gains
  `FP-XXE-PARSE-001` (python, `cwe_id="CWE-611"`, needles
  `"resolve_entities=True"` / `"xml.sax.make_parser("`, citing
  CVE-2013-1665 -- Python's stdlib XML libraries, as used by Django's
  `xml.dom.pulldom`-based deserializer, allowed a remote attacker to read
  arbitrary files via a DOCTYPE-declared external entity, the canonical
  Python XXE exemplar). Module docstring updated: nine -> ten shipped
  fingerprints, XXE moved out of the "deliberately not shipped" list.
- `tests/unit/strata/test_threat.py`: new `TestCwe611Xxe` class (catalog
  entry shape, `owasp-top-10` view membership, never-fires assertion).
- `tests/unit/strata/test_cve_fingerprint.py`: new `TestXxeFingerprint`
  class (fingerprint shape/CWE join, drift-clean against the default
  catalog).
- `tests/test_vet.py`: two litmus positive/negative tests on
  `TestFingerprintScan` (`test_matches_the_xxe_fingerprint_positive` /
  `test_does_not_match_the_xxe_fingerprint_negative`) proving
  `scan_file_fingerprints` fires on an unhardened `etree.XMLParser`
  config and not on the hardened one (T-0153's fingerprint-scan pattern).
- `tests/unit/strata/test_litmus_cwe.py` + new
  `tests/unit/strata/litmus/cwe_611_unfired.strata`: CWE-611 added to
  `_FIRING_FIXTURES`/`_UNFIRED_FIXTURES` (T-0145's exhaustive per-CWE
  litmus fixture pattern, discovered as a hard requirement mid-task --
  `test_every_catalog_entry_has_a_fixture_mapping` fails loudly for any
  catalog id with no fixture mapping, by design). The new fixture mirrors
  `cwe_798_unfired.strata`'s shape and proves THREAT003 reports zero
  CWE-611 obligations for a foreign-caller-reaches-parser scenario.
- `docs/strata/threat.md`: CVE-fingerprints section updated (ten
  fingerprints, XXE no longer in the "not shipped" list); "three catalog
  ids can never fire" design-finding paragraph extended to name CWE-611
  as a fourth, with its `cwe_611_unfired.strata` fixture named directly
  (no longer "not added here" -- it exists).

Evidence (10 ids, all pytest, collected against a fresh
`pytest --collect-only` pass, 2905 node ids):
```
tests/unit/strata/test_threat.py::TestCwe611Xxe::test_cwe_611_entry_exists_in_the_catalog
tests/unit/strata/test_threat.py::TestCwe611Xxe::test_cwe_611_is_reachable_via_the_owasp_top_10_view
tests/unit/strata/test_threat.py::TestCwe611Xxe::test_cwe_611_never_fires_capability_kind_is_none
tests/unit/strata/test_cve_fingerprint.py::TestXxeFingerprint::test_fp_xxe_parse_001_exists_and_joins_cwe_611
tests/unit/strata/test_cve_fingerprint.py::TestXxeFingerprint::test_fp_xxe_parse_001_resolves_against_the_default_joined_catalog
tests/test_vet.py::TestFingerprintScan::test_matches_the_xxe_fingerprint_positive
tests/test_vet.py::TestFingerprintScan::test_does_not_match_the_xxe_fingerprint_negative
tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_catalog_entry_has_a_fixture_mapping
tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_unfired_ids_are_exactly_the_capability_kind_none_entries
tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-611]
```
All recorded via `frob ticket evidence T-0189 ...` (two batches, 7 then 3
ids; final count 10, confirmed by the CLI's own echo).

Not Filed: T-draft-46c43552 (never refiled) ("release: bump version to 0.14.0 + stamp for
T-0189 CWE-611/XXE catalog addition (REL001)", kind=docs, scope
pyproject.toml/CHANGELOG.md/.frob-release.json) -- `frob release check`
classifies this ticket's catalog additions as a MAJOR public-API change
(module-level tuple constant content is part of the tracked signature
digest in this repo's release gate), and REL001 fails until the version
is bumped to >= 0.14.0 and `frob release stamp` is re-run. None of
pyproject.toml/CHANGELOG.md/.frob-release.json are in T-0189's declared
scope, so the bump is a separate scoped unit of work rather than a
silent scope expansion here (T-0333's Done report in this same ledger is
the precedent for doing the version bump as its own ticket-scoped
change alongside a REL001-triggering additive change).

Gates:
- `make core` run first (fresh worktree, natives were unbuilt) --
  `frob_core`/`strata_core` built clean.
- `uv run pytest tests/unit/strata/test_threat.py
  tests/unit/strata/test_cve_fingerprint.py tests/test_vet.py
  tests/unit/strata/test_litmus_cwe.py -q`: all green, no failures.
- `make coverage` (foreground, full suite): green, exit 0 --
  "Coverage XML written to file coverage.xml", `frob check
  --stamp-coverage` stamped 404 files. (First run caught two real
  failures in `test_litmus_cwe.py`'s exhaustiveness drift-lock before
  the fixture was added; fixed, then this final green run.)
- `frob test --collect`: 2905 node ids collected, 0 declared natives
  missing.
- `frob check --ticket T-0189`: 1 error remains --
  `REL001: public API changed (major) since 0.13.0; bump the version to
  >= 0.14.0 (currently 0.13.0), then run: frob release stamp`
  (`pyproject.toml:0`) -- out of this ticket's declared scope, not filed as
  T-draft-46c43552 (never refiled) above rather than fixed silently here or waived
  without a real fix. All other gates pass (139 warnings, all
  pre-existing per `frob-arch`/`frob-dup`/`frob-exports` categories
  unrelated to this change; PRE001 cleared via `frob ticket sweep
  T-0189` after edits).

Not closing this ticket -- reviewer sign-off per the review-gated flow.
