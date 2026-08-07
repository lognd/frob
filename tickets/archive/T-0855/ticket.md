---
id: T-0855
title: 'mutation-evidence precheck diffs pre-merge in stacked worktrees: already-landed
  sibling code reads as this ticket''s diff'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_mutation_evidence.py
- tests/test_tickets_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: 'The T-0855 fix in src/frob/tickets/_mutation_evidence.py adds

    _matches_base_ref_tip and changes _touched_python_files; its unit test

    coverage (TestTouchedPythonFiles.test_already_landed_sibling_content_excluded

    and the two _matches_base_ref_tip tests) lives in

    tests/test_tickets_mutation_evidence.py, the module''s existing test home,

    not a new file. Extending scope to cover it rather than leaving the new

    tests dangling outside declared scope.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_already_landed_sibling_content_excluded
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_true_for_identical_content
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_false_for_differing_content
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_filters_to_scope_and_python
- tests/test_ticket_land.py::TestPlannedStateAutoAdvanceOnLand::test_planned_ticket_with_full_evidence_lands_to_done
designated_repro_test: null
threat: null
component: null
---
Seen landing the T-0847/T-0848/T-0850 chain: land runs the TEST016 precheck BEFORE its merge step, diffing the worktree tree against current main. In a stacked multi-ticket worktree whose siblings already landed (squash-applied to main), content-identical files still enumerate as touched until the worktree merges main, so mutants are generated from code this ticket did not change and its evidence rightly kills none of them -- a false EvidenceConfirmatoryOnly block. Coordinator workaround is merge-main-then-retry. Fix: run the precheck against the post-merge state (or skip files whose worktree content is identical to main's blob), keeping the honest block for genuinely-changed lines.