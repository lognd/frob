---
id: T-1678
title: 'BUG002 compares a main-landed fix against itself: base_ref defaults to main'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_mutation_evidence.py
- tests/test_gates_mutation_evidence.py
- tickets/T-1678/ticket.md
- tickets/T-1678/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: BUG002 vacuous-comparison fix lives entirely in _mutation_evidence.py; regression
    coverage in its paired test file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: BUG002 vacuous-comparison fix lives entirely in _mutation_evidence.py; regression
    coverage in its paired test file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1678/ticket.md
  reason: SCOPE001 flags the ticket's own v2 per-ticket ledger file as out of scope;
    tickets.md is implicitly in-scope for every ticket per playbook sec 4, this is
    its v2-layout equivalent
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1678/done-report.md
  reason: v2 ledger layout splits the Done report into its own per-ticket file; implicitly
    in-scope like tickets/T-1678/ticket.md
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_same_as_head_is_vacuous
- tests/test_gates_mutation_evidence.py::TestBugRepro::test_fix_committed_direct_to_main_is_unresolved_not_refused
designated_repro_test: null
threat: null
component: null
---
check_bug_repro / bug_repro_violations in src/frob/gates/_mutation_evidence.py take base_ref: str = 'main'. The check re-runs the designated repro test at that ref to prove the test FAILS without the fix and PASSES with it.

That is correct for the worktree flow: an agent's fix lives on a branch, main genuinely lacks it, so main is a valid pre-fix ref. It is degenerate for work committed DIRECTLY to main, which is exactly the coordinator's flow. There, base_ref='main' resolves to HEAD -- the fix commit itself -- so the check runs the repro test against the fix and reports:

  T-1676's designated reproduction test PASSED at the parent commit
  (ada33703) -- this evidence does not prove the defect was fixed

ada33703 IS the fix. The message calls it 'the parent commit' while naming the commit under test, so the operator is told their evidence is confirmatory-only when in fact the comparison was vacuous. Observed on T-1676, 2026-08-06; the bound test genuinely does fail before the fix (the old code returned Err(PytestFailed) where the test asserts is_ok).

This is the R1/R2 shape: a check reporting a real-sounding negative when it could not actually make the comparison it claims to have made.

Work:
1. Resolve the pre-fix ref from the TICKET, not from a hardcoded branch name -- the commit the ticket started at, or the merge-base of the current branch against main, so it means the same thing whether the fix landed via a worktree or directly on main.
2. When the resolved ref CONTAINS the fix (ref is an ancestor-or-equal of HEAD and the ticket's own commits are already in it), the comparison is impossible: report that explicitly as UNRESOLVED rather than as a failed obligation. Per T-1664, a check that cannot decide must say so instead of emitting a verdict.
3. The message must never call a commit 'the parent commit' when it is the commit under test.

T-1676 was closed with --skip-mutation-evidence citing this ticket.