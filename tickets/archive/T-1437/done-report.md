## Done report

Root cause (confirmed by direct reproduction, not just theory): git does
not write any path's resolved merge content back to the actual
working-tree file until the ENTIRE git-merge machinery finishes -- it
only ever hands a merge-driver invocation three TEMP files (%O/%A/%B) for
the ONE path it is resolving. So the old _archived_ids(root), a plain
disk read of tickets-archive.md, always saw the PRE-merge archive from
inside a live tickets.md merge-driver invocation, even though
tickets-archive.md is ALSO registered to merge=frob-ledger and may be
concurrently resolving its own new content. This reproduced exactly the
observed incident: a ticket done+archived on main after a worktree
branched got resurrected into tickets.md on the worktree's next real git
merge main.

Fix 1 (src/frob/app/ticket_runner/_land_cmd.py):
_archived_ids_for_merge_driver resolves archived ids from git OBJECTS
instead of the working tree -- git rev-parse MERGE_HEAD names the commit
being merged in (real for the whole duration of an in-progress merge),
and git show HEAD:tickets-archive.md / git show
MERGE_HEAD:tickets-archive.md read each side's actual committed archive
content directly from the object store, sidestepping working-tree
staleness entirely. The union of ids from both refs is used. Degrades to
the old disk-based _archived_ids(root) whenever MERGE_HEAD cannot be
resolved (not currently inside a git merge) or either ref's content fails
to parse. Verified frob ticket land's own internal splice call
(_merge_main_into_worktree) does NOT share this defect: there root is the
authoritative main checkout being read FROM (never the branch being
merged), so its own disk state was never stale to begin with -- this
already had test coverage
(test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive).

Fix 2 (src/frob/tickets/_archive.py, AC[1]): _write_archived_and_active
no longer hard-refuses with Err(DuplicateId) when an id is present in
BOTH the active ledger and the archive -- it collapses to the archive's
existing copy (never overwritten) and still drops the id from the active
ledger, returning the count of tickets genuinely newly archived. This is
the CLI repair path the incident needed: before this, a worktree left
with a stray active/archive duplicate (from a stale pre-fix merge, or any
other cause) had to fall back to the playbook's manual section 10b
restore recipe.

Scope was widened via frob ticket scope --add (src/frob/app/
ticket_runner/_land_cmd.py, src/frob/tickets/_archive.py) after
investigation showed the real defect and its fix live outside the
ticket's originally declared scope (_land_merge.py, _reporting.py) --
splice_ledger itself (in _land_ledger_merge.py, re-exported via
_land_merge.py) already correctly accepts an archived_ids parameter; the
bug was entirely in WHAT was passed as archived_ids at the live-merge
call site, and in archive()'s own refusal behavior.

Both fixes reproduced against the real (not stale-globally-installed)
worktree code: the merge-driver test drives _merge_driver directly
in-process against a genuine MERGE_HEAD (a real git merge --no-commit
left in a conflicted state via -c merge.frob-ledger.driver=false, since a
shelled-out `uv run frob` from a tmp-dir cwd would resolve to some other
installed frob, not this worktree's own patched code). I manually
verified the merge-driver test fails without the fix (reverted
archived_ids=_archived_ids_for_merge_driver(root) to archived_ids=frozenset()
and re-ran -- the test correctly failed, then restored the real fix and
re-ran green) before finalizing.

### Changed
```
 docs/modules/tickets.md                      |  68 ++++++++++++-
 src/frob/app/ticket_runner/_close_cmd.py     |  51 ++++++----
 src/frob/app/ticket_runner/_land_cmd.py      |  81 +++++++++++++++-
 src/frob/tickets/_archive.py                 |  65 ++++++++++---
 tests/test_ticket_merge_driver.py            | 138 +++++++++++++++++++++++++-
 tests/test_tickets.py                        |  44 +++++++++
 tests/unit/test_ticket_close_bug002_t1438.py | 140 +++++++++++++++++++++++++++
 tickets.md                                   | 108 ++++++++++++++++++++-
 8 files changed, 657 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_id_present_in_both_active_and_archive_collapses_not_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 443 warning(s), 693 waived
- error-findings: DUP001@tests/test_ticket_merge_driver.py, OPAQUE001@tests/unit/test_ticket_close_bug002_t1438.py, PRE001@tickets/T-1437, SELFAUDIT001@design, WIRE001@tests/unit/test_ticket_close_bug002_t1438.py
