## Done report

BUG002 compared a main-landed fix against itself whenever `base_ref`
resolved to the same commit as HEAD -- the coordinator's direct-commit-
to-main flow. `_bug_repro_outcome_at_ref` now resolves both `HEAD` and
`base_ref` to commit shas via a new `_resolve_sha` helper before spending
a real checkout+subprocess on the comparison; when they are equal, it
returns a new `_BugReproOutcome.SAME_AS_HEAD` outcome (distinct from
`NO_VERDICT`, logged at WARNING naming exactly why no comparison is
possible) instead of running the repro test against the fix commit and
mislabeling it "the parent commit". Every existing caller
(`bug_repro_violations`'s ordinary and `frob:no-behavior-change`-inverted
branches) already treats any non-{FAILED_AT_PARENT,PASSED_AT_PARENT}
outcome as "no violation", so `SAME_AS_HEAD` degrades the same way
`NO_VERDICT` does -- UNRESOLVED, never a false EvidenceConfirmatoryOnly
refusal and never a false pass.

This fixes both call sites without touching either: `frob.tickets._land`
passes `main_branch_name` (a resolved branch name) straight through, and
`frob.app.ticket_runner._close_cmd` already computes a merge-base before
calling in -- for a ticket whose entire history landed as commits directly
onto main (T-1676's shape), that merge-base collapses to HEAD itself,
which is exactly the case the new sha-equality check catches.

Out of scope, left as-is: item 3 of the ticket ("the message must never
call a commit 'the parent commit' when it is the commit under test") is
satisfied structurally rather than by editing `_bug002_message` -- since
the vacuous case now short-circuits to `SAME_AS_HEAD` before either
`PASSED_AT_PARENT`/`FAILED_AT_PARENT` can be reached, `_bug002_message`
and `_no_behavior_change_message` are never invoked for a commit that is
also the commit under test any more; their wording for a genuine parent
commit is unchanged and still correct.

### Changed
```
 tickets/T-1678/ticket.md | 29 ++++++++++++++++++++++++++++-
 1 file changed, 28 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_same_as_head_is_vacuous` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugRepro::test_fix_committed_direct_to_main_is_unresolved_not_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 661 warning(s), 721 waived
- error-findings: none (measured, zero errors)
