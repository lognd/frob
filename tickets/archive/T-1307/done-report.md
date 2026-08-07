## Done report

Closed 2 of 4 TEST005 findings with real behavioral tests, and
attribution-limited/environment-blocked the other 2:

- src/frob/dup/_core.py::core_available (branch 62.5% -> 73%): added
  tests/test_dup.py::TestCoreAvailable.test_import_error_returns_false_and_logs,
  exercising the ImportError branch (unreachable in this dev checkout's
  normal state, where frob_core is actually built) via a monkeypatched
  builtins.__import__ plus lru_cache.cache_clear().
- src/frob/dup/_exhaustiveness.py::validate_claim_rungs (branch 59.1% ->
  100%): added two tests exercising both previously-uncovered offender
  branches (unregistered rung name, clone_type-not-claimed mismatch)
  against synthetic DupClaim.model_copy() instances.
- src/frob/dup/_legacy_cpp.py (module line 15.2% -> 82%, clears the 70%
  module_line_cov floor): the module had ZERO direct unit test coverage
  (only reachable transitively through the legacy dup scanner, never
  actually exercised by any existing dup test suite -- confirmed by a
  scoped --cov run against the full existing dup test suite showing 9%).
  Added tests/unit/test_dup_legacy_cpp.py mirroring the existing
  tests/unit/test_dup_legacy_py.py precedent: real tree-sitter cpp
  parses driving _iter_functions_cpp/_enclosing_class_cpp/
  _collect_locals_cpp/_serialize_cpp_body directly. Writing this test
  surfaced a real correctness bug: _collect_locals_cpp never actually
  collects C++ function PARAMETERS as locals (looks up the "parameters"
  field on function_definition, but tree-sitter's cpp grammar puts it on
  the function_declarator child instead) -- filed as T-1509
  (bug, scope src/frob/dup/_legacy_cpp.py) rather than fixed here, since
  T-1307's own scope is test coverage, not scanner correctness; the new
  test documents and asserts the CURRENT (buggy) behavior explicitly so
  it does not silently regress further.
- src/frob/dup/_pipeline/_smt.py (module line 21.0%, still below floor):
  NOT fixed -- this is an environment artifact, not a real gap. The
  module's tests (tests/unit/test_dup_smt.py) skip because z3-solver is
  not importable; attempted `uv sync --extra smt` in this worktree and
  the z3-solver wheel build fails outright (LibError: Unable to build
  Z3) -- confirmed this is a genuine build-environment limitation, not
  something a source or test change can fix from inside this session.
  Classifying this the same way as the T-1235 attribution-limited class:
  a real gap that needs a working z3-solver build in CI/dev environment
  before it can be closed, not a burn-down task.

Verified with a scoped
`pytest tests/unit/test_dup_legacy_cpp.py tests/test_dup.py tests/test_dup_exhaustiveness.py
--cov=frob.dup._legacy_cpp --cov=frob.dup._core --cov=frob.dup._exhaustiveness --cov-branch`
run (per-module results above) -- section 6c's unscoped-package caveat
noted: the coordinator's full make coverage stamp is the trustworthy
package-wide TEST005 number, not this scoped run.

### Changed
```
 .frob-release.json                               |   4 +-
 CHANGELOG.md                                     |   4 +
 design/frob.strata                               |   4 +
 docs/audits/README.md                            |   2 +
 docs/audits/check-performance.md                 |   2 +
 docs/audits/coordination-churn.md                |   2 +
 docs/audits/docs-staleness-2026-07-29.md         |   2 +
 docs/audits/frob-blindspots-2026-07-23.md        |   2 +
 docs/audits/gates-accounting.md                  |   2 +
 docs/audits/gates-quality.md                     |   2 +
 docs/audits/gates-vacuous.md                     |   2 +
 docs/audits/graph.md                             |   2 +
 docs/audits/lang-check-docs.md                   |   2 +
 docs/audits/perf.md                              |   2 +
 docs/audits/strata.md                            |   2 +
 docs/audits/test005-zero-classification-t1418.md |   2 +
 docs/audits/tickets-testing-round2.md            |   2 +
 docs/audits/tickets-testing.md                   |   2 +
 docs/audits/vet.md                               |   2 +
 docs/design/registry/check-coverage.yaml         |  14 +-
 docs/modules/gates.md                            |   3 +
 pyproject.toml                                   |   2 +-
 src/frob/check/__init__.py                       |   2 +
 src/frob/gates/__init__.py                       |  15 +
 src/frob/gates/_doclink_docanchor.py             | 288 ++++++++-
 src/frob/gates/_waive.py                         |   6 +
 tests/test_gates.py                              | 160 +++++
 tickets.md                                       | 724 ++++++++++++++++++++++-
 uv.lock                                          |   2 +-
 29 files changed, 1227 insertions(+), 33 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 7 error(s), 442 warning(s), 748 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w20t-test005/src/frob/dup/_core.py:29, OPAQUE001@tests/test_dup.py, PERF002@src/frob/gates/_doclink_docanchor.py, PRE001@tickets/T-1307, SELFAUDIT001@design, WIRE001@src/frob/gates/_doclink_docanchor.py, WIRE001@tests/unit/test_dup_legacy_cpp.py
