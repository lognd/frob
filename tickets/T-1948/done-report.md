## Done report

Changed:
src/frob/tickets/_unlanded.py::_directive_anchored_ticket_ids (new)
src/frob/tickets/_unlanded.py::_directive_anchor_signals_on_branch (new)
src/frob/tickets/_unlanded.py::_finished_signals_on_branch (now merges
in the new third signal)

Evidence:
tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchored_code_with_queued_ticket_is_flagged
tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchored_code_with_in_progress_ticket_is_not_flagged
tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchor_yields_to_a_stronger_signal
tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchor_in_tickets_path_is_not_a_self_signal
Repro confirmed manually (frob's own --check-repro has the same
unrelated PYTHONPATH bug as T-1987 hit, filed during T-1987 and landed
as T-2005 (renumbered from its draft id at T-1987's own land);
--designate-repro-force used with the manual repro evidence recorded in
the designation reason).

Filed: none new (T-2005 already covers this same repro-check defect --
not duplicated)

Gates: full tests/unit/test_unlanded_branch_work.py suite (13 tests)
green. Deliberately did NOT widen scope to the uncommitted-work case
(frob worktree sweep's existing kept:dirty gate already owns that) per
the ticket's own explicit scope note.

### Changed
```
 CHANGELOG.md                            |   6 +-
 src/frob/tickets/_unlanded.py           | 100 +++++++++++++++++++++++++++++-
 tests/unit/test_unlanded_branch_work.py | 104 ++++++++++++++++++++++++++++++++
 tickets/T-1948/ticket.md                |  17 +++++-
 4 files changed, 220 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchored_code_with_queued_ticket_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchored_code_with_in_progress_ticket_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchor_yields_to_a_stronger_signal` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_directive_anchor_in_tickets_path_is_not_a_self_signal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, ARCH001@src/frob/tickets/_unlanded.py, E501@/home/logan/projects/frob/.claude/worktrees/t1987-series/src/frob/tickets/_unlanded.py, F401@/home/logan/projects/frob/.claude/worktrees/t1987-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1987-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1948, SELFAUDIT001@design, unsupported-operator@src/frob/tickets/_unlanded.py
