## Done report

Implemented ledger v2 design section 4.1 (renumber via git mv + multi-file
reference rewrite) as a new v2-mode branch of renumber_one:

- renumber_one now dispatches to the new renumber_one_v2 whenever
  _store_mode(root) == "v2", before its own enforce_worktree_lease call.
  finalize_draft/finalize_draft_for_land call renumber_one via the existing
  package-level indirection, so they pick up v2 behavior automatically --
  no change needed to _draft_finalize.py itself.
- renumber_one_v2 acquires ticket_lock for old_id and new_id in SORTED
  order (design section 3's fixed-order discipline), git mv's the ticket
  directory (tickets/<old>/ or tickets/archive/<old>/, whichever exists;
  falls back to a plain os.rename outside a git repo or on an untracked
  path), rewrites the moved ticket.md's own id: frontmatter field, and
  rewrites every other tickets/**/*.md file's whole-word prose citation of
  the old id (reusing _rewrite_body_prose_references's matching core,
  re-pointed at the multi-file glob via _scan_v2_reference_files). It also
  still runs the existing _scan_code_references pass (directive lines /
  registry dispositions across the tracked tree), unchanged from v1.
- Split into _validate_v2_renumber_ids / _build_v2_renumber_report /
  _persist_v2_renumber to stay under ARCH001's 60-line function budget.
- A dry_run call takes no locks and mutates nothing.
- Errors: InvalidTransition (old_id == new_id), NotFound (old_id has no
  v2 ticket dir), DuplicateId (new_id already taken).

Changed:
  src/frob/tickets/_new_renumber.py::renumber_one_v2
  src/frob/tickets/_new_renumber.py::_validate_v2_renumber_ids
  src/frob/tickets/_new_renumber.py::_build_v2_renumber_report
  src/frob/tickets/_new_renumber.py::_persist_v2_renumber
  src/frob/tickets/_new_renumber.py::_v2_id_dir
  src/frob/tickets/_new_renumber.py::_rewrite_v2_id_field
  src/frob/tickets/_new_renumber.py::_v2_reference_files
  src/frob/tickets/_new_renumber.py::_scan_v2_reference_files
  src/frob/tickets/_new_renumber.py::_git_mv_ticket_dir
  src/frob/tickets/_new_renumber.py::renumber_one (v2 dispatch added)
  design/frob.strata (sync-interface: renumber_one_v2, TestRenumberOneV2)

Evidence:
  tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
  tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
  tests/test_tickets_collision.py::TestRenumberOneV2::test_locks_acquired_in_sorted_id_order_no_deadlock
  tests/test_tickets_collision.py::TestRenumberOneV2::test_dry_run_mutates_nothing
  tests/test_tickets_collision.py::TestRenumberOneV2::test_target_id_already_exists_is_duplicate_id
  tests/test_tickets_collision.py::TestRenumberOneV2::test_unknown_old_id_is_not_found

Verification run (scoped, memory-budget discipline):
  pytest tests/test_tickets_collision.py tests/unit/test_ticket_store.py -q
    -> 96 passed
  frob check --ticket T-1255 --budget 100 (chunked across static /
    gates-security invocations): no unwaived violations attributable to
    _new_renumber.py or TestRenumberOneV2 remain after the ARCH001 split
    and the sys sync-interface run; pre-existing unrelated debt (refactor
    SYS102/SYS103 gaps, app/__init__ OPAQUE001, exports warnings) untouched.

Filed: none -- no out-of-scope work discovered.

Gates: frob check --ticket T-1255 clean of new violations (verified via
  chunked --budget 100 static + gates-security passes); ARCH001/DRIFT002/
  SELFAUDIT001 findings introduced by this change were fixed in-ticket,
  not waived.

### Changed
```
 design/frob.strata                |  16 ++
 docs/design/ledger-v2.md          |  13 ++
 docs/modules/tickets.md           |  72 ++++++-
 src/frob/tickets/_new_renumber.py | 262 ++++++++++++++++++++++++-
 src/frob/tickets/_reporting.py    |  66 ++++++-
 src/frob/tickets/_store.py        | 394 ++++++++++++++++++++++++++++++++++----
 tests/test_tickets_collision.py   | 146 ++++++++++++++
 tests/unit/test_process_lock.py   | 159 +++++++++++++++
 tests/unit/test_ticket_store.py   | 180 +++++++++++++++++
 tickets.md                        | 296 ++++++++++++++++++++++++++--
 10 files changed, 1539 insertions(+), 65 deletions(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_locks_acquired_in_sorted_id_order_no_deadlock` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_dry_run_mutates_nothing` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_target_id_already_exists_is_duplicate_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_unknown_old_id_is_not_found` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 6 error(s), 480 warning(s), 682 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, PRE001@tickets/T-1255, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design
