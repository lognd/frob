---
id: T-0761
title: 'CRITICAL: frob ticket land can commit ledger+version but DROP all feature
  code (T-0640 false-green); T-0463 completeness assertion has a hole'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: critical
parent: T-0417
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty
designated_repro_test: null
acceptance:
- text: GIVEN a worktree branch adding a new source file WHEN frob ticket land runs
    THEN the landed commit contains that file OR land refuses with a completeness
    error; a regression test reproduces the land-drops-code shape
  evidence:
  - tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty
threat: null
component: null
---
CRITICAL false-green found 2026-07-22: frob ticket land for T-0640 marked the ticket DONE and committed the version bump + ledger line (dbae6f2f, 4 files: .frob-release.json, CHANGELOG.md, pyproject.toml, tickets.md) but carried NONE of the feature code -- src/frob/strata/_reliability.py (340 lines, NEW), the _audit.py/_waive.py/__init__.py/sys_runner.py edits, design/frob.strata dispositions, docs, tests, and litmus fixtures were all on the worktree branch (commits 2e9dce36/47e0b181/9dea1b21) and never reached main. sys audit silently lost the entire reliability family; the ticket read done with the feature absent. The T-0463 land-completeness assertion (which correctly caught a missing _scan.py on T-0235) did NOT fire. Recovered manually by cherry-picking the 3 code commits (b13d2c66/dbc00b68 + parent) 3-way onto main. Root-cause the land path: the T-0640 land followed a manual acceptance-binding + finalize sequence (store-API evidence write, git commit, then frob ticket land); investigate whether merge-main-into-worktree followed by squash-apply, or the finalize commit, produced a base against which the code commits appeared already-present, so the squash diff reduced to version+ledger only. HARDEN the completeness assertion: it must verify that every file the worktree branch changed vs the TRUE merge-base is present in the landed commit -- a NEW file the branch added that is absent from the squash is exactly the T-0235 case it claims to cover but missed here. Add a regression test reproducing land-drops-all-code-keeps-ledger.