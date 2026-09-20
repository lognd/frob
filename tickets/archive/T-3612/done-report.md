## Done report

T-3612 -- narrow LandInProgress to the ledger-splice critical section for
tickets-dir writers

WHAT CHANGED

Before: `frob.tickets._leases.refuse_if_land_in_progress` (the single
choke point every ledger-writing verb -- new/drop/body/scope/fail/
evidence/done-report/accept/start/close/requeue/block, dispatched
through `_refuse_if_land_in_progress_for_dispatch` and reused directly
by `_setters.py`'s single-field setters, `_reconcile.py`'s apply guard,
`ticket_runner/_ledger_mirror.py`, `gates/_waive_audit_watermark.py`, and
`verify/_drain.py` -- consults before writing) refused for as long as a
`frob ticket land` process held `.frob/land.lock` (a non-blocking flock
probe, `_land_flock_probe`) OR a live `ticket land`-shaped process was
found by a T-1619 `/proc` belt-and-braces scan
(`_scan_for_live_land_process`). `land.lock` is held for a land's WHOLE
run -- precheck through gates through squash-commit, measured 4-45
minutes -- so every OTHER ledger-writing verb was refused for that
entire window, even though the only step that genuinely races a filing
verb's own write is the land's ledger SPLICE: each `write_ticket`/
`write_all`/`write_archive` call the land's finalize/merge steps make
already runs under its own short `ledger_lock` (`.frob/tickets.lock`)
span (T-0889), which is the IDENTICAL lock every filing verb's own write
already acquires.

After: `refuse_if_land_in_progress` probes `tickets.lock` directly
(`_ledger_splice_flock_probe`, `frob.tickets._leases.py`) instead of
`land.lock`. A land's slow phases (precheck, gates) no longer refuse
anything through this choke point at all; only the land's actual splice
does, for however long that specific write takes (measured target <2s
p95 per the ticket). `land()` itself is untouched -- it never went
through `refuse_if_land_in_progress` at all, serializing against a
second `land()` via its own `_land_lock` (a real blocking flock on
`land.lock`, `frob.tickets._land.py`) -- so "a second land still
refuses" holds exactly as before this ticket, unaffected.

WHY THE OLD PROCESS-SCAN BACKSTOP WAS DROPPED FROM THIS CHOKE POINT

`_scan_for_live_land_process` (the T-1619 `/proc` belt-and-braces scan,
covering the race window before a land has written its `land.lock`
holder JSON, and any fcntl-unavailable platform) is now IRRELEVANT to
`refuse_if_land_in_progress`'s new question ("is `tickets.lock` held
right now") -- a live land process that has not yet reached its splice
does not hold `tickets.lock`, so scanning for it would just reintroduce
the whole-duration refusal this ticket exists to remove. The function
itself is untouched and still backs `_land_in_progress_for_ticket`'s own,
separate lease-staleness use (T-2264) -- only this ONE choke point
stopped consulting it.

OBSERVABILITY

