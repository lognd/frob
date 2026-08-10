---
id: T-1711
title: consider relocating _write_ticket_unchecked out of src/frob/tickets/_store.py
  into a test-only helper module
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_store.py
- tests/unit/test_ticket_store.py
- tests/test_ticket_land.py
- tests/_write_unchecked.py
- docs/modules/tickets.md
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'T-1711 investigated relocating _write_ticket_unchecked into a tests/-tree

    helper (per the T-1592 permanent="true" precedent) and this is the right

    outcome: it needs a small shared module both current test-fixture callers

    (tests/unit/test_ticket_store.py, tests/test_ticket_land.py) can import,

    plus updates to those two call sites and _store.py itself to drop the

    symbol and its WIRE001/follow_up waiver.

    '
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-1711 investigated relocating _write_ticket_unchecked into a tests/-tree

    helper (per the T-1592 permanent="true" precedent) and this is the right

    outcome: it needs a small shared module both current test-fixture callers

    (tests/unit/test_ticket_store.py, tests/test_ticket_land.py) can import,

    plus updates to those two call sites and _store.py itself to drop the

    symbol and its WIRE001/follow_up waiver.

    '
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/_write_unchecked.py
  reason: 'T-1711 investigated relocating _write_ticket_unchecked into a tests/-tree

    helper (per the T-1592 permanent="true" precedent) and this is the right

    outcome: it needs a small shared module both current test-fixture callers

    (tests/unit/test_ticket_store.py, tests/test_ticket_land.py) can import,

    plus updates to those two call sites and _store.py itself to drop the

    symbol and its WIRE001/follow_up waiver.

    '
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/tickets.md
  reason: 'docs/modules/tickets.md''s own prose names _write_ticket_unchecked''s module

    path (frob.tickets._store) directly; T-1711''s relocation to tests/ makes

    that doc line stale and AFFECT001-flagged the moment write_ticket''s own

    docstring changed to point at the new home -- narrow addition to update

    the one doc line, not a broad doc rewrite.

    '
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/ledger-v2.md
  reason: 'write_ticket''s docstring changed (module-path update to reflect T-1711''s

    relocation of _write_ticket_unchecked), which AFFECT001 flags against

    every doc in write_ticket''s affects()-closure, including ledger-v2.md''s

    own Content-loss guard section -- narrow addition to touch that one

    section with an accurate T-1711 note.

    '
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_ticket_store.py::TestWriteTicketUnchecked::test_skips_the_content_loss_guard_entirely
designated_repro_test: null
threat: null
component: null
---
frob:ticket T-1679

`_write_ticket_unchecked` (`frob.tickets._store`) is a deliberately
test-fixture-only escape hatch for the T-1637/T-1679 content-loss guard --
by design it has no production caller and never should. WIRE002 requires
a real `follow_up` ticket for its WIRE001 waiver since it lives in `src/`
(the `permanent="true"` test-tree exemption only applies to symbols under
`tests/`). This ticket is that accountable follow-up: investigate whether
`_write_ticket_unchecked` can be relocated into a `tests/`-tree helper
module instead (it needs access to the private `_write_ticket_impl` split
point in `_store.py`, so this may require exporting a narrow test-only
seam, or may simply not be worth the churn -- either outcome is a
legitimate close for this ticket).

## Done report

Relocated `_write_ticket_unchecked` from `src/frob/tickets/_store.py` into
a new `tests/_write_unchecked.py` module. Both existing test-fixture
callers (`tests/unit/test_ticket_store.py::TestWriteTicketUnchecked`,
`tests/test_ticket_land.py`'s splice_ledger/TICK005 fixtures) now import
it from there instead. The new module wraps `_store._write_ticket_impl`
(the private mode-dispatched write `write_ticket` performs after its own
content-loss guard passes), imported directly across the module boundary
-- the same pattern this repo already uses for private cross-module test
imports.

This was worth doing (not "not worth the churn"): now that the symbol
lives under `tests/`, its no-production-caller WIRE001 waiver qualifies
for the `permanent="true"` test-tree exemption (`frob.gates._wire.
_wire002_is_permanent_test_helper_waiver`, the T-1592 precedent) -- so
the waiver and its `follow_up="T-1711"` attribute were dropped entirely,
rather than needing a fresh placeholder ticket the moment this one
closes (the exact WIRE002 orphan-churn class T-1592 exists to end).

Updated `write_ticket`'s own docstring in `_store.py` (module-path
pointer) and its `docs/modules/tickets.md` / `docs/design/ledger-v2.md`
affects()-closure doc references to name the new location, closing the
AFFECT001 finding the docstring edit raised.

Evidence: tests/unit/test_ticket_store.py::TestWriteTicketUnchecked::test_skips_the_content_loss_guard_entirely
passes against the relocated primitive; the pre-existing
tests/test_ticket_land.py suites that use it via the new import
(TestSpliceOnlyTicket, TestSiblingDoneReportPreserved,
TestLand::test_sibling_evidence_rebind_carried_forward_end_to_end,
TestTick005LandRegressions) all still pass, confirming the relocation is
behavior-preserving.

### Changed
```
 tickets/T-1711/ticket.md | 89 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 88 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1183 warning(s), 733 waived
- error-findings: none (measured, zero errors)
