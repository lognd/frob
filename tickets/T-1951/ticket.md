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

## Done report

frob:no-behavior-change reason="only the two frob:tests directive lines on _restrict_to_branch_own_files changed (re-pointed at the real, currently-collecting regression tests T-1922 actually shipped, tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal's two methods, instead of a tests/unit/test_land_committed_waive_deletion_own_files.py file that was never created). No production logic in src/frob/tickets/_land.py changed at all. There is no defect for a designated repro test to reproduce; the bound evidence (the same two real tests) correctly PASSES at both parent and fix, which is exactly what a no-behavior-change claim predicts."

Per the coordinator's note, this ticket's body also describes the four
COV003 orphans (T-0185/T-1351/T-1507/T-1512) -- that half is stale and
already fixed by T-1941 (landed a33c02831055). Only the DRIFT002 x2
half is addressed here; re-measured before starting (see below) and
confirmed the COV003 findings are already gone.

ROOT CAUSE: T-1922's land (b508b0ad3) added two `frob:tests` directives
on `_restrict_to_branch_own_files` naming
`tests/unit/test_land_committed_waive_deletion_own_files.py::
TestRestrictToBranchOwnFiles.test_filters_out_a_finding_the_branch_never_committed_itself`
and `...test_keeps_a_finding_the_branch_genuinely_committed_itself` --
but that file was never created; the two real regression tests T-1922
actually wrote landed instead in `tests/test_ticket_land.py`'s existing
`TestCommittedWaiveDeletionRefusal` class, under different names
(`test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse`
/ `test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses`),
directly exercising `_restrict_to_branch_own_files` end-to-end via
`land(..., dry_run=True)`. Confirmed via `git show b508b0ad3 --
tests/test_ticket_land.py` and `git grep -l _restrict_to_branch_own_files
-- tests/` (no hits anywhere else). The directive's target simply never
existed -- classic "directive added, file never written" drift, same
class as T-1954's DOC002 sibling finding from the same land.

Fix: re-pointed both `frob:tests` directives at the real, currently-
collecting node ids. Verified both collect and pass:
`pytest tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses`
-> `collected=2 failed=0`.

Verification: `frob check --only docanchor --only drift` (unscoped,
after T-1954's fix landed in the same worktree): 0 errors, 0 warnings, 2
waived (pre-existing DRIFT001 waivers, untouched).

Filed: none.

### Changed
```
 rapid-debt.jsonl | 1 +
 1 file changed, 1 insertion(+)
```

### Evidence
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 1015 warning(s), 705 waived
- error-findings: ARCH001@src/frob/gates/_dead_symbols.py
