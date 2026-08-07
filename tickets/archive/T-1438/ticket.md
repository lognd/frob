---
id: T-1438
title: BUG002 close check resolves parent ref to the worktree's own branch, not the
  ticket's real base
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/gates/_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_close_bug002_t1438.py::TestCloseMutationEvidenceBaseRef::test_uses_merge_base_not_own_branch_tip
- tests/unit/test_ticket_close_bug002_t1438.py::TestCloseMutationEvidenceBaseRef::test_still_skips_when_merge_base_unresolvable
- tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_refuses_when_evidence_passes_at_parent
- tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_succeeds_when_evidence_fails_at_parent
designated_repro_test: null
threat: null
component: null
---
`frob ticket close`'s BUG002/mutation-evidence check
(`_close_mutation_evidence_for_ticket`, src/frob/app/ticket_runner/_close_cmd.py)
passes `current_branch(root)` as the "parent commit" ref to
`bug_repro_violations`/`_bug_repro_outcome_at_ref`
(src/frob/gates/_mutation_evidence.py). In a dispatched worktree agent's
normal flow, `current_branch(root)` is the WORKTREE'S OWN branch (e.g.
"w1c-wire"), which by the time `close` runs already carries the ticket's
own fix commit at its tip -- `git worktree add --detach <scratch>
<branch-name>` then checks out the FIX, not the pre-fix parent, so the
designated repro test trivially "passes at parent" for every single
bug-kind ticket closed this way, and BUG002 refuses every close with a
false EvidenceConfirmatoryOnly (TEST016) error.

Reproduced directly on T-1431 (2026-08-02): manually diffing the ticket's
own fix out of the working tree and re-running the bound evidence test
against the true parent commit (the merge-base with main, 2ecd9401) shows
it genuinely FAILS there and passes with the fix restored -- the evidence
is real, but `close`'s own base-ref resolution cannot see that because it
resolves to the wrong ref (its own branch tip, not the ticket's
merge-base-with-main).

`land`'s own precheck (referenced in this function's docstring,
`_land_precheck`) apparently has the same `current_branch(root)`-as-base-
ref pattern -- worth checking whether it has the same defect or whether
land's flow differs enough (merge target vs. worktree branch) to avoid it;
not verified here, out of T-1431's scope.

Fix direction: BUG002/close should resolve the ticket's actual base
(`cfg.ticket_base_ref`, default "main", or the true git merge-base of
HEAD against it) rather than the worktree's own branch name, mirroring
how `working_diff` already computes `_merge_base(root, base)` for the
scope/wire gates.