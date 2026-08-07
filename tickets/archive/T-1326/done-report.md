## Done report

Extended T-1323's uncommitted-state waive-deletion guard to also scan the
branch's already-COMMITTED history (merge-base..HEAD), closing the
laundering gap flagged at T-1323's own review: a frob:waive deletion
committed mid-ticket, rather than left dirty, was invisible to a check
that only ever inspected `git diff HEAD`.

_land_merge.py: factored the diff-parsing core out of
_uncommitted_waive_deletions into _waive_deletions_in_diff(worktree,
diff_args), reused by a new _committed_waive_deletions(worktree,
merge_base) (diff_args=(f"{merge_base}..HEAD",)). Added
_committed_out_of_scope_waive_deletions, mirroring
_uncommitted_out_of_scope_waive_deletions's ownership/declaration logic
(_deletion_owned + _waive_deletion_declared_in_done_report) exactly.

_land.py: added _check_committed_waive_deletions (ERROR-tier refusal,
LandError.OutOfScopeWaiveDeletion, names file+rule in the log line) and
wired it into _land_precheck, ahead of both the v1 and v2 merge paths
(both dispatch through the same _land_precheck call in _land_locked, so
both are covered). Resolving main_branch had to move earlier in
_land_precheck to compute the true merge-base via the existing
_true_merge_base helper; split _load_ticket_for_land and
_resolve_main_branch_for_land out of _land_precheck to keep it under the
ARCH001 line-count threshold after the new check was added.

Merge-base drift (a waiver deleted on MAIN's own side of the ancestor,
never touched by the landing branch) is correctly NOT counted: the diff
range is merge_base..HEAD, which never includes main-only commits.

Multi-line/continuation frob:waive comments (a reason="..." wrapping onto
a following physical line) are explicitly scoped OUT, documented in
_waive_deletions_in_diff's docstring: _LAND_WAIVE_LINE_RE only ever
matched a single physical line (mirrors frob.gates._fix_engine's own
_WAIVE_SINGLE_LINE_RE scope), on both the uncommitted and committed
paths equally -- not a regression this ticket introduces, but not closed
either; flagged as a named follow-up rather than silently left unnoted.

Tests added (tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal):
committed out-of-scope undeclared deletion refuses before merge;
committed in-scope deletion allowed; committed Done-report-declared
deletion allowed; merge-base drift (main-side deletion) not counted
against the branch.

### Changed
```
 src/frob/tickets/_land.py       | 141 +++++++++++++++++++++++++++++++++-------
 src/frob/tickets/_land_merge.py | 120 +++++++++++++++++++++++++++++-----
 tests/test_ticket_land.py       | 138 +++++++++++++++++++++++++++++++++++++++
 tickets.md                      |  77 +++++++++++++++++++++-
 4 files changed, 434 insertions(+), 42 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_in_scope_waive_deletion_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_declared_in_done_report_waive_deletion_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_merge_base_drift_deletion_on_main_side_not_counted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
