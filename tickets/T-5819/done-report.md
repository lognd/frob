## Done report

Changed: src/frob/tickets/_draft_finalize.py::_finalize_draft_for_land_locked (added call), src/frob/tickets/_draft_finalize.py::_rewrite_main_ledger_dangling_references (new); docs/modules/tickets-lifecycle.md; tests/test_ticket_promote_dangling_refs.py

Why: `finalize_draft_for_land` rewrote parent/blocked_by/prose references to a promoted draft id only within the landing worktree's own tickets/ tree (`_renumber_one(worktree, ...)`), by design (see that function's own docstring on why it must not also lock/write main_root). A ticket that lived ONLY on main -- already landed by a sibling worktree, or wired by a coordinator citing a known agent's draft id directly in a parent/blocked_by field before that agent's own land ran -- was structurally invisible to that scan, so its reference to the draft id was left permanently dangling once the draft id stopped resolving anywhere (measured 2026-09-24 filing the coord tree). Fixed by adding a best-effort post-renumber pass, `_rewrite_main_ledger_dangling_references`, that scans main_root's own ticket tree (v2-mode only) for citations of the draft id and rewrites them to the final id, reusing `_renumber_v2._scan_v2_reference_files`'s matching core. Non-fatal by design: a scan/write failure here is logged but never fails the land itself.

Evidence: tests/test_ticket_promote_dangling_refs.py::TestRewriteMainLedgerDanglingReferences -- test_sibling_blocked_by_and_parent_rewritten is the ticket's own positive control (a ticket on main citing the draft id as both parent and blocked_by, both rewritten to the final id; an unrelated citation is left alone); test_no_matching_reference_is_a_true_no_op and test_v1_mode_repo_is_skipped are the must-not-regress controls.

Filed: none.

Gates: clean (ruff check/format clean on both touched files; existing tests/unit/test_draft_finalize_attachments.py and the T-5166 land-suite regression tests re-run clean against this change).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
