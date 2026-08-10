---
id: T-1951
title: COV003 x3 (T-1351/T-1507/T-1512) + DRIFT002 x2 in src/frob/tickets/_land.py
  -- unscoped error floor regression
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
blocked_by:
- T-1941
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: rapid-debt.jsonl
  reason: 'rapid-debt.jsonl is auto-appended by frob ticket land''s own rapid-profile

    debt bookkeeping (T-1681) during this ticket''s own land attempts/merges

    in this shared worktree -- not content this ticket authored, but the

    file is touched by the commits it produces.

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Full unscoped frob check --only coverage --only doclink --only drift on main (root checkout, commit b041a31b4 at time of filing) found 6 errors, none attributable to T-1933/T-1935 (confirmed: identical findings reproduce from a completely separate checkout with no worktree changes). Findings: COV003 on T-0185/T-1351/T-1507/T-1512 (evidence 'tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure' or T-0185's own evidence no longer resolves to a collected test -- likely test_check.py was edited by a recent land without re-verifying these tickets' bound evidence), plus DRIFT002 x2 on src/frob/tickets/_land.py::_restrict_to_branch_own_files (its frob:tests edges to tests/unit/test_land_committed_waive_deletion_own_files.py no longer resolve). This looks like floor drift from concurrent lands (T-1720/T-1922/T-1928/T-1934 all landed recently) that a post-land sweep has not yet caught or filed. Investigate whether an existing sweep-filed ticket already covers this (check rapid-debt.jsonl/recent T-19xx tickets) before duplicating; if not, fix the stale evidence ids/test references.