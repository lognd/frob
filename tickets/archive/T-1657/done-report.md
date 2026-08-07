## Done report

Measured UNSCOPED, before/after, on fresh non-deflated coverage.xml (no
TEST017 finding either run):

Before: 62 TEST005 findings (make coverage: 8616 tests, 0 failed; coverage.xml
copied from .frob/coverage.partial.xml per playbook 6d).

After: 55 TEST005 findings (make coverage: 8628 tests, 0 failed after fixing
a design/frob.strata interface-list drift the new tests introduced --
`frob sys sync-interface` added the 5 new top-level test symbols to the
testsuite node's interface= list; without it, 4 self-conformance tests
failed: test_selfconform.py's TestRealGateGreen and TestCoverageTotality,
test_frob_self_model.py's test_sys_gate_zero_violations, and
test_conform_eval_needle.py's test_real_repo_design_selfconform_has_no_eval_gap
-- re-ran all 4 after the fix, all pass).

62 - 55 = 7 findings closed by this round's 12 new tests across 6 symbols:
- src/frob/gates/_fix_engine_shared.py::clear_autofix_manifest (was already
  above threshold pre-round; test added for the untested OSError branch
  anyway since a real failure mode was undertested even if not gate-flagged)
- src/frob/gates/_prework.py::record_prework (OSError write path)
- src/frob/gates/_prework.py::load_prework (malformed JSON + schema
  mismatch)
- src/frob/gates/_ratchet.py::load_ratchet_lock (malformed JSON + schema
  mismatch)
- src/frob/gates/_ratchet.py::ratchet_enabled_rules (malformed TOML +
  non-list rules shape)
- src/frob/gates/decisions.py::load_decisions (bad YAML frontmatter,
  non-mapping frontmatter, schema validation failure)
- src/frob/gates/_baseline.py::load_baseline (malformed JSON; was already
  above threshold pre-round, same rationale as clear_autofix_manifest)

Every new test induces a REAL failure (a directory where a file is
expected -> IsADirectoryError/OSError; literal malformed JSON/TOML/YAML
on disk; a schema-mismatched dict) and asserts the documented
Result[T,E]/None contract -- none merely execute lines to move a
percentage.

Filed successor: T-1661 (renumbers at land), citing the
remaining breakdown: app=10, serve=9, arch=8, tickets=5, scaffold=5,
refactor=3, testing=3, gates=9 (down from 14), strata=2, vet=2, dup=1.
Not closing T-1657 -- 55 findings remain, per its own body's standing
instruction not to close on partial progress.

Untestable this round: none attempted and abandoned; the dup/_smt.py
finding (z3 SMT solver internals) was left alone as noted in the
successor body -- same "may need dedicated investigation" caveat carried
forward from T-1655.

### Changed
```
 design/frob.strata          | 571 +++++++++++++++++++-------------------
 frob-coverage.lock.json     | 167 ++++++-----
 tests/test_decisions.py     |  42 +++
 tests/test_gates.py         |  82 ++++++
 tests/test_gates_ratchet.py |  54 ++++
 tickets.md                  | 659 +++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 1220 insertions(+), 355 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestAutofixManifest::test_clear_autofix_manifest_swallows_oserror` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_record_prework_returns_err_on_oserror` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_malformed_json` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_schema_mismatch` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestBaselineDelta::test_load_baseline_malformed_json_is_none` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_malformed_json_treated_as_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_schema_mismatch_treated_as_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_malformed_toml_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_non_list_rules_shape_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_bad_yaml_frontmatter_is_err` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_frontmatter_not_a_mapping_is_err` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_schema_validation_failure_is_err` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 2852 warning(s), 849 waived
- error-findings: none (measured, zero errors)
