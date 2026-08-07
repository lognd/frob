## Done report

Added `src/frob/tickets/_reconcile.py` -- `reconcile(root, *, apply=False,
remove_orphans=False)` + `ReconcileReport` -- reusing the T-0473 lease
registry (`frob.tickets._leases`, which already records each in-progress
ticket's worktree path/branch) to detect, and optionally heal, T-0476's
two anomaly classes structurally, with no coordinator polling of
output-file mtimes:

1. Stale hold: a ticket the checkout's OWN `tickets.md` shows
   `IN_PROGRESS` with no corresponding LIVE lease (`read_all_leases`
   already drops any lease whose recorded worktree no longer exists on
   disk, T-0473's own liveness guard -- "no live lease" covers both
   "never had one" and "had one, worktree died"). Healed by
   `transition(..., QUEUED)` -- the same legal state-machine edge `frob
   ticket requeue` (T-0472) uses -- which releases any lingering lease as
   a side effect of `transition` itself (T-0473's own sync).
2. Orphan worktree: a real, live `git worktree` (`git worktree list
   --porcelain`, excluding the main checkout) with no lease naming it at
   all.

CLI: `frob ticket reconcile [--apply] [--remove-orphans]`. No flags is a
pure dry-run report. `--apply` requeues stale holds (cheap, reversible)
and reports orphan worktrees but does NOT delete them. `--remove-orphans`
(requires `--apply`) additionally `git worktree remove --force`s them --
gated as its own separate opt-in since deleting a worktree is a strictly
more destructive action than requeuing a ticket.

DESIGN DEVIATION from the ticket body's literal "auto-clean via tiered
frob clean": `frob.clean`'s tiers (`scan`/`clean` in `src/frob/clean/`)
operate on build/cache ARTIFACTS (`__pycache__`, `dist/`, coverage files,
...) via allowlisted glob patterns, not on live git worktrees -- there is
no tier concept for "a linked worktree checkout" to plug into, and
reusing `frob.clean`'s removal machinery for a `git worktree remove` would
have meant either bolting an unrelated concern onto `frob.clean` or
faking a `CleanTier` that doesn't fit its allowlist-of-patterns model.
Orphan-worktree removal is instead its own direct `git worktree remove`
call in `_reconcile.py`, gated behind `--remove-orphans` for safety. This
is disclosed rather than silently narrowed.

Exports: `reconcile`, `ReconcileReport` added to `frob.tickets.__all__`.
Docs: new `## frob ticket reconcile (T-0476)` section in
`docs/modules/tickets.md`, right after the T-0473 lease-side-channel
section it completes.

Tests (real `git worktree add`/`git worktree remove` fixtures, no mocks,
matching `tests/test_ticket_leases_cross_worktree.py`'s style) in new
`tests/test_ticket_reconcile.py`: dry-run report vs `--apply` requeue +
lease release for a stale hold; a live in-progress ticket with a real
lease is correctly left untouched; an orphan worktree is flagged but not
removed under `--apply` alone, and IS removed under `--apply
--remove-orphans`; a worktree holding a live lease is never treated as an
orphan. Plus a CLI dispatch smoke test (`TestTicketReconcileCli` in
`tests/unit/test_app_runners_batch7.py`) for the trivial no-anomalies/
load-error paths -- the real anomaly-detection logic is exercised end to
end by the library-level tests, not re-mocked at the CLI layer.

Version bumped 0.38.0 -> 0.39.0 (REL001, minor: new public
`frob.tickets._reconcile` API) with matching CHANGELOG.md entries for
both 0.38.0 (T-0473, which had been missing one) and 0.39.0 (T-0476);
`.frob-release.json`/`uv.lock` restamped.

CAVEAT (declared-scope collision, not a code defect -- same class as
T-0474's): `mutate_scope` refused to add `src/frob/app/config.py` and
`src/frob/app/ticket_runner.py` to this ticket's formal scope; T-0419 (an
unrelated, still in-progress ticket elsewhere) holds an over-broad lease
on `src/frob/app/` that necessarily overlaps any file under it. Both
files already carry pre-existing, unrelated `frob:waive SCOPE001`
directives (T-0319/T-0323), so `frob check` reports 0 new errors for
them; only T-0476's own `scope:` field omits them.

All 8 evidence tests pass; full run of test_ticket_reconcile.py (6) +
test_app_runners_batch7.py (108, including the new
TestTicketReconcileCli pair) is green together. `frob check --ticket
T-0476` reports exactly 1 error, `REG003` on `docs/design/registry/
pii.yaml` -- pre-existing, unrelated to any file this ticket touches
(traced to T-0351, landed by another team's PII work before this session
started).

### Changed
```
 docs/modules/tickets.md                       |  15 ++++
 src/frob/__main__.py                          |  10 ++-
 src/frob/app/config.py                        |   5 ++
 src/frob/app/ticket_runner.py                 |  66 +++++++++++++-
 tests/system/test_cli_ticket_worktree_root.py |   4 +-
 tests/test_prework_parity.py                  |   5 +-
 tests/unit/test_app_runners_batch7.py         |  96 +++++++++++++++++++-
 tickets.md                                    | 125 +++++++++++++++++++++++++-
 8 files changed, 316 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_dry_run_reports_but_does_not_requeue` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_apply_requeues_stale_hold_and_releases_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_live_in_progress_ticket_with_lease_is_untouched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree::test_live_worktree_with_no_lease_is_flagged_not_removed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree::test_apply_and_remove_orphans_actually_removes_it` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree::test_worktree_holding_a_live_lease_is_not_orphan` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketReconcileCli::test_no_anomalies_logs_clean_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketReconcileCli::test_load_error_exits_1` (pytest node id, verified passing when recorded)
