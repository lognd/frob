---
id: T-2356
title: 'Ledger v2 cutover: delete tickets.md/tickets-archive.md and the monofile code
  path once the v2 tree round-trips'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
blocked_by:
- T-2355
parent: T-2346
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_merge_zones.py
- .gitattributes
- tickets.md
- tickets-archive.md
- src/frob/gates/_tickets_gate.py
- tests/test_ticket_land_merge.py
- tests/test_tickets_migration.py
- docs/modules/tickets-data-storage.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets.md
  reason: deleting the monofiles + their code path per design section 7 step 2, plus
    checking/extending LEDGERV1001
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tickets-archive.md
  reason: deleting the monofiles + their code path per design section 7 step 2, plus
    checking/extending LEDGERV1001
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: deleting the monofiles + their code path per design section 7 step 2, plus
    checking/extending LEDGERV1001
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_ticket_land_merge.py
  reason: deleting the monofiles + their code path per design section 7 step 2, plus
    checking/extending LEDGERV1001
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_tickets_migration.py
  reason: deleting the monofiles + their code path per design section 7 step 2, plus
    checking/extending LEDGERV1001
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'doc updates for the cutover: monofile section retirement'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets.md
  reason: 'doc updates for the cutover: monofile section retirement'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_is_silent
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_warns_before_sunset
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_monofile_mode_errors_past_sunset
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_no_ledger_content_at_all_is_silent
designated_repro_test: tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e2ed60480f76189b19157b99c6357a8d563068e7
---
Child 2 of 2 (see the paired migration ticket for the golden round-trip
test + migrating the 108 tickets-only-in-tickets.md; this one is blocked
on that one).

Per docs/design/ledger-v2.md section 7 step 2/5: once the v2 tree
round-trips cleanly (verified by the paired ticket's golden test, run
against THIS repo's real tickets.md/tickets-archive.md content, not just
the fixture), delete `tickets.md` and `tickets-archive.md` in a SEPARATE
commit from the migration -- the two-commit sequence the design
specifies so the cutover stays `git revert`-able.

Also per section 4 (Cutover, T-1553 landed): the monofile-mode code path
(`_render_ledger`, `splice_ledger`, `_land_merge.py`,
`_land_merge_zones.py`) and `.gitattributes`' merge-driver line are
explicitly flagged in that same design doc as "NOT yet deleted... remains
a separate follow-up ticket" -- fold that removal into this ticket rather
than filing a third, since it is the natural last step once no monofile
exists to merge/render.

LEDGERV1001 (`frob.gates._tickets_gate`, already shipped) currently WARNs
on a monofile-MODE repo (`_store_mode(root) == "single"`) -- confirm
whether it also needs to positively assert tickets.md/tickets-archive.md
are ABSENT post-cutover (a repo in "v2" store-mode that still happens to
have a stray tickets.md sitting around, unread but not deleted, would
currently pass silently); if so, extend it rather than adding a fourth
rule id for the same concern.

Positive controls: (1) a state change made via the CLI post-cutover is
visible through the ONE remaining representation (`tickets/<ID>/
ticket.md`) -- there is no second copy left to disagree; (2) `frob
ticket doable`/`show`/`board`/every other read path that used to fall
back to tickets.md for a pre-migration id still resolves it (via its now-
real per-ticket file from the paired migration ticket); (3) a repo that
still has BOTH a v2 tree and a monofile is flagged (whatever mechanism
you extend/add for it), not silently accepted as a permanent, indefinite
compatibility window.