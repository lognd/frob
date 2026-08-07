---
id: T-1657
title: 'TEST005 remainder (~55 findings): successor to T-1655'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestAutofixManifest::test_clear_autofix_manifest_swallows_oserror
- tests/test_gates.py::TestScopePrework::test_record_prework_returns_err_on_oserror
- tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_malformed_json
- tests/test_gates.py::TestScopePrework::test_load_prework_returns_none_on_schema_mismatch
- tests/test_gates.py::TestBaselineDelta::test_load_baseline_malformed_json_is_none
- tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_malformed_json_treated_as_empty
- tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths::test_schema_mismatch_treated_as_empty
- tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_malformed_toml_returns_empty
- tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths::test_non_list_rules_shape_returns_empty
- tests/test_decisions.py::test_bad_yaml_frontmatter_is_err
- tests/test_decisions.py::test_frontmatter_not_a_mapping_is_err
- tests/test_decisions.py::test_schema_validation_failure_is_err
designated_repro_test: null
threat: null
component: null
---
Successor to T-1655 (itself successor to T-1650/T-1273): T-1655's agent
closed a slice (gitio.py excerpt, doctor.py scan_venv_shims, mutate/_journal.py
record_journal_progress + remove_journal, vet/_capability.py
non_executable_line_numbers, refactor/_gitops.py working_tree_clean +
current_sha -- 8 symbols, 15 new tests, all real Err/edge-path induced
failures bound via frob:tests) and must NOT close T-1655 on partial
progress per its own body's standing instruction -- filing this successor
instead, per that same instruction.

Remaining work, last measured on a fresh non-deflated coverage.xml
(make coverage run completed cleanly, coverage.xml copied from
.frob/coverage.partial.xml, no TEST017 finding): approximately 53-60
TEST005 findings remain (68 measured at T-1655 start, minus the 8 symbols
whose branch/line coverage crossed threshold in this slice -- re-measure
unscoped with `frob check --only test` before burning down further, since
some counts may shift as branch percentages move independently of symbol
count).

Remaining breakdown by package at T-1655 start (re-verify -- gates and
app in particular are large and were NOT touched this round):
gates=14, app=10 (incl. app/ticket_runner), serve=9, arch=8, tickets=5,
scaffold=5, refactor=4 (1 of 5 closed), testing=3, vet=1 (1 of 2 closed),
strata=2, mutate=0 (2 of 2 closed), dup=1 (src/frob/dup/_pipeline/_smt.py
-- involves z3 SMT solver internals, genuinely harder to reach with a
narrow unit test; may need a dedicated investigation rather than a quick
Err-path test), doctor.py=0 (closed), gitio.py=0 (closed).

Method (carried forward, it worked):
- Measure UNSCOPED. A --ticket-scoped zero is not a package zero.
- Verify coverage.xml freshness and non-deflation (TEST017) before
  trusting any count; if TEST017 fires, stop and report rather than
  burning down against fiction. Recover from .frob/coverage.partial.xml
  per playbook 6d if the promote-to-committed step is blocked.
- Write tests that would FAIL if the behaviour broke -- induce the real
  failure (OSError, malformed input, missing git ref) and assert the
  documented Result/contract. A test that only executes lines to move a
  percentage is worse than the missing coverage -- it hides the gap
  permanently.
- Bind each test to the symbol it covers with a frob:tests directive,
  node-level.
- Prioritize `gates` (14) and `app`/`serve` (10/9) next -- they are the
  largest remaining clusters and were not touched this round; `dup`'s
  z3-solver code may warrant a scope note or separate investigation if a
  narrow unit test proves impractical.

Do NOT close this ticket on partial progress. Either drive it to zero or
file a named successor first and say so in the Done report, same as
T-1650/T-1655 before it.