Every refusal still logs at WARNING (`_refuse_for_held_ledger_splice_
lock`), and now also logs a best-effort correlated `land.lock` holder
(pid/ticket_id) when one happens to be recorded, since `tickets.lock`
itself carries no holder metadata (a bare advisory flock, unlike
`land.lock`'s JSON marker) -- a correlation, not a proof (a non-land
ledger write can hold `tickets.lock` too), but the common case is a
land's splice and it gives an operator a pid to check. New: every write
ALLOWED during an in-progress land (i.e. `land.lock` held, `tickets.lock`
free -- exactly the window this ticket newly permits) is logged at INFO
with the land's holder pid/ticket_id, inside `refuse_if_land_in_
progress`'s own success path, so the narrowing is observable rather than
a silent behavior change.

SCOPE

Ticket scope started as src/frob/tickets/_leases.py,
src/frob/tickets/_land.py, tests/unit/test_land_in_progress_window.py.
Added tests/test_ticket_leases.py to scope mid-ticket (via `frob ticket
scope --add`, reason recorded on the ticket) once running the existing
suite showed 10 tests in TestRefuseIfLandInProgress/TestDispatchLandGuard/
TestCommitTicketLedgerChange asserting the exact OLD land.lock-based
contract this ticket deliberately changes -- they were not incidental
breakage, they were testing the behavior this ticket's own acceptance
criteria say must change, so leaving them red instead of updating them
would have been indistinguishable from a real regression to the next
person who ran the suite.

TESTS

New: tests/unit/test_land_in_progress_window.py (6 tests) -- two real
held-flock scenarios (a background thread genuinely holding the OS
flock, not a monkeypatched stand-in): land.lock held/tickets.lock free
allows the write (and logs the INFO line, asserted); tickets.lock held
refuses, naming the correlated land.lock holder; tickets.lock held with
NO land.lock at all still refuses (a non-land concurrent write); no lock
at all allows; tickets.lock released partway through the bounded wait
then succeeds (never a hang, never corruption); and a second `_land_lock`
acquire still times out while a first holds it (land-vs-land exclusivity,
proven untouched).

Updated in tests/test_ticket_leases.py (retargeted from land.lock to
tickets.lock, or flipped to match the new contract, each with a T-3612
directive and docstring explaining the retarget):
  - test_refuses_while_land_lock_held -> split into
    test_land_lock_held_alone_no_longer_refuses (now asserts Ok, the
    starvation window this ticket closes) and
    test_refuses_while_ledger_lock_held (the narrowed replacement,
    holds tickets.lock, still asserts the holder-name correlation).
  - test_allows_after_a_killed_lands_lock_is_os_released -> retargeted
    to hold/kill a subprocess against tickets.lock instead of land.lock.
  - test_waits_then_succeeds_once_the_lock_frees -> retargeted to
    tickets.lock.
  - test_wait_times_out_and_still_refuses_loudly -> retargeted to hold
    tickets.lock while writing land.lock's holder JSON separately
    (unheld) for the correlation-naming assertion.
  - test_wait_budget_counts_from_the_lands_own_start_not_this_calls_start
    -> retargeted: tickets.lock is the resource actually held (never
    released, forcing the timeout); land.lock's started_at metadata
    (written separately, unheld) still drives `_resolve_land_wait_
    budget`'s scaling, which this ticket left untouched.
  - test_belt_and_braces_process_scan_without_the_lock_file -> renamed
    test_belt_and_braces_process_scan_no_longer_used_here, flipped to
    assert Ok: a live land-shaped process alone (no lock held at all)
    must no longer refuse through this choke point.
  - test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger ->
    retargeted from holding `_land_lock` to holding `ledger_lock`
    (`tickets.lock`) directly -- holding only `_land_lock`, as before,
    no longer reproduces a real race under the narrowed contract, since
    a land's slow phase (all `_land_lock` alone represents) is exactly
    the window this ticket makes safe to file into.
  - TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_
    progress and test_refused_verb_never_writes_the_ticket_file_at_all
    -> both retargeted from land.lock/`_land_lock` to tickets.lock/
    `ledger_lock`.
  - TestCommitTicketLedgerChange::test_rollback_on_land_in_progress_
    leaves_root_clean -> retargeted to hold tickets.lock.
  Unaffected, verified still passing unchanged: test_allows_when_no_
  lock_file, test_stale_holder_body_naming_a_dead_pid_never_held_is_not_
  reported_in_progress, test_a_land_targeting_a_different_repo_does_not_
  block_this_one, test_a_land_does_not_block_on_its_own_descendant,
  test_read_only_verb_runs_while_land_in_progress,
  test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_
  dispatches, test_land_verb_itself_is_exempt.

Also ran clean (unchanged): tests/unit/test_land_lock_liveness.py,
tests/unit/verify/test_drain.py (T-2406's exclude_pid caller -- confirms
`_probe_land_once`'s accept-and-discard shape does not break it).

Full slice run together: tests/test_ticket_leases.py +
tests/unit/test_land_lock_liveness.py + tests/unit/verify/test_drain.py +
tests/unit/test_land_in_progress_window.py = 189 passed, 0 failed.

ruff check / ruff format --check: clean on every touched file.
ty check: All checks passed on src/frob/tickets/_leases.py,
src/frob/tickets/_land.py, tests/test_ticket_leases.py,
tests/unit/test_land_in_progress_window.py.

DUPLICATE-CONSTANT RESIDUE, FILED NOT FIXED

`_leases.TICKETS_LEDGER_LOCK_REL` is a second, independently-defined
`Path(".frob") / "tickets.lock"` literal -- `frob.tickets._store`'s
canonical `_LOCK_REL`/`_lock_path` are deliberately PRIVATE (T-0601: "no
consumer outside this module and its own test"), and `_store.py` was
outside T-3612's declared scope, so there was no way to import a shared
public symbol instead. This is exactly the "two independently-defined
copies that could silently drift apart" shape `_leases.py`'s own T-1619
comment already warns against for `LAND_LOCK_REL` (which _land.py
correctly imports rather than redefining). Filed a follow-up ticket
(see the coordinator's ticket-id note) to give `_store.py` one public
accessor and delete the duplicate; deferred only because it touches a
file outside this ticket's scope.

RESIDUAL RISK NOTED, NOT ADDRESSED (OUT OF SCOPE)

`refuse_if_land_in_progress` is also the guard every OTHER mutating verb
(not just new/drop/body/scope/fail/evidence/done-report/accept) goes
through at the dispatch layer (`_refuse_if_land_in_progress_for_dispatch`,
`frob/app/ticket_runner/__init__.py`, out of this ticket's scope) unless
listed in `_LAND_LOCK_EXEMPT_VERBS` (land/merge-driver/sweep-async) or
`_LAND_SAFE_READ_ONLY_VERBS`. That set includes `renumber`/`promote`,
which write across MANY files with no single ledger_lock-guarded commit
step (T-1615 deliberately excludes them from the uniform auto-commit).
This ticket's narrowing therefore also shortens the window those verbs
are refused during a land, and the ticket body itself does not analyze
whether their own multi-file write pattern is equally safe against a
land's splice the way a single ledger_lock-guarded filing-verb write is.
Not fixed here (ticket_runner/__init__.py is out of scope, and the
ticket's own acceptance criteria are scoped to the ledger-lock probe
itself); flagged for the coordinator to decide whether a follow-up
ticket should audit renumber/promote's interaction with a land's splice
specifically.

VERIFICATION COMMANDS RUN

ruff check <scoped files> -- clean (one auto-fixable import-order finding
in the new test file and in tests/test_ticket_leases.py, both fixed via
`ruff check --fix`).
ruff format --check <scoped files> -- clean, no reformatting needed.
ty check <scoped files> -- "All checks passed!".
PYTHONPATH=<worktree>/src <root venv python> -m pytest -q -p no:xdist
  tests/test_ticket_leases.py tests/unit/test_land_lock_liveness.py
  tests/unit/verify/test_drain.py tests/unit/test_land_in_progress_window.py
  -> 189 passed, 0 failed.

Did not run: `frob ticket done-report` (per coordinator instruction (b) --
this file substitutes for it) and the ticket-scoped `frob check` (per the
same instruction).

### Changed
```
 design/frob.strata                                 |   2 +-
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 src/frob/tickets/_land.py                          |  23 +-
 src/frob/tickets/_leases.py                        | 208 ++++++++++++++---
 tests/test_ticket_leases.py                        | 258 ++++++++++++++-------
 tests/unit/test_land_in_progress_window.py         | 227 ++++++++++++++++++
 tickets/T-3612/ticket.md                           | 115 ++++++++-
 7 files changed, 704 insertions(+), 135 deletions(-)
```

### Evidence
- `tests/unit/test_land_in_progress_window.py::TestLandInProgressWindowNarrowedToSplice::test_land_lock_held_but_tickets_lock_free_allows_the_write` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_in_progress_window.py::TestLandInProgressWindowNarrowedToSplice::test_tickets_lock_held_refuses_naming_the_correlated_land_holder` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_in_progress_window.py::TestSecondLandStillRefused::test_second_land_lock_acquire_times_out_while_the_first_holds_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
