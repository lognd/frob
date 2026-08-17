---
id: T-2181
title: 'T-2179 residue: ''already implemented'' still decides from scope-file overlap,
  so any branch that touched a shared file claims someone else''s ticket -- t-2107
  and t2049-series falsely claim T-2114'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_scope_touch_in_a_different_commit_is_not_correlated
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_when_nothing_touches_it
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ledger_only_churn_is_not_reported
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_scope_globs_never_reports
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_scope_touch_in_a_different_commit_is_not_correlated
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

worktrees_touching_ticket correlated "any commit touches tickets/<id>/"
and "the whole branch diff touches scope" as two independent questions.
Two unrelated commits sharing a branch (a bookkeeping ledger edit for
this ticket, and a real-work commit for a DIFFERENT ticket that happens
to touch a shared scope-glob file) could together satisfy both
conditions and produce a false "already implemented" verdict -- measured
for real: --ticket T-2114 reported t-2107 and t2049-series, neither of
which had implemented T-2114.

Fix: correlation now runs per commit. For each commit that touches
tickets/<id>/, git show --name-only is checked directly against that
SAME commit's own diff for a scope-matching file -- a single commit
must carry both signals together.

Repro test committed alone first
(tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_scope_touch_in_a_different_commit_is_not_correlated),
confirmed FAILED_AT_PARENT against c5f7ce372 (the repro-only commit) via
frob ticket evidence --check-repro, then the fix landed in a separate
commit. All 4 pre-existing tests in the same class updated for the new
per-commit git-call shape (log now uses --format=%H, followed by `git
show --name-only` per sha, instead of a single `git diff` over the
whole branch).

Filed: none -- no out-of-scope work discovered.

### Changed
```
 docs/guides/coordinator-scripts.md     | 144 +++++++++--
 scripts/fleet_status.py                | 441 ++++++++++++++++++++++++++++++---
 tests/unit/test_coordinator_scripts.py | 311 ++++++++++++++++++++++-
 tickets/T-2180/ticket.md               |   2 +-
 tickets/T-2181/ticket.md               |  12 +-
 5 files changed, 847 insertions(+), 63 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_scope_touch_in_a_different_commit_is_not_correlated` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_when_nothing_touches_it` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ledger_only_churn_is_not_reported` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_scope_globs_never_reports` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2180/src/frob/app/ticket_runner/_land_cmd.py, PERF003@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2181, SELFAUDIT001@design, TEST001@scripts/fleet_status.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
