## Done report

T-2046 follow-through (coordinator-directed, land contention prevented
`frob ticket new` from filing this cleanly so it is tracked as a draft,
T-2067, rather than waiting): PERF004 flagged
src/frob/tickets/_land.py:1999's `sorted(p.name for p in dir_path.iterdir())`
as a loop-invariant-hoist candidate. Verified the coordinator's read before
changing anything: the sort is genuinely not loop-invariant (each iteration
sorts a DIFFERENT directory's own entries, same shape as the existing
_rapid_sweep.py waiver), but it is also unnecessary -- the only use of
`entries` is `entries != ["ticket.md"]`, an equality test against a
single-element list where order can never affect the result (any second
entry, whichever side it sorts to, already fails the length/membership
test). Deleted `sorted()` rather than waiving PERF004, since the waiver
route would have permanently encoded a wrong explanation (unhoistable) for
a call that was actually just redundant.

Added a regression test
(TestCommitOrphanedNewTicketDirOnlyDrift::test_extra_file_sorting_before_ticket_md_is_never_committed)
that specifically uses an extra filename ("aaa-before.txt") sorting BEFORE
"ticket.md" alphabetically, pinning that the guard refuses identically
regardless of where the surprise entry would have sorted -- this is the
case that would have gone silently wrong if the removal were ever
mistakenly paired with a change to compare only entries[0] or similar.

Measurement: `frob check --only perf`, full unscoped run, grepped for
`PERF004.*_land.py`. Before (sorted() present): 1 finding, `src/frob/
tickets/_land.py:1999`. After (sorted() removed): 0 findings for that
file. `pytest tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py`:
13 passed both before and after (the new test is added in the
test-only commit ec004ebbc, before the fix commit be58a38e9, and already
passes at that point too since it pins behavior rather than reproing a
bug -- this is a quality/perf fix, not a BUG-kind ticket, so BUG002's
repro-must-fail-first discipline does not apply the same way; the split
commit is kept anyway for auditability).

T-2046's own three acceptance shapes re-verified in this same tree:
test_two_well_formed_orphaned_dirs_are_both_committed (two valid dirs
both commit), test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
(mixed dirty tree declines fully, commits nothing),
test_one_unparseable_dir_among_several_commits_nothing (one non-parsing
dir among several yields no commits) -- all pass unchanged post-fix.

Disposed the T-1693 verify quarantine raised on T-2046's land commit
(38074dd92c2c): `frob verify dispose --file-ticket
"PERF004:src/frob/tickets/_land.py:=T-2046" --reason "..."` -- confirmed
CLEARED, deferred landing resumes.

### Changed
```
 src/frob/tickets/_land.py                          |  2 +-
 .../test_land_dirty_main_orphaned_ticket_t2026.py  | 19 ++++++++
 tickets/T-2067/ticket.md                 | 53 ++++++++++++++++++++++
 3 files changed, 73 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_extra_file_sorting_before_ticket_md_is_never_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2067, SELFAUDIT001@design
