## Done report

Fixed the T-1050 incident class on both sides: `frob ticket fail` now
releases the lease when the failed ticket was in-progress, and `frob
doctor` reports any ticket already stuck this way.

Write side: `frob ticket fail <id> --summary TEXT`
(frob.app.ticket_runner._close_cmd._fail) previously only ever appended a
Failure log entry via `record_failure` -- it never called `transition`,
so an IN_PROGRESS ticket stayed IN_PROGRESS forever after a fail-log,
holding its cross-worktree lease (`_sync_cross_worktree_lease` only
releases a lease on a `transition` call OUT of IN_PROGRESS). `_fail` now
requeues (IN_PROGRESS -> QUEUED, the same legal `_TRANSITIONS` edge `frob
ticket requeue` uses) whenever the ticket was IN_PROGRESS when
fail-logged -- a failed attempt is correctly a retry candidate, not a
permanently stuck ticket, and this is the one `transition` call that
actually releases the lease. A ticket that was NOT IN_PROGRESS when
fail-logged is left in its current state unchanged (matches pre-fix
behavior for that case; `record_failure` itself deliberately stays a pure
append with no transition, since some callers log a historical failure
retroactively on a ticket that isn't in-progress).

`drop_ticket` was already correct (transitions to DROPPED through the
normal state machine, releasing the lease the same way) -- confirmed by
reading it; `fail` was the only broken "retire path" the ticket body's
"any retire path" language referred to. No other lease-releasing verb
needed a change.

Read side: `frob.doctor.scan_stale_ticket_leases` reports any ticket
stuck IN_PROGRESS with no live lease (wired into
`DoctorReport.stale_ticket_leases` / `run_diagnosis`'s healthy verdict
and remediation, same class as the existing stale-mutate-journal check).
Deliberately reuses `frob.tickets._reconcile.reconcile(root,
apply=False)` -- the exact same dry-run detection `frob ticket
reconcile`/`frob ticket requeue <id>` already implement -- rather than
reimplementing lease-staleness logic a second time; `frob doctor` never
requeues anything itself, only reports and points at the fix (`frob
ticket requeue <id>` or `frob ticket reconcile --apply`).

Updated docs/modules/tickets.md (record_failure/_fail's new requeue note
in the public-api section) and docs/guides/install.md (new "Stale ticket
lease scan (T-1131)" section, matching the existing mutate-journal/
malformed-edge section style) in the same change.

Out of scope, not touched: the pre-existing SCOPE002 scope-closure debt
across the ticket family's broad scope globs (already tracked as
T-1145, filed from T-1125); the pre-existing TICK006 phantom and INV006
finding surfaced by `frob check --ticket T-1131` are unrelated to this
diff (confirmed by symbol/file -- neither touches anything this ticket's
scope covers).

Addendum: land's mutation-evidence gate (TEST016) found the original 6-id
evidence set confirmatory-only against scan_stale_ticket_leases's error
path (a surviving mutant negating `if result.is_err:`) -- added
test_scan_degrades_to_empty_on_a_malformed_ledger (a genuinely malformed
tickets.md forcing reconcile's real Err path) to kill it.

Addendum 2: the malformed-ledger test still left the same TEST016 mutant
(doctor.py:284's `apply=False` negated to `apply=True`) confirmatory-only
-- both the error path and the malformed-ledger path return the same
observable value regardless of `apply`. Strengthened
test_scan_flags_in_progress_ticket_with_no_lease to additionally assert
the ticket's ledger state is untouched after the scan (frob doctor is
read-only, apply=False is load-bearing) -- verified by hand that this
assertion fails under the apply=True mutant and passes against real code.

### Changed
```
 docs/guides/install.md                   |  34 ++++++++
 docs/modules/tickets.md                  |  13 +++
 src/frob/app/ticket_runner/_close_cmd.py |  40 +++++++++-
 src/frob/doctor.py                       |  64 ++++++++++++++-
 tests/system/test_cli_doctor.py          | 121 ++++++++++++++++++++++++++++
 tests/test_tickets.py                    |  59 ++++++++++++++
 tickets.md                               | 132 ++++++++++++++++++++++++++++++-
 7 files changed, 456 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_scan_flags_in_progress_ticket_with_no_lease` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_scan_ignores_live_leased_ticket` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_scan_degrades_to_empty_on_a_malformed_ledger` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
