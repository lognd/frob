## Done report

Design decision: `.strata` design-file declarations are exempt from
TEST001/TEST002 entirely. A "unit test" has no defined meaning for a
`flow`/`operation`/`scenario` design construct (`_walk_strata.py` maps
these onto `SymbolKind.FUNCTION`/`METHOD` only as a best-effort analogy
for the graph-generic symbol model, not because they are invocable Python
functions) -- there is nothing for pytest to call. A design construct's
correctness is discharged by strata's own sys gates (`frob sys audit` /
self-conformance / the prover), never by a `frob:tests kind="unit"` edge.
This is consistent with T-0164's COV002 precedent: a `.strata` file is one
design artifact governed by design-level machinery, not per-symbol pytest
bookkeeping. No alternative discharge semantics were defined, because none
would be meaningful -- inventing a fake "unit test" convention for a `flow`
would just move the confusion rather than resolve it.

Changed:
- src/frob/gates/__init__.py::_test001_002 (skip records whose
  `record.id.path` ends with `.strata`, alongside the existing test-file
  skip; docstring extended to record the T-0168 decision)

Evidence:
- tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_strata_flow_declarations
  (new regression test: a `.strata` file's `flow` declaration with zero
  edges and zero matching tests must not raise TEST001/TEST002)
- tests/test_gates.py -k "TEST001 or TestConventionUnitBinding or
  TestSysGate" -- 23 passed (no regressions in adjacent TEST001/COV002
  strata-aware tests)

Filed: none (no out-of-scope work found).

Gates: `frob check --ticket T-0168` and `frob test --base main` to be
recorded post-merge in this same Done report update if either surfaces
findings; otherwise this text stands as final.
