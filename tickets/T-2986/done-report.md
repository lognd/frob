## Done report

Changed:
- src/frob/tickets/_archive.py::_archive_v2_move_tickets
- src/frob/tickets/_archive.py::_rewrite_moved_attachment_paths (new)
- tickets/archive/T-2195/ticket.md (repair)
- tickets/archive/T-2197/ticket.md (repair)
- tickets/archive/T-2244/ticket.md (repair)
- tickets/archive/T-2328/ticket.md (repair)
- tickets/archive/T-2350/ticket.md (repair)
- tickets/archive/T-2543/ticket.md (repair)

Root cause: `archive_v2` moves a done/dropped ticket's directory via
`git_mv_dir` (tickets/<id>/ -> tickets/archive/<id>/) but never touched
the ticket's own `attachments[].path` field. `_cov004` always resolves an
attachment as `Path("tickets") / attachment.path`, so a path still
carrying the pre-move `<id>/attachments/...` shape silently stopped
resolving the moment the directory moved.

Fix: `_archive_v2_move_tickets` now calls a new
`_rewrite_moved_attachment_paths` after each `git_mv_dir`, which does a
targeted text substitution on the just-moved ticket.md (`- path:
<id>/...` -> `- path: archive/<id>/...`), a no-op when the ticket carries
no attachment in that shape. Deliberately not routed through
`write_ticket` (its v2 path resolves the ACTIVE directory via
`v2_ticket_dir`, which would recreate `tickets/<id>/` at the path
`git_mv_dir` just vacated).

Found vs repaired: scanned every archived ticket's attachment list (13
entries total across the archive). 10 entries in 6 tickets
(T-2195 x3, T-2197 x1, T-2244 x1, T-2328 x3, T-2350 x1, T-2543 x1)
carried the broken id-prefixed shape; all 10 target files were verified
still present at the moved (archive/<id>/attachments/...) location, so
all 10 were safely repairable and all 10 were repaired via a mechanical
text substitution (git diff per file is a single one-line change). The
remaining 3 entries (T-1433, legacy shared attachments/<id>/ shape,
never touched by archive's directory move) already resolved correctly
and needed no change. Nothing was found unrepairable.

COV004 before/after (unscoped `frob check --only coverage --json`):
before = 10 findings (measured live on main pre-fix, matches ticket's
own measured evidence); after = 0 findings (confirmed via
scripts/check_summary.py on this worktree post-fix and post-repair).
Two unrelated pre-existing COV001/COV007 findings remain on
scripts/branch_stranded_work_analysis.py (untouched by this change,
confirmed via `git status --porcelain` showing no diff there).

Ledger integrity: `uv run frob ticket list` exits 0 both before this
change (confirmed via the ticket's own pre-triage measurement) and after
(measured explicitly this ticket, exit=0, 164 active tickets counted
correctly).

Regression test: tests/test_ticket_land.py::TestArchiveV2::
test_archived_ticket_attachment_still_resolves_for_cov004 -- archives a
v2 ticket carrying a self-contained-shaped attachment, asserts the
recorded path is rewritten to the archive/ prefix, asserts the file
resolves at that path, and runs coverage_gate directly to assert COV004
does not fire.

Filed: none -- no out-of-scope defect discovered.

Gates: `frob check --only coverage` clean of COV004 findings; 2
unrelated pre-existing errors on scripts/branch_stranded_work_analysis.py
untouched by this change (not waived, out of scope, verified via git
status showing no diff to that file).

### Changed
```
 src/frob/tickets/_archive.py     | 74 ++++++++++++++++++++++++++++++++++++++++
 tests/test_ticket_land.py        | 71 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2986/ticket.md         |  9 +++--
 tickets/archive/T-2195/ticket.md |  6 ++--
 tickets/archive/T-2197/ticket.md |  2 +-
 tickets/archive/T-2244/ticket.md |  2 +-
 tickets/archive/T-2328/ticket.md |  6 ++--
 tickets/archive/T-2350/ticket.md |  2 +-
 tickets/archive/T-2543/ticket.md |  2 +-
 9 files changed, 162 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestArchiveV2::test_archived_ticket_attachment_still_resolves_for_cov004` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 16 error(s), 2138 warning(s), 853 waived
- error-findings: AFFECT001@tests/test_ticket_land.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2986/src/frob/tickets/_archive.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, PRE001@tickets/T-2986, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
