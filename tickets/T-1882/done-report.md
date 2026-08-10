## Done report

Changed:
- src/frob/app/ticket_runner/_query.py::_renumber -- no-argument `frob ticket renumber` no longer runs the destructive whole-ledger form at all (removed outright, not guarded); `--dry-run` still previews read-only via `frob.tickets.renumber(dry_run=True)`.
- src/frob/app/ticket_runner/_query.py::_renumber_one -- refusal message no longer names the no-argument form as a remedy; names only `renumber <old> <new>`.
- src/frob/tickets/_new_renumber.py::renumber -- added `dry_run` kwarg (preview-only, no lock, no write) and a live-cross-worktree-lease refusal (`_refuse_if_other_worktree_holds_live_lease`) before any real write; split `_renumber_dry_run`/`_log_bulk_renumber_preview` out to stay under ARCH001.
- src/frob/tickets/_new_renumber.py::renumber_one -- same live-lease refusal added ahead of the v1-mode write path.
- src/frob/tickets/_renumber_v2.py::renumber_one_v2 -- same live-lease refusal added ahead of the v2-mode (git mv) write path.

Investigation (requirement 3): `git grep` found no production caller of the bulk `frob.tickets.renumber` other than the CLI's own no-arg dispatch. `frob.gates._fix_engine.fix_tick002_renumber` (the TICK002 auto-fix, the actual remedy for the incident that motivated this ticket) calls `finalize_draft` -> the single-id `renumber_one`, never the bulk form. With no legitimate caller, the no-arg CLI dispatch is deleted outright rather than guarded behind an opt-in flag, per this repo's standing "delete the verb, don't add a mechanism to manage it" policy. The underlying `frob.tickets.renumber` library primitive is kept (still tested, still doc-anchored) for a future caller with a real need, but the CLI can no longer reach it for a real write -- only `--dry-run` surfaces it.

Evidence: 7 ids bound via `frob ticket evidence T-1882` (see ledger entry) -- covering the bulk-renumber contiguity/blocked-by primitives (pre-existing, still passing), the new `dry_run=True` no-write guarantee, the new live-cross-worktree-lease refusal (real two-worktree git fixture), and the new CLI-level refusal/dry-run behavior via a real subprocess (`tests/system/test_cli_ticket.py`).

Filed: none -- no out-of-scope work discovered during this ticket.

Gates: `frob check --ticket T-1882 --budget` clean (0 errors across all 43 gate families, run in two budget-chunked passes). `frob check --land-parity` clean (0 unscoped errors). `pytest tests/test_tickets.py tests/test_ticket_leases_cross_worktree.py tests/system/test_cli_ticket.py` all pass (180 collected, 0 failed).

Design/doc note: `docs/modules/tickets.md` and `design/frob.strata` were both held by other in-progress tickets' live leases (T-1832, T-1870/others) for the whole duration of this ticket, so this change does not touch either -- `renumber`'s docstring/`frob:doc` anchor still describes its contract accurately (only a `dry_run` kwarg and a refusal path were added, no behavior change to the documented contract), and the CLI-level system test added coverage through an *already-declared* file (`tests/system/test_cli_ticket.py`) specifically to avoid needing a new `design/frob.strata` interface= entry.

### Changed
```
 src/frob/app/ticket_runner/_query.py       |  87 ++++++++++++++-----
 src/frob/tickets/_new_renumber.py          | 130 ++++++++++++++++++++++++++++-
 src/frob/tickets/_renumber_v2.py           |  15 ++++
 tests/system/test_cli_ticket.py            |  62 ++++++++++++++
 tests/test_ticket_leases_cross_worktree.py |  62 ++++++++++++++
 tests/test_tickets.py                      |  22 +++++
 tickets/T-1882/ticket.md                   |  34 +++++++-
 7 files changed, 388 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestSchemaExtras::test_renumber_makes_ids_contiguous` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestSchemaExtras::test_renumber_rewrites_blocked_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestSchemaExtras::test_renumber_dry_run_previews_without_writing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_bulk_renumber_refused_by_unmerged_sibling_worktrees_live_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_bulk_renumber_dry_run_still_works_under_a_live_lease` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestBulkRenumberCliRemoved::test_no_args_always_refuses` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestBulkRenumberCliRemoved::test_dry_run_still_previews_read_only` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 945 warning(s), 695 waived
- error-findings: PRE001@tickets/T-1882, REG002@docs/design/registry/check-coverage.yaml
