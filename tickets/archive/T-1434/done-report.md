## Done report

Confirmed: yes, frob ticket land's worktree-merge flow could silently
discard a freshly stamped frob-coverage.lock.json. Root cause located in
src/frob/tickets/_land_git_ops.py's _auto_resolve_out_of_scope_conflicts:
frob-coverage.lock.json is essentially never inside a landing ticket's own
declared scope (it is a shared, cross-cutting artifact, not owned by any
one ticket), so any GENUINE merge conflict on it (both the worktree and
main independently ran --stamp-coverage since diverging) fell into the
same code path as an ordinary out-of-scope conflict: keep one side
(git checkout --theirs, main's side) unconditionally, with no freshness
or ratchet comparison. That matches the "reverted to an older committed
value" shape both T-1270 and T-1419 independently observed -- confirmed,
not refuted.

Fix: src/frob/tickets/_land_git_ops.py::_merge_coverage_lock_conflict, a
narrow, file-specific resolver invoked before the general blind-checkout
loop in _auto_resolve_out_of_scope_conflicts. It reads both conflicting
sides via `git show :2:<path>` / `:3:<path>`, parses them as the lock's
{"source_sha", "module_line"} shape, and keeps the ELEMENTWISE MAX of
both sides' module_line percentages for every module present on either
side -- the same "never silently lower a committed floor" principle
_apply_lock_ratchet (T-1363) already applies to a single side's own
write, extended across a two-sided merge. Falls back to the pre-existing
blind-checkout behavior only if either side fails to parse (never worse
than before this ticket, only better when it succeeds).

Verified with a new reproduction test
(tests/test_ticket_land.py::TestCoverageLockConflictMerges::
test_conflicting_lock_merges_to_the_higher_of_both_sides): seeds a base
lock, has the worktree stamp a higher number for one module and main
independently stamp a higher number for a DIFFERENT module, lands, and
confirms BOTH sides' higher numbers survive in the merged result rather
than either being silently discarded. The full existing
tests/test_ticket_land.py suite (203 tests) still passes with this
change, including TestOutOfScopeConflictAutoResolved (the ordinary
out-of-scope conflict behavior for files other than the coverage lock is
completely unchanged).

Not a workflow-only finding: this is a genuine code defect with a code
fix, not purely an agent-habit issue needing only a playbook correction
-- though docs/guides/agent-playbook.md (already in scope) is updated
too (new section 6f) so an agent who still sees a stray
frob-coverage.lock.json diff at land time knows land now merges it
correctly and does not need T-1270's `git checkout` workaround anymore.

### Changed
```
 Makefile                             |  31 ++++-
 docs/guides/agent-playbook.md        |  55 +++++++++
 src/frob/gates/_coverage.py          |  76 ++++++++++++
 src/frob/tickets/_land_git_ops.py    | 112 +++++++++++++++++
 tests/test_gates.py                  |  90 ++++++++++++++
 tests/test_ticket_land.py            |  71 +++++++++++
 tests/unit/test_makefile_coverage.py |  55 +++++++++
 tickets.md                           | 231 ++++++++++++++++++++++++++++++++++-
 8 files changed, 714 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCoverageLockConflictMerges::test_conflicting_lock_merges_to_the_higher_of_both_sides` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 515 warning(s), 694 waived
- error-findings: ARCH001@src/frob/tickets/_land_git_ops.py, PRE001@tickets/T-1434, SELFAUDIT001@design
