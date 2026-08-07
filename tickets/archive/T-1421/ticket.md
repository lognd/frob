---
id: T-1421
title: 'BUG002: a bug ticket must prove the defect no longer reproduces -- evidence
  must fail at the parent commit'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_mutation_evidence.py
- tests/test_gates_mutation_evidence.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates_mutation_evidence.py::TestBugRepro::test_reconstructed_uncalled_guard_passes_at_both_is_refused
- tests/test_gates_mutation_evidence.py::TestBugRepro::test_reconstructed_wired_guard_fails_at_parent_is_permitted
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_reason_present_suppresses
- tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_non_bug_kind_never_checked
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_security_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_bug_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_findings_no_violations
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_bare_directive_without_reason_does_not_suppress
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_no_directive_at_all
- tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_first_pytest_node_id_is_designated
- tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_no_pytest_evidence_is_none
- tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_exec_disabled_is_no_verdict
- tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_worktree_add_failure_is_no_verdict
- tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_no_pytest_evidence_no_violation
- tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_waived_with_reason_no_violation
- tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_passed_at_parent_is_error_violation
- tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_failed_at_parent_no_violation
- tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_no_verdict_no_violation
designated_repro_test: null
acceptance:
- text: GIVEN a kind=bug ticket whose bound evidence passes at BOTH its parent commit
    and the fix commit WHEN it is closed or landed THEN it is refused, because that
    evidence does not establish the defect was fixed
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBugRepro::test_reconstructed_uncalled_guard_passes_at_both_is_refused
- text: GIVEN a kind=bug ticket whose bound evidence fails at the parent commit and
    passes at the fix WHEN it is closed or landed THEN it is permitted
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBugRepro::test_reconstructed_wired_guard_fails_at_parent_is_permitted
- text: GIVEN a bug whose defect genuinely cannot be reproduced in a test WHEN the
    ticket is closed THEN an explicit justified override is required and logged loudly,
    never a silent pass
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_reason_present_suppresses
- text: GIVEN the new check WHEN its added land-time cost is measured THEN that cost
    is recorded, and only the designated reproduction evidence is re-run rather than
    the whole suite
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_non_bug_kind_never_checked
threat: null
component: null
---
A bug ticket must prove the defect it describes no longer reproduces -- not merely that new code exists and is tested.

THE GAP, with five measured instances from 2026-08-01/02. Each of these landed, passed its own tests, satisfied its acceptance, and closed honestly. In every case the defect remained live on main afterwards:

  T-1384  added own_obligations_clean to frob.tickets._evidence -- nothing computed it. Follow-up T-1387.
  T-1399  added gate_claims_verified to the same module -- nothing computed it. Follow-up T-1410.
  T-1391  added only_paths to FMT001's fix handler -- nothing passed it. Follow-up still open.
  T-1239  split the cache recovery except-clause -- an adjacent IntegrityError still destroyed shared caches. Follow-up T-1416.
  T-1401  corrected the ratchet clamp -- the stamped write does not survive to git. Follow-up T-1419.

No agent was dishonest and no test was weak. Each disclosed the gap accurately. The problem is structural: a ticket's acceptance verifies THE CHANGE, not THE EFFECT. "I added a guard and tested the guard" is true and satisfiable while the hazard is untouched.

WHY TEST016 DOES NOT ALREADY COVER THIS. TEST016 refuses a bug/security ticket whose bound evidence kills zero mutants of its own diff-touched code. That is a real and valuable check -- it catches confirmatory-only tests -- and it fired correctly this session (T-1371). But it is scoped to the diff. In all five cases above the new code WAS mutation-detectable by its own unit tests; the defect was that no caller reached it. TEST016 cannot see an absent caller. The two checks are complementary, not redundant.

THE PROPOSED RULE. For a kind=bug (and kind=security) ticket, at least one bound evidence test must FAIL at the ticket's parent commit and PASS at the fix. That is the mechanically checkable form of "the defect no longer reproduces", and it would have caught all five: a test driving the real close path fails before T-1410's wiring and passes after, whereas a unit test of an uncalled guard passes at both commits and is therefore not evidence of a fix at all.

IMPLEMENTATION NOTES, not prescriptive.

Cost is the main design question. Checking one test at one prior commit is cheap; the naive shape is a detached worktree at the parent commit, run the single named node id, assert non-zero exit. Do NOT run the suite. Measure and report the added land-time cost -- if it is material, consider running it only for the SUBSET of evidence explicitly designated as the reproduction test rather than all bound ids.

Not every bug ticket can satisfy this honestly, and the design must say what happens then. Genuine cases: a fix for a crash that cannot be reproduced deterministically; a defect whose reproduction requires an environment the test suite cannot create (the xdist worker crash in T-1240 was diagnosed as already-fixed by T-1385 and needed no new code at all); a documentation or ledger correction filed as kind=bug. The escape hatch must be explicit and justified in the Done report -- named, not silent -- in the same spirit as the existing --skip-mutation-evidence override, which logs loudly and requires justification rather than suppressing the finding.

Reuse rather than rebuild. frob already has the machinery: T-0754's ClaimDivergence re-evaluates captured claims post-merge, T-1410 runs a gate and filters findings by glob, and the mutation-evidence path already checks out and perturbs code. This should compose with those, not duplicate them -- the repo's no-duplication rule applies with force here.

WHAT SUCCESS LOOKS LIKE. Reconstruct any one of the five tickets above as a fixture: a ticket whose bound evidence passes at BOTH the parent and the fix commit must be refused. A ticket whose evidence fails at the parent and passes at the fix must be permitted. Both directions need a regression test, or this gate is exactly the kind of unverified guard it exists to prevent.