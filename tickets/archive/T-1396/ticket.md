---
id: T-1396
title: 'TEST005 burn-down: src/frob/gates remaining findings past the 0.0% priority
  tier'
state: done
kind: feature
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/gates/**
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/gates/test_scope_symref_helpers.py::TestMacroSymbolFile::test_no_separator_returns_none
- tests/gates/test_scope_symref_helpers.py::TestMacroSymbolFile::test_qualname_not_macro_suffixed_returns_none
- tests/gates/test_scope_symref_helpers.py::TestMacroSymbolFile::test_macro_suffixed_qualname_returns_file_path
- tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_bare_file_symref_exact_match
- tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_bare_file_symref_prefix_match
- tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_bare_file_symref_no_match
- tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_dotted_symref_exact_match
- tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_dotted_symref_parametrized_match
- tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_dotted_symref_no_match
- tests/gates/test_scope_symref_helpers.py::TestFileOfSymrefInScope::test_dotted_symref_file_in_scope
- tests/gates/test_scope_symref_helpers.py::TestFileOfSymrefInScope::test_dotted_symref_file_out_of_scope
- tests/gates/test_scope_symref_helpers.py::TestFileOfSymrefInScope::test_bare_path_symref_in_scope
designated_repro_test: null
threat: null
component: null
---
## Description + plan
T-1279's brief listed 12 symbols in src/frob/gates at exactly 0.0%
branch coverage. Investigation found 10 of the 12 (secrets_gate,
parse_failure_gate, opaque_gate, scan_emitted_rule_ids/
generated_gate_rule_ids partially, scope_digest, prework_gate,
test_gate, release_gate, perf_gate, run_gates) already carry real,
behavioral frob:tests-bound unit tests exercising both clean and
finding-producing branches (e.g. tests/test_secrets_gate.py,
tests/test_gates.py::TestParseFailureGate,
tests/test_gates.py::TestKnownGateRuleIds, tests/test_gates.py's
TestScopeDigest*/TestPreworkGate*/TestTestGate*/TestReleaseGate*/
TestPerfGate*/TestRunGates* classes). Their reported 0.0% is most
plausibly the known coverage-attribution gap tracked by T-1235/T-1395
(subprocess + multiprocess worker coverage not being attributed back
to the parent process) rather than a genuine test gap -- this ticket
does not re-litigate that; it is out of `src/frob/gates/**` scope.

Genuine, closeable gaps found and fixed by T-1279 itself:
- `mutation_evidence_violations`'s `Err` (ExecDisabled) degrade branch
  had no direct test -- added (tests/gates/test_mutation_evidence_err_branches.py).
- `scan_emitted_rule_ids`'s comment-skip line, missing-scanned-base-dir,
  and unresolved-const-ref branches had no direct test -- added
  (tests/gates/test_rule_id_scan_branches.py).

Remaining work for a genuine, non-attribution-driven TEST005 burn-down
of src/frob/gates (179 findings total, only 12 were the 0.0% priority
tier T-1279 targeted): audit the other ~167 findings in the 0-75%
band across src/frob/gates/** for real missing-branch gaps (as opposed
to attribution noise) and close them with behavioral tests, same
discipline as T-1279 (no assert-True filler, judge dead code before
writing a test for it).

## Acceptance
- [ ] GIVEN the gates package at the 75%/70% floors WHEN frob check --only test runs THEN it reports 0 TEST005 findings under src/frob/gates/** that are NOT explained by the T-1235/T-1395 coverage-attribution gap
- [ ] GIVEN a symbol judged to have a genuine missing-branch gap WHEN a test is added THEN it asserts real behavior, never filler