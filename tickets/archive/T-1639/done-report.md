## Done report

CrossTicketLeakage no longer blocks on a QUEUED/PLANNED/BLOCKED sibling (T-1639).

Confirmed the reported bug directly: `_find_leaked_tickets` (src/frob/tickets/_land.py)
skipped only `DONE`/`DROPPED` siblings -- "still open" meant every other
state, including QUEUED (a ticket nobody has started, zero commits, no
worktree, no lease). A freshly filed ticket with a generously broad scope
(this repo's own filing convention) reserved that scope against every
other land immediately.

Fix: a scope hit against a sibling is now only ever REFUSED
(`_report_leaked_tickets`/`Err(LandError.CrossTicketLeakage)`) when that
sibling is `IN_PROGRESS`. This reuses the exact line
`frob.tickets._leases` already draws for worktree leases -- a lease is
recorded ONLY when a ticket enters `IN_PROGRESS` (`transition`'s own
T-0473 mechanism), never for QUEUED/PLANNED/BLOCKED -- so "declared scope
is a claim" and "declared scope is an intention" already had a real,
existing state boundary in this codebase; CrossTicketLeakage was simply
not using it. A hit against a non-`IN_PROGRESS` sibling is still logged
(INFO, naming the ticket, its state, and the overlapping paths) so the
overlap is disclosed, not silently dropped -- it just no longer refuses.

T-1618's genuine purpose (a shared series worktree carrying a sibling's
COMMITTED work onto main) is unaffected: that shape always involves a
sibling that was actually started, so it is always `IN_PROGRESS` (or
already `DONE`/`DROPPED`, both already exempted before this change) by
the time it could leak anything on the branch. Verified this holds by
NOT touching `_leaked_hits_for_candidate`'s own T-1370/T-1390 exemption
logic at all -- only the state gate at the top of `_find_leaked_tickets`'s
loop changed.

Changed:
- src/frob/tickets/_land.py::_find_leaked_tickets -- state gate narrowed
  from "not DONE/DROPPED" to "IN_PROGRESS only refuses; otherwise log and
  continue"
- src/frob/tickets/_land.py::_check_cross_ticket_leakage -- docstring
  updated to describe the IN_PROGRESS-only refusal condition
- docs/modules/tickets.md -- new "Cross-ticket leakage only refuses on an
  IN_PROGRESS sibling (T-1639)" section, with frob:doc edges bound from
  both changed functions

Tests added (real git fixture repos, matching this test module's existing
style -- not mocks):
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_planned_sibling_scope_overlap_does_not_block

Verification:
- `uv run pytest tests/unit/test_land_cross_ticket_leakage.py` -- 8 passed
  (6 pre-existing regressions unaffected, 2 new)
- `uv run pytest tests/unit/test_scope_lease_deadlock.py` -- 5 passed
  (adjacent lease-deadlock suite unaffected)
- `uv run frob check --ticket T-1639` -- 0 errors other than the one
  land-absorbed SELFAUDIT001 (a testsuite interface-sync entry `frob
  ticket land` writes automatically via `frob sys sync-interface` before
  its own merge, per the playbook -- confirmed via `--land-parity` below,
  not left unaddressed)
- `uv run frob check --land-parity` -- clean, 0 unscoped errors (this IS
  the exact evaluation the land sweep runs, including its own
  sync-interface pass, so the SELFAUDIT001 above is confirmed resolved by
  land itself, not a real gap)

T-1639 and T-1645 share one root cause: frob treating a declaration made
BEFORE work identically to one made DURING work. I did not find a third
instance of this same confusion within this ticket's own scope
(src/frob/tickets/_land.py, src/frob/tickets/_land_git_ops.py,
docs/modules/tickets.md) -- the only other state-sensitive check I
touched incidentally, T-1370's same-worktree-lease exemption
(`_leaked_hits_for_candidate`), already keys off a REAL lease (which only
exists once IN_PROGRESS), so it was already correct on this axis and
needed no change.

### Changed
```
 docs/guides/install.md                 |  42 ++++++--
 docs/modules/app.md                    |   6 +-
 docs/modules/render.md                 |   5 +-
 src/frob/app/doctor_runner.py          |  26 +++++
 src/frob/doctor.py                     |  93 +++++++++++------
 src/frob/tickets/_land.py              |  70 ++++++++++++-
 tests/system/test_cli_doctor.py        |  59 +++++++++--
 tests/test_ticket_land.py              |  96 ++++++++++++++++++
 tests/unit/test_doctor_runner_t1276.py |  67 ++++++++++++-
 tickets-archive.md                     |   3 +-
 tickets.md                             | 177 ++++++++++++++++++++++++++++++++-
 11 files changed, 589 insertions(+), 55 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_planned_sibling_scope_overlap_does_not_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 711 warning(s), 851 waived
- error-findings: none (measured, zero errors)
