---
id: T-1553
title: 'ledger v2: flip fresh-repo default to v2 (safe, test-fixture-audited)'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- tests/test_tickets.py
- tests/test_ticket_land.py
- tests/test_tickets_migration.py
- tests/test_tickets_collision.py
- tests/test_tickets_velocity.py
- docs/design/ledger-v2.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/ledger-v2.md
  reason: ticket's own plan item 4 requires recording the v1->v2 fresh-repo-default
    flip as landed in both design docs
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/tickets.md
  reason: ticket's own plan item 4 requires recording the v1->v2 fresh-repo-default
    flip as landed in both design docs
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_tickets.py::TestArchive::test_id_present_in_both_active_and_archive_collapses_not_refuses
- tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed
- tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
- tests/test_tickets.py::TestArchive::test_new_ticket_corrupt_archive_fails_loudly
- tests/test_tickets.py::TestSingleFileLedger::test_new_tickets_land_in_single_tickets_md
- tests/test_tickets.py::TestSingleFileLedger::test_write_ticket_never_touches_a_sibling_ticket_bytes
- tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v1_v2_parity_for_equivalent_history
designated_repro_test: null
threat: null
component: null
---
## Description

T-1491 investigated flipping `_store_mode`'s final fresh-repo default
from 'single' (v1) to 'v2' (design section 7 deliverable 4, final
cutover) and found the change itself safe in principle but the blast
radius across this repo's own test suite too large to land inside T-1491
without becoming a much bigger ticket than its own declared scope. Many
existing v1-path tests construct a fixture via a bare `tmp_path` with no
explicit `tickets.md` seed and rely on `_store_mode`'s current default to
implicitly choose v1/'single' semantics -- flipping the default alone
(measured directly against `tests/test_tickets.py`) breaks at least:
`TestArchive::test_new_ticket_corrupt_archive_fails_loudly`,
`TestArchive::test_id_present_in_both_active_and_archive_collapses_not_refuses`,
`TestSingleFileLedger::test_new_tickets_land_in_single_tickets_md`,
`TestArchive::test_blocked_by_archived_ticket_resolves_closed`,
`TestSingleFileLedger::test_write_ticket_never_touches_a_sibling_ticket_bytes`,
`TestArchive::test_new_ticket_id_continues_past_archived_max` -- and this
is only one test file; `tests/test_ticket_land.py`,
`tests/test_tickets_migration.py`, `tests/test_tickets_collision.py`,
`tests/test_tickets_velocity.py`, and any CLI/integration test that
constructs a fresh repo without seeding `tickets.md` first are likely
affected the same way, unmeasured here.

## Plan

1. Audit every v1-path test fixture across `tests/test_tickets*.py` and
   `tests/test_ticket_land.py` that currently relies on the implicit
   fresh-repo default; update each to seed an explicit `tickets.md` (even
   an empty `# Tickets\n\n` header) so it pins v1 mode deliberately
   instead of by accident of default.
2. Flip `_store_mode`'s final `return "single"` to `return "v2"`.
3. Re-run the full suite (coordinator step, `make coverage` /
   unscoped `frob check`) and fix any remaining fallout outside the
   audited files.
4. Update `docs/design/ledger-v2.md` / `docs/modules/tickets.md` to
   record the flip as landed, not merely designed.

## Acceptance

- [ ] GIVEN a fresh repo with no `tickets.md`/`tickets/*.md`/`tickets/T-####/`
      content at all WHEN any ticket-store operation runs THEN it chooses
      v2 mode, not v1.
- [ ] GIVEN the full existing test suite WHEN run against the flipped
      default THEN every previously-passing test still passes (v1-path
      tests updated to seed `tickets.md` explicitly, not broken by the
      flip).