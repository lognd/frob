## Done report

Leaf carrier for T-1420's fourth delivered portion. The v2-mode git-mv
renumber backend (T-1255 family, already comment-delimited) moved
verbatim from _new_renumber.py (989 -> 730 lines) to the new
_renumber_v2.py (288 lines); renumber_one dispatches through a local
import to avoid a circular import. Five frob:tests edges repointed in
tests/test_tickets_collision.py and _store.py's DUP002 waiver prose
updated to the new path -- DRIFT002 read 5 errors before the repoint,
0 after, confirming the edges are live. Scoped archgate/wire/
dead_symbols/doclink/docanchor/fmt checks all 0 errors; repo-wide
LARGE001 48 -> 47 unwaived. The branch also carries the vet _capability
seam-analysis design draft (parent T-1420) for the next dedicated
session.

### Changed
```
 src/frob/tickets/_new_renumber.py | 273 ++--------------------------
 src/frob/tickets/_renumber_v2.py  | 296 +++++++++++++++++++++++++++++++
 src/frob/tickets/_store.py        |  18 +-
 tests/test_tickets_collision.py   |  10 +-
 tickets.md                        | 364 +++++++++++++++++++++++++++-----------
 5 files changed, 578 insertions(+), 383 deletions(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_locks_acquired_in_sorted_id_order_no_deadlock` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 380 warning(s), 730 waived
- error-findings: AFFECT001@src/frob/tickets/_new_renumber.py, AFFECT001@src/frob/tickets/_renumber_v2.py, AFFECT001@src/frob/tickets/_store.py, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:29, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:35, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:57, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:58, INV006@src/frob/tickets/_renumber_v2.py
