## Done report

Design decision: a `.strata` file is one design artifact -- a single
`frob:ticket` directive on the file's `module` declaration now covers every
`node`/`flow`/`boundary`/`assert`/... nested under it for COV002 purposes,
the same blast-radius reasoning `_scope_covers` already applies at the file
level, one notch finer. Per-declaration edges are no longer demanded; a
`.strata` file with no directive anywhere still fires COV002 normally (not
a blanket exemption).

Changed:
- src/frob/gates/__init__.py::_strata_module_symref (new)
- src/frob/gates/__init__.py::_covered_by_strata_module (new)
- src/frob/gates/__init__.py::_cov002 (extended: checks strata-module
  coverage before falling through to scope coverage)

Evidence:
- tests/test_gates.py::TestCov002StrataModuleCoverage::test_module_level_ticket_edge_covers_nested_declaration
- tests/test_gates.py::TestCov002StrataModuleCoverage::test_declaration_without_module_edge_still_fires

Filed: none (no out-of-scope work found; T-0165/T-0168 explicitly left
untouched per instructions).

Gates: `frob check --ticket T-0164` clean -- 0 errors, only the pre-existing
TEST006 warn (no coverage stamp, unrelated to this change) and the usual
repo-wide waived PERF/arch advisories. `pytest tests/test_gates.py` passes
(all prior COV002 tests plus the 2 new ones).
