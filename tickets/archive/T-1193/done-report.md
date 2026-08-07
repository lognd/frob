## Done report

No follow-up ticket needed for this disposition pass itself (the two real residues it found are already tracked as child tickets T-1265/T-1266, cited below). Investigated all six audit-residue rows with per-row file:line evidence (planner agent, worktree land 603a2857) and adversarially re-verified the four already-handled claims (reviewer APPROVE, all four CONFIRMED non-vacuous with regression tests). Registry re-dispositioned accordingly (commit on main): CHK-THEME-PYTHON-ONLY and CHK-SUBSYS-LANG-CHECK-DOCS -> handled_by:COV001 (T-0554 wires _run_gates into cpp/rust/ts pipelines); CHK-THEME-FAIL-OPEN -> handled_by:PARSE001 (T-0400 all-lockfiles scan, T-0402 disclosed non-UTF-8 skip); CHK-SUBSYS-GRAPH-EDGES -> handled_by:PARSE001 (T-0402 new-file CacheStale incl docs); CHK-SUBSYS-GATES-ACCOUNTING DRIFT001 clause handled (T-0556 body-facet union), residual c/cpp frob:tests clause repointed to child T-1266; CHK-THEME-GITIGNORED-TRUST confirmed real and repointed to child T-1265. No row silently dropped; the two real residues live on as dedicated security children. Evidence: registry concern-family test + exhaustiveness-gate test bound; frob check --only registry passes 0 errors.

### Changed
(no changed files detected)

### Evidence
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_concern_family_entries_are_deferred_or_handled` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 8 error(s), 6123 warning(s), 668 waived
- error-findings: DEPR002@src/frob/app/docs_runner.py, DEPR002@src/frob/app/map_runner.py, DEPR002@src/frob/app/outline_runner.py, DEPR002@src/frob/app/xref_runner.py, DOC001@docs/audits/docs-staleness-2026-07-29.md, DOC001@docs/design/check-fix-engine.md, DOC001@docs/design/ledger-v2.md, DOC001@docs/design/refactor-verb.md
