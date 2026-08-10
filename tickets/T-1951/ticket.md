---
id: T-1951
title: COV003 x3 (T-1351/T-1507/T-1512) + DRIFT002 x2 in src/frob/tickets/_land.py
  -- unscoped error floor regression
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Full unscoped frob check --only coverage --only doclink --only drift on main (root checkout, commit b041a31b4 at time of filing) found 6 errors, none attributable to T-1933/T-1935 (confirmed: identical findings reproduce from a completely separate checkout with no worktree changes). Findings: COV003 on T-0185/T-1351/T-1507/T-1512 (evidence 'tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure' or T-0185's own evidence no longer resolves to a collected test -- likely test_check.py was edited by a recent land without re-verifying these tickets' bound evidence), plus DRIFT002 x2 on src/frob/tickets/_land.py::_restrict_to_branch_own_files (its frob:tests edges to tests/unit/test_land_committed_waive_deletion_own_files.py no longer resolve). This looks like floor drift from concurrent lands (T-1720/T-1922/T-1928/T-1934 all landed recently) that a post-land sweep has not yet caught or filed. Investigate whether an existing sweep-filed ticket already covers this (check rapid-debt.jsonl/recent T-19xx tickets) before duplicating; if not, fix the stale evidence ids/test references.