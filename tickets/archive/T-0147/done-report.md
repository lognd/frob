## Done report

Changed:
- src/frob/vet/_cve.py (new): MatchStatus, CweDisposition, CweLink, CveMatch, link_cwe_ids, match_dependencies_against_mirror, plus private helpers (_evaluate_entry, _status_for_affected, _product_matches, _best_cvss, _description_summary, _cwe_ids_of, _match_record_dependency, _cwe_catalog_index, _cwe_out_of_scope_index, _parse_comparable)
- src/frob/vet/_models.py::VetError (added CveMirrorInvalid member)
- src/frob/vet/__init__.py (re-exports new _cve.py symbols)
- src/frob/app/config.py::AppConfig (added vet_cve_mirror field, wired into from_external's path-field loop) [scope extension, justified above]
- src/frob/app/vet_runner.py::_cve_matches_for, _print_cve_table, _run_scan (CLI dispatch + table/JSON output) [scope extension]
- src/frob/__main__.py::_add_vet_parser (--cve-mirror flag) [scope extension]
- docs/modules/vet.md (new "CVE mirror matching (T-0147)" section, public-api anchors, Implementation notes)
- tests/unit/cve/test_vet_match.py (new, 11 tests)
- tests/unit/cve/fixtures/vet_mirror/cves/2024/1xxx/CVE-2024-1000.json, CVE-2024-1001.json (new synthetic fixtures; see docs/modules/vet.md Implementation notes for why a separate mirror from the T-0146 real-record one was needed)
- tickets.md (this ticket's scope list + Done report)

Evidence: 11 pytest node ids under tests/unit/cve/test_vet_match.py, recorded via `frob ticket evidence T-0147` (see this ticket's evidence: list above). Measured: `pytest tests/unit/cve/ tests/test_vet.py tests/test_vet_containment.py -q` -> 121 collected, 0 failures (121 = 76 + 22 + 12 + 11 across the four files, verified via --collect-only -q; the -q run itself shows dot-progress only, no summary line, under this repo's pytest-xdist config). `frob test --base main` selected touched-set python suite -> exit=0, 2.18s. `ruff check`/`ruff format --check`/`ty check` on every touched file -> clean. Manual CLI verification: `frob vet <dir> --cve-mirror <mirror>` (table and --json output) and the unconfigured/no-op and missing-mirror-loud-failure paths, all exercised by hand against a throwaway uv.lock fixture in /tmp, matching the automated test coverage.

Filed: none (no out-of-scope work discovered beyond the three CLI-wiring files already declared above).

Gates: `frob check --ticket T-0147` -- gates stage reports "pass, 87 violation(s), 67 waived" (0 unwaived violations attributable to this ticket's scope after: (1) 3 PERF001/PERF003 false-positive waivers added in this diff with specific reasons -- see src/frob/vet/_cve.py, src/frob/app/vet_runner.py, tests/unit/cve/test_vet_match.py; (2) SCOPE001/PRE001 cleared by extending T-0147's scope + `frob ticket sweep T-0147` per the justification above). The single remaining FAIL line (`ruff-format: 1 file would be reformatted`, tests/unit/cve/test_parser.py) is pre-existing on main -- verified independently by running `ruff format --check` against the main-branch copy of that file, which also fails; not touched by this diff, left for T-0148 (drive frob check gates to zero).

Known cuts (disclosed, not silently dropped): no VET-numbered gate rule feeds CVE matches into `frob check`'s enforce/exit-code path yet (reporting-only this slice, `VET012`-shaped follow-up candidate); product matching is exact case-insensitive string match against `affected[].product`, not a real CPE-dictionary join (undercounts, documented in docs/modules/vet.md).
