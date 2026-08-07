## Done report

Changed: none (evidence-only close)

Investigation: the ticket body itself states 0 symbols at exactly 0.0%
branch coverage for this package -- all 11 findings are partial-coverage/
module-line, the lower-priority tier, so acceptance[1]'s dead-code
routing criterion is vacuously satisfied (nothing to judge or route).

The registry package has an unusually large, well-exercised test surface:
tests/test_registry_models.py, tests/test_capability_registry.py (445
tests collected across just these two plus tests/test_registry_staleness.py),
plus tests/test_registry_reconciliation_*.py (7 files),
tests/test_registry_exhaustiveness.py, tests/test_registry_corpus.py,
tests/test_check_coverage_registry.py, tests/unit/strata/test_registry_cross_*.py.
Ran a representative subset standalone: uv run pytest
tests/test_registry_models.py tests/test_registry_staleness.py
-p no:cacheprovider -n0 -q -- 24/24 pass. Sampled three and confirmed each
is a real behavioral assertion (not import-only/filler):
- TestLoadRegistryDir::test_loads_typed_entries: asserts real typed
  entries parsed from a registry YAML fixture
- TestReg010Gate::test_missing_gate_rule_entry_warns: asserts the REG010
  gate actually fires a warning for an uncovered gate rule id
- TestNegativeFixtures::test_re_compile_is_not_eval: asserts the
  capability-pattern matcher correctly does NOT fire on a benign
  re.compile call (a negative-fixture false-positive guard)

`frob check --ticket T-1300 --only test` in this worktree: 0 errors, 6
warnings, none TEST005 (TEST005 not computable here -- no coverage stamp
in this fresh worktree, TEST006 fires instead; playbook sec 6b makes
coverage stamping coordinator-only). Per the T-1297 precedent (sibling
TEST005 ticket, same 0-at-0.0% shape), binding acceptance[0] on the
strength of the ticket's own 0-at-0.0% claim plus this sampled behavioral
verification across an unusually large existing test surface, not a
fresh full-package TEST005 recount (which this worktree cannot produce).

Evidence:
- tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries
- tests/test_registry_staleness.py::TestReg010Gate::test_missing_gate_rule_entry_warns
- tests/test_capability_registry.py::TestNegativeFixtures::test_re_compile_is_not_eval

Filed: none

Gates: uv run frob check --ticket T-1300 --only test -- 0 errors, 6
warnings (none TEST005), 3 pre-existing waived warnings unrelated to this
ticket.

### Changed
```
 tickets.md | 285 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 268 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestReg010Gate::test_missing_gate_rule_entry_warns` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestNegativeFixtures::test_re_compile_is_not_eval` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 7 error(s), 390 warning(s), 684 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design, TICK003@tickets.md
