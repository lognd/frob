## Done report

Implemented archive_v2 (src/frob/tickets/_archive.py): a v2-mode `archive()`
now dispatches to a plain `git mv tickets/<id> tickets/archive/<id>` per
done/dropped ticket, taken under that ticket's own `ticket_lock`, with zero
`ticket.md`/`done-report.md` content rewrite -- the T-0959 archive-clobber
failure mode is structurally impossible on this path (design section 4.3),
not merely guarded the way the v1 monofile path still is. `git_mv_dir`
(src/frob/tickets/_store.py) is a fresh copy of `_new_renumber._git_mv_ticket_dir`'s
shape rather than a shared import, since `_new_renumber` already imports
`_load_merged` FROM `_archive` and a reverse import would cycle (waived
DUP002 with that reasoning).

`load_archive` and `_store_mode` are made v2-aware: `load_archive` globs
`tickets/archive/T-####/ticket.md` directly (no content-hash cache, unlike
the single-file archive path -- archived directories are never rewritten in
place so there is little churn for a cache to save), and `_store_mode` now
checks the archive glob too, so a v2 repo whose active tree has been fully
drained still reads as 'v2' rather than misdetecting as fresh/legacy.

Three regression tests added to tests/test_ticket_land.py::TestArchiveV2,
each bound to one acceptance criterion:
- test_archive_moves_directory_via_git_mv_no_content_rewrite: a real git
  repo, archive() the ticket, assert the moved file's bytes are identical
  to pre-move and `git status --porcelain` shows an `R` rename line (AC 0/1).
- test_archive_v2_regression_two_sided_divergence_no_clobber: reproduces the
  T-0959 shape directly on the v2 path -- main archives one ticket, an
  independently-branched worktree closes and archives a second (plus
  re-archives the first, since its own checkout predates main's sweep), a
  real `git merge` unions both into main with no lost block (AC 2).
- test_archived_v2_ticket_still_resolves_as_blocker: archives a ticket
  referenced via `blocked_by`, then confirms `load_queue`'s merged view
  still resolves it as DONE (AC 3).

Widened T-1256's scope to add docs/modules/tickets.md and
docs/design/ledger-v2.md via `frob ticket scope --add` -- SCOPE002 flagged
pre-existing `frob:doc` edges on `archive`/`load_active`/`load_queue`
(functions the scoped files already declared, not touched by this diff)
pointing into those docs.

Pre-existing, out-of-scope findings NOT touched by this ticket (verified
identical against the same test run with src/frob/tickets/_store.py and
_archive.py reverted to their committed state before this ticket's edits):
- TestArchiveResurrection::test_archived_id_never_resurrected and
  TestArchiveSpliceDiscipline's two land tests fail on main already (an
  IncompleteLand/T-0463 completeness-gap refusal over `.frob/` scratch
  files getting swept into a test's own `git add -A`) -- unrelated to
  archive_v2, confirmed by re-running them against the unmodified files.
- SCOPE001 on design/frob.strata and src/frob/tickets/_new_renumber.py:
  residue of T-1253/T-1254/T-1255's already-committed, already-closed
  work earlier in this same worktree branch, not touched this ticket.
- A long tail of pre-existing COV002/COV006/COV007 findings in
  src/frob/gates/**, src/frob/strata/_compliance.py,
  src/frob/refactor/_apply.py, design/frob.strata -- none in this
  ticket's scope or diff.
- ARCH001 in src/frob/refactor/_scan.py -- pre-existing, last touched by
  the T-1197 land commit, not this ticket.

Gates run: `frob check --ticket T-1256 --only gates-native` (pass except
the pre-existing ARCH001 above) and `--only gates-fast` (PRE001 cleared by
a re-sweep; TEST001 cleared by adding a frob:doc/frob:tests pair to the one
under-covered new symbol, v2_archive_dir; remaining errors are the
pre-existing ones enumerated above, confirmed unrelated to this diff).

### Changed
```
 .gitattributes                     |  11 +
 design/frob.strata                 |  16 +
 docs/design/ledger-v2.md           |  13 +
 docs/modules/tickets.md            |  72 ++-
 src/frob/tickets/_archive.py       |  85 +++-
 src/frob/tickets/_land.py          |  75 +++-
 src/frob/tickets/_land_finalize.py | 111 ++++-
 src/frob/tickets/_new_renumber.py  | 273 +++++++++++-
 src/frob/tickets/_reporting.py     |  66 ++-
 src/frob/tickets/_store.py         | 683 ++++++++++++++++++++++++++--
 tests/test_ticket_land.py          | 311 +++++++++++++
 tests/test_tickets.py              | 121 +++++
 tests/test_tickets_collision.py    | 146 ++++++
 tests/unit/test_process_lock.py    | 159 +++++++
 tests/unit/test_ticket_store.py    | 180 ++++++++
 tickets.md                         | 883 +++++++++++++++++++++++++++++++++++--
 16 files changed, 3116 insertions(+), 89 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestArchiveV2::test_archive_moves_directory_via_git_mv_no_content_rewrite` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveV2::test_archive_v2_regression_two_sided_divergence_no_clobber` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveV2::test_archived_v2_ticket_still_resolves_as_blocker` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveV2::test_first_ever_archive_uses_real_git_mv_not_rename_fallback` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
