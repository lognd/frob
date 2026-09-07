---
id: T-4130
title: 'all three CI legs red after the 79-commit push: 12 failures in four clusters,
  three of them a landed change with unupdated callers or test doubles'
state: done
kind: bug
origin: agent
created: '2026-09-06'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_conftest_suite_result_status.py
- tests/unit/test_check_gates_summary.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_runtime_deps.py
- tickets/T-4136/ticket.md
scope_breadth_ack: true
scope_breadth_ack_reason: 'SCOPE002 closure-explosion class (T-3299/T-3902/T-3957/T-4098/T-4103):
  these test files'' pre-existing (untouched by T-4130) frob:tests bindings to src/frob/app/check_runner.py
  etc. pull in unrelated modules this ticket does not touch. No frob:waive-addressable
  mechanism exists for a tickets.md:0 finding; acked per the T-4103 precedent rather
  than absorbing unrelated files into scope.'
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-4136/ticket.md
  reason: T-4130's own new-ticket file, filed for the T-4105 producer/consumer desync
    found while testing this ticket's fix
  actor: logan
  at: '2026-09-07'
evidence:
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_completed_run_format_is_unchanged
- tests/unit/test_check_gates_summary.py::TestGatesFamilyResultUnresolved::test_unresolved_findings_never_fail_the_family
- tests/unit/test_check_gates_summary.py::TestGatesFamilyResultUnresolved::test_unresolved_count_shown_as_its_own_term_not_folded_into_warn
- tests/unit/test_check_gates_summary.py::TestGatesFamilyResultUnresolved::test_errors_still_fail_the_family_regardless_of_unresolved
- tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active
- tests/unit/test_runtime_deps.py::TestRuntimeDepsDeclared::test_every_unguarded_third_party_import_is_declared
designated_repro_test: null
acceptance:
- text: given the ubuntu CI leg, when the full suite runs, then it reports zero failures
  evidence:
  - tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_completed_run_format_is_unchanged
- text: given the four landed changes named in this ticket, when the regression is
    fixed, then none of them is reverted
  evidence:
  - tests/unit/test_check_gates_summary.py::TestGatesFamilyResultUnresolved::test_errors_still_fail_the_family_regardless_of_unresolved
- text: given an import name absent from the runtime-deps mapping table, when the
    test fails, then its message says the name is unmapped rather than claiming the
    dependency is undeclared
  evidence:
  - tests/unit/test_runtime_deps.py::TestRuntimeDepsDeclared::test_every_unguarded_third_party_import_is_declared
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ALL THREE CI LEGS FAILED ON THE TEST STEP after the 79-commit push, on a base
where ubuntu and macOS were both GREEN one run earlier. This is a regression
introduced by that batch, it is the sole blocker on the alpha, and it must be
fixed before anything else.

MEASURED, ubuntu leg of run 34054144192: collected=13547 failed=12. macOS and
Windows failed the same step. Four clusters, every one attributable, and THREE OF
THE FOUR ARE THE SAME MISTAKE: a landed change updated a producer and left a
consumer that constructs or calls the same thing untouched.

CLUSTER 1 -- 7 failures, from T-4103's conftest change.
    tests/unit/test_conftest_suite_result_status.py, all seven tests
    AttributeError: '_FakeReporter' object has no attribute 'ensure_newline'
    AttributeError: '_StatsReporter' object has no attribute 'ensure_newline'
  The session-finish hook now calls a new method on the terminal reporter. Two
  hand-written reporter DOUBLES in a DIFFERENT test module do not implement it.
  T-4103 added and verified fixtures in its own test file and never ran the
  other module that doubles the same object.
  NOTE FOR THE FIX: T-4103's final implementation does NOT call the method the
  ticket originally prescribed -- it uses the terminal writer's current-line
  width, because the prescribed call is a no-op under this repo's doubled quiet
  flag. Read what the code actually does now before updating the doubles, and
  make the doubles implement the real surface rather than the one named here.

CLUSTER 2 -- 3 failures, a signature change with unupdated callers.
    tests/unit/test_check_gates_summary.py, TestGatesFamilyResultUnresolved
    TypeError: _gates_family_result() missing 1 required positional argument:
    'root'
  A required parameter was added to a private helper and three call sites in
  this test module still pass the old arity. Find which landed ticket added it
  before changing anything -- if the parameter is genuinely required, the tests
  update; if it could be optional with a safe default, that is the smaller
  change and may be the better one. Decide deliberately and say which.

CLUSTER 3 -- 1 failure, from T-3985's subject-count primitive.
    tests/unit/test_app_runners_batch6.py
      TestJsonStdoutStructuralGuard
      ::test_legitimate_json_payload_is_byte_identical_with_guard_active
    The JSON payload gained a subject_count key set to None and the test asserts
    byte-identical output.
  THIS ONE NEEDS A JUDGEMENT, NOT A TEST EDIT. The test's name says the payload
  must be byte-identical; that is a compatibility contract for anything parsing
  our JSON. Decide whether the new key belongs in this payload at all, and
  whether a null subject count is meaningful to a consumer or is itself the
  silent-zero shape the primitive exists to prevent. If the key stays, update
  the test AND say why the contract may change. If it does not belong here,
  remove it from this payload instead.

CLUSTER 4 -- 1 failure, and the test is wrong, not the code.
    tests/unit/test_runtime_deps.py
      ::TestRuntimeDepsDeclared::test_every_unguarded_third_party_import_is_declared
    "unguarded top-level imports with no [project].dependencies declaration
     (add the dep or guard the import): {'pathspec': {...}}"
  MEASURED: pathspec IS declared, at pyproject.toml line 26. The test carries a
  hardcoded import-name-to-distribution-name table and pathspec is not in it, so
  a missing TABLE ENTRY renders as a missing DEPENDENCY. The remedy the message
  tells you to apply ("add the dep") is already done, so following the message
  cannot clear the finding -- a no-exit, and the fourteenth instance of that
  class.
  Add the table entry. THEN fix the message so this cannot recur: a name absent
  from the table is a different state from a name present but undeclared, and
  the two must not print the same sentence. Consider whether the table should be
  derived rather than hand-maintained -- every new dependency is a future
  instance of this bug.

WHY ALL OF THIS MATTERS BEYOND THE RED BUILD: clusters 1, 2 and 3 are the
producer/validator desync class, three times in one batch, all of them invisible
to the ticket that caused them because each ticket verified its own files. A
ticket-scoped check that passes while the batch is red is the measurement trap
this repo has already documented. Whatever else is done here, record whether a
cheap producer-side guard exists -- something that fails when a landed change
alters a surface that another module doubles or calls.

MUST-FIRE FIXTURE:   the full suite is green on ubuntu.
MUST-STAY-QUIET:     none of the four landed changes is reverted -- T-4103's
                     newline fix, the family-result parameter, the subject-count
                     primitive and the pathspec migration all remain in force.
THIRD FIXTURE:       the runtime-deps test distinguishes an unmapped import name
                     from an undeclared dependency in its failure message.

ACCEPTANCE
- All 12 ubuntu failures cleared without reverting any of the four changes.
- macOS re-checked; Windows failures re-counted and NOT expected to reach zero.
- Cluster 3's contract question answered explicitly rather than by editing the
  assertion.
- The runtime-deps table entry added and its message made honest.
- All three fixtures committed.