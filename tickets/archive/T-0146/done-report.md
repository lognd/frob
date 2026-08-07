## Done report

Changed:
- src/frob/cve/_models.py (new) -- CveState, CveError, CveMetadata, Version, Affected, ProblemTypeDescription, ProblemType, Cvss, Metric, Reference, Description, CnaContainer, AdpContainer, CveContainers, CveRecord
- src/frob/cve/_parser.py (new) -- parse_record, iter_mirror
- src/frob/cve/__init__.py (new) -- public exports
- tests/unit/cve/__init__.py (new)
- tests/unit/cve/test_parser.py (new) -- 11 tests
- tests/unit/cve/fixtures/*.json (new, 5 files) + tests/unit/cve/fixtures/mirror/... (new, 7 files: the same 5 records laid out under cves/YYYY/NNNxxx/, plus a truncated-JSON file and a structurally-invalid record for the error-path tests)
- docs/modules/cve.md (new)
- docs/index.md (linked docs/modules/cve.md)

Fixtures are REAL CVE Record Format v5 JSON, fetched directly from raw.githubusercontent.com/CVEProject/cvelistV5/main (network used only during authoring/fixture-collection, never in the parser or in any test):
- CVE-2021-44228 (Log4Shell): 2 ADP containers, CVSS v3.1 on an ADP container (baseScore=10, CRITICAL), CNA problemTypes with 3 real CWE ids (CWE-502, CWE-400, CWE-20).
- CVE-2023-38545 (curl SOCKS5 heap overflow): affected[].versions[] with lessThan + versionType="semver", both "affected" and "unaffected" statuses in one list.
- CVE-2024-3094 (xz backdoor): multiple affected[] entries across vendors (xz upstream + several Red Hat products), defaultStatus="unaffected" alongside explicit versions.
- CVE-2024-4681: CNA metrics carrying a real cvssV4_0 score (found via `gh api search/code -f q='cvssV4_0 repo:CVEProject/cvelistV5'`).
- CVE-2024-7039: REJECTED-state record (found via `gh api search/code -f q='"state": "REJECTED" repo:CVEProject/cvelistV5'`) -- parses fully into CveState.REJECTED with dateRejected populated; cna container is near-empty (only rejectedReasons, which this module does not model and correctly ignores as an extra field).

Every model uses `model_config = ConfigDict(frozen=True, extra="ignore")` (repo convention per src/frob/vet/_models.py): unknown fields never fail parsing, but a missing required field (cveMetadata.state, containers.cna, affected[].versions[].version/status) raises pydantic ValidationError, caught and turned into `Err(CveError.MalformedRecord)` -- verified directly by test_parse_missing_required_field against a hand-built fixture missing cveMetadata.state.

Evidence: 11 pytest node ids (10 unit + 1 integration satisfying TEST003 on src/frob/cve), bound via `frob ticket evidence T-0146`:
- tests/unit/cve/test_parser.py::test_parse_log4shell_multi_adp_and_cwe
- tests/unit/cve/test_parser.py::test_parse_version_ranges_with_less_than
- tests/unit/cve/test_parser.py::test_parse_multi_vendor_affected
- tests/unit/cve/test_parser.py::test_parse_cvss_v4
- tests/unit/cve/test_parser.py::test_parse_rejected_record
- tests/unit/cve/test_parser.py::test_parse_missing_file
- tests/unit/cve/test_parser.py::test_parse_truncated_json
- tests/unit/cve/test_parser.py::test_parse_missing_required_field
- tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
- tests/unit/cve/test_parser.py::test_iter_mirror_invalid_root
- tests/unit/cve/test_parser.py::test_cve_module_end_to_end_over_mirror (kind="integration", satisfies TEST003 for src/frob/cve)

Full suite: `uv run pytest -q` -- all pass (2 pre-existing skips, unrelated to this change).
Touched-set: `frob test --base main` -- python runner exit=0.

Waivers (4, all PERF003, all in tests/unit/cve/test_parser.py, all the same shape -- a flat set/list/dict comprehension or a short `for container in (cna, *adp): for x in container.y` walk over 1-7 small fixture records, none inherently a join): lines 14, 47, 133, 173. Each carries its own `frob:waive PERF003 reason="..."` directive at point of use.

Gates: `frob check --ticket T-0146` clean -- pass, 87 violation(s), 59 waived (matches the 87-violation main baseline exactly; the +4 waived count is this ticket's 4 new waivers, no new unwaived violations attributable to this diff). Verified by diffing `frob check` (no ticket) against main before/after: both report 87 violation(s).

Filed: none (no out-of-scope work discovered).

Not closed and not committed per process instructions -- ticket left in-progress for review.

### Post-REJECT addendum

Reviewer REJECTed on two findings; everything else (schema fidelity, error paths, no-network, Result convention, waivers, tests, docs) was verified clean and left untouched.

**1. MAJOR -- non-ASCII bytes in fixtures (fixed).** `CVE-2021-44228.json` had a literal U+2019 curly apostrophe (2 occurrences, "Microsoft's Response..." reference name) and `CVE-2024-4681.json` had literal German umlauts in its `de`-language description. Both files (top-level fixture and the copy under `fixtures/mirror/...`) were re-serialized with `json.dump(obj, fh, ensure_ascii=True, indent=4)` after `json.load`-ing the original bytes -- this re-encodes every non-ASCII character as a `\uXXXX` escape without touching JSON structure or field order, so the records stay byte-for-byte semantically identical (verified: `parse_record` on the re-serialized `CVE-2024-4681.json` still returns the German description starting with "Es wurde eine Schwachstelle...", and the escaped apostrophe in the Log4Shell reference decodes back to the original curly-quote character). All 4 affected files (`CVE-2021-44228.json`, `CVE-2024-4681.json`, and their `fixtures/mirror/cves/.../` copies) now contain zero bytes >= 0x80, confirmed via `grep -P '[^\x00-\x7F]'` returning empty across the whole `tests/unit/cve/fixtures/` tree.

Added `test_fixtures_are_ascii_and_escaped_unicode_round_trips` to `tests/unit/cve/test_parser.py`: asserts every file under `tests/unit/cve/fixtures/` (via `rglob("*.json")`) is pure ASCII bytes, and that `CVE-2024-4681.json`'s German description round-trips through `parse_record` to the expected unicode string (checked via `chr(0xFC)` rather than a literal umlaut in the test source, so the test file itself stays ASCII per the same repo-wide rule -- writing the literal character directly was blocked by this environment's own ASCII-enforcement hook, which is a live demonstration that the rule is real and load-bearing, not just documentation). This locks both directions: no future fixture add can reintroduce raw non-ASCII bytes, and the escaping cannot silently corrupt the represented text.

**2. MINOR -- curl fixture (CVE-2023-38545.json) authenticity (verified, no change).** Re-fetched the live upstream record from `raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2023/38xxx/CVE-2023-38545.json` and diffed it against the committed fixture with `diff <(python3 -m json.tool fixture) <(python3 -m json.tool upstream)` -- empty diff, i.e. byte-for-byte identical after whitespace normalization. The back-to-back Siemens `affected[]` entries (RUGGEDCOM APE1808, two near-duplicate SIMATIC S7-1500 CPU 1518-4 PN/DP MFP entries, SIMATIC S7-1500 CPU 1518F-4 PN/DP MFP, SIPLUS S7-1500 CPU 1518-4 PN/DP MFP) and the `version == lessThan == "8.4.0"` / `"7.69.0"` range shapes are genuinely present in Siemens ProductCERT's real ADP submission upstream, not a fetch or transcription artifact -- ADP data from third-party coordinators is exactly this messy in practice (repeated product entries at slightly different granularity, ranges expressed as a single boundary point). Kept verbatim; no fixture change was needed or made for this finding.

**Re-measured numbers after both fixes:**
- `uv run pytest tests/unit/cve -q`: 12 passed (was 11; +1 new hygiene test).
- `uv run pytest -q` (full suite): all pass, 2 pre-existing skips, unrelated.
- `frob test --base main`: python runner exit=0.
- `frob check --ticket T-0146`: pass, 87 violation(s), 60 waived (was 59; the new hygiene test's `next(d.value for d in ... if d.lang == "de")` lookup tripped one new PERF003, waived in place with its own `frob:waive` directive -- same shape as the pre-existing waivers, a single filtered lookup over one record's short list, not a nested join).
- Evidence: 12 pytest node ids now bound (added `tests/unit/cve/test_parser.py::test_fixtures_are_ascii_and_escaped_unicode_round_trips` via `frob ticket evidence T-0146`).

Still not closed, still not committed.
