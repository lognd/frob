## Done report

Changed:
- src/frob/vet/_capability_registry.py (new) -- single-source
  CAPABILITY_KINDS (13), DangerousOperation/MatrixExcuse models,
  ~70 structured entries across python/typescript/rust/c-cpp,
  CAPABILITY_MATRIX_EXCUSES (per-cell reasons, blanket C/C++ retired),
  capability_matrix()/unexcused_empty_cells()/validate_registry_kinds(),
  NO_CAPABILITY_MODULES.
- src/frob/vet/_capability.py -- _PATTERNS compiled from the registry;
  c-cpp first-class scanned language; scan_file_operations() names the
  firing registry entries; self-match exclusion extended.
- src/frob/app/sys_runner.py -- capability-matrix report wired into
  frob sys audit, printing the coverage proof line, gating on 0
  unexcused cells.
- src/frob/strata/_selfconform.py, _threat.py -- extended kinds and
  DEFAULT_BENIGN_CAPABILITIES for the new kinds.
- design/frob.strata -- may sql/fetch_url/deserialize on graphlang/vet +
  6 honestly-reasoned assume discharge claims; self-model counts 6->12.
- tests/test_capability_registry.py (new) -- matrix exhaustiveness,
  drift-lock vs CWE_CATALOG, 29 per-cell fire fixtures + 2 negatives,
  and TestNoSilentNeedleRegression (merge-base needle snapshot +
  reclassification allowlist, reproduces the Popen( scenario).
- tests/test_vet.py, tests/system/test_frob_self_model.py -- updated.

Evidence: 46 node ids recorded via frob ticket evidence.

Gates: frob check --ticket T-0158 exit 0 -- ruff-check/ruff-format pass,
gates 0 violation(s)/347 waived. frob sys audit PROVED, self-conformance
PROVED, capability coverage: 13 kind(s) x 4 language(s), 29 cell(s)
patterned+proven, 23 excused with reasons, 0 unexcused. Full pytest green.

Reviewer: round 1 REJECT (dropped Popen( needle -- silent detection
regression); round 2 REJECT (E501 lint). Both fixed: Popen( restored via
a mechanical merge-base-vs-compiled needle diff (62 needles compared,
Popen( the only true drop, urllib./fetch( reclassified to fetch_url with
reasons, cmdclass excused) plus a regression-lock test; E501 reflowed.
Final: all six substantive cruxes PASS -- needle equivalence
independently re-derived and mutation-tested, exhaustiveness mutation-
tested, stdlib/c-cpp coverage spot-checked, fixtures real, deferred
tickets honest, gates clean. APPROVE.

Filed: T-0180 (closed-world unknown-import accounting), T-0181
(survey-prioritized third-party registry entries), T-0182 (per-operation
fire/negative fixtures) -- deferred slices, not silent stubs.
