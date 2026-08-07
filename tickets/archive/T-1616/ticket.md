---
id: T-1616
title: BUG002 is unsatisfiable for a pure refactor, and reclassifying kind silently
  dodges it
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/app/ticket_runner/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_reason_present_recognized
- tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_bare_directive_without_reason_not_recognized
- tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange::test_passed_at_parent_no_violation
- tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange::test_failed_at_parent_is_error_violation
- tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange::test_no_verdict_no_violation
- tests/test_ticket_evidence.py::TestKindHistory::test_change_before_any_work_not_recorded
- tests/test_ticket_evidence.py::TestKindHistory::test_change_after_evidence_recorded
- tests/test_ticket_evidence.py::TestKindHistory::test_change_after_done_report_recorded
- tests/test_ticket_evidence.py::TestKindHistory::test_history_is_append_only
- tests/test_ticket_evidence.py::TestKindHistoryLandNotice::test_notice_logged_at_land
- tests/test_ticket_evidence.py::TestKindHistoryLandNotice::test_no_history_no_notice
designated_repro_test: null
threat: null
component: null
---
BUG002 requires a bug-kind ticket's designated evidence test to FAIL at the parent commit, proving the defect existed and was fixed. That is exactly right for a behavioral defect. It is unsatisfiable by construction for a pure refactor, where the whole obligation is the opposite: prove behavior is UNCHANGED. A refactor's tests pass at the parent because they must.

frob's kinds are feature, bug, security, ux, docs, invariant, incident. None of them means refactor. So a ticket that fixes a structural finding with no behavior change -- an ARCH001 over-length function, a DUP001 duplicate, a LARGE001 file split -- has no honest kind:
- Filed as bug, it is blocked by BUG002 forever and cannot land.
- Filed as feature, it lands, but only because the classification dodged the check.

Observed 2026-08-05: T-1593 (splitting _land_core, _check_mutation_evidence, run_pending_sweep to clear the last 3 ARCH001 errors on main) was filed as bug and refused by BUG002. Its own Done report certifies "pure extraction, same call order, same short-circuit/error semantics, same log lines, no new branches" -- the strongest possible statement that no repro test could fail at the parent. It was relabeled to feature to land.

That relabel is defensible on the merits here, and it is ALSO the finding: if a one-word kind change is all that stands between a bug-kind ticket and skipping its evidence obligation, then BUG002 is advisory for anyone willing to relabel. A gate that can be dodged by reclassification is not enforcing what it claims.

Two things to fix, and the second matters more than the first:

1. Give refactor-shaped work an honest home: either a refactor kind, or an explicit "no behavioral change intended" attribute that BUG002 recognizes and that swaps the obligation rather than removing it. A refactor's evidence obligation should be REAL but DIFFERENT -- prove behavior unchanged (the touched code's existing tests pass at both parent and tip, characterization tests exist for the extracted seams), rather than prove a defect fixed. That keeps the rigor and matches what a refactor can actually demonstrate.

2. Make reclassification visible. Changing kind on a ticket that already has evidence or a Done report should be recorded in the ledger and surfaced at land, so a reviewer sees "this was a bug when the work was done and became a feature before it landed" instead of a silent edit. Kind changes before any work starts are ordinary; kind changes that relax an evidence obligation after the fact are the ones worth showing.

Related: this is the same family as the empty-diff TEST016 refusals seen when a shared series worktree lands its whole branch -- an evidence rule correctly firing on a shape its author did not anticipate. The fix in both cases is to give the unanticipated shape its own honest path, never to weaken the rule.