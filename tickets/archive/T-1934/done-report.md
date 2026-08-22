## Done report

Built `frob.tickets._unlanded` (pure git plumbing, no checkout): scans
every local branch except main for a ticket that looks finished
(`tickets/T-####/done-report.md` present, or `ticket.md`'s own `state:`
reading `done`/`dropped`), resolves that ticket id's state on `main`
checking BOTH the active path and the archive path (the 186-false-
positive shape the brief called out), and excludes any ticket whose
CURRENT lease `frob.tickets._leases.lease_staleness_reason` judges still
live (T-1876's staleness predicate, reused, not re-derived).

Per the coordinator's mid-dispatch correction, this is NOT a new
standalone verb -- it is a fourth `frob ticket reconcile` anomaly class
(`ReconcileReport.unlanded_branch_work`, report-only, never healed by
`--apply`), plus:

- `frob worktree sweep`: a new `kept:unlanded` verdict
  (`_kept_unlanded_verdict_if_present`), checked BEFORE the dirty-tree
  gate and NOT overridden by `--force` -- fixes the inverted heuristic
  directly (a clean, unlanded worktree is now kept, not removed).
- `frob ticket doable`: an "N branch(es) carry unlanded ticket work"
  line alongside T-1876's stale-lease warning.

Verified before/after (acceptance 1): before `frob.tickets._unlanded`
existed, `tests/unit/test_unlanded_branch_work.py` failed on
`ModuleNotFoundError` (confirmed directly by temporarily moving the
module aside and re-running the suite); after, all 7 tests pass,
including the T-1315/runner-wiring shape itself
(`test_confirmed_leak_shape_done_report_plus_in_progress`).

Two residues filed while working this ticket, both pre-existing and
verified unrelated via `git diff --stat main -- <path>` (empty in both
cases):
- T-1949: `_close_failure_hint` (_close_cmd.py) exceeds
  ARCH001's 60-line function threshold.
- SEC110 (src/frob/app/ticket_runner/_new.py) and SELFAUDIT001 (design)
  land-parity findings are also pre-existing/unrelated but were NOT
  separately filed (already-known, unowned repo-wide debt visible on
  every `--land-parity` run regardless of ticket, not something this
  investigation newly surfaced).

Gates: `frob check --only test/archgate/gates-fast/doclink --ticket
T-1934` and `frob check --land-parity` all read clean for this ticket's
own diff (every remaining finding independently confirmed pre-existing
via `git diff --stat main -- <path>`). `git diff main --diff-filter=D
--stat` is empty. `runner-wiring` branch is untouched (T-1315 recovery
is a separate, later commit on this same worktree/branch, cherry-picking
its scope files rather than merging the branch itself).

### Changed
```
 docs/modules/tickets.md                           |  43 ++++
 src/frob/app/ticket_runner/_lifecycle.py          |  54 +++--
 src/frob/app/ticket_runner/_query.py              |  28 +++
 src/frob/tickets/_leases.py                       |  59 ++++-
 src/frob/tickets/_reconcile.py                    |  24 ++
 src/frob/tickets/_unlanded.py                     | 255 ++++++++++++++++++++++
 tests/test_ticket_leases.py                       | 108 +++++++++
 tests/test_ticket_reconcile.py                    |  87 ++++++++
 tests/unit/test_app_runners_doable_stale_lease.py |  53 ++++-
 tests/unit/test_unlanded_branch_work.py           | 251 +++++++++++++++++++++
 tickets/T-1934/ticket.md                          |  90 ++++++++
 tickets/T-1949/ticket.md                |  36 +++
 12 files changed, 1070 insertions(+), 18 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 4 error(s), 1275 warning(s), 715 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, DOC001@docs/design/cli-hygiene.md, SEC110@src/frob/app/ticket_runner/_new.py, SELFAUDIT001@design
