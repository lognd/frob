---
id: T-2986
title: Archive move breaks COV004 attachment path resolution repo-wide (tickets/archive/<id>
  vs recorded tickets/<id> path)
state: in-progress
kind: bug
origin: agent
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets
- src/frob/gates/__init__.py
- tests/test_ticket_land.py
- tickets/archive/T-2195/**
- tickets/archive/T-2197/**
- tickets/archive/T-2244/**
- tickets/archive/T-2328/**
- tickets/archive/T-2350/**
- tickets/archive/T-2543/**
- docs/design/ledger-v2.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2195/**
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2197/**
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2244/**
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2328/**
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2350/**
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2543/**
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/design/ledger-v2.md
  reason: 'COV004 fix requires: the regression test (tests/test_ticket_land.py),

    repairing the 6 archived tickets whose attachments[].path was stale

    (tickets/archive/T-2195, T-2197, T-2244, T-2328, T-2350, T-2543), and

    documenting the one narrow content-rewrite exception in

    docs/design/ledger-v2.md''s existing "Archive as git mv" section (AFFECT001

    doc-anchor closure for the touched TestArchiveV2 class).

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001 fix: declare fs.read/fs.write for src/frob/tickets/_archive.py''s
    new direct file I/O in _rewrite_moved_attachment_paths'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 ratchet bump for _archive.py's newly declared fs.read/fs.write
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_ticket_land.py::TestArchiveV2::test_archived_ticket_attachment_still_resolves_for_cov004
designated_repro_test: null
acceptance:
- text: Given a done ticket with a recorded attachment (path + sha256) is archived
    via `frob ticket archive`, when `frob check --only docblocks` or `--only coverage`
    (COV004) runs afterward, then no COV004 violation fires for that ticket's attachment.
  evidence:
  - tests/test_ticket_land.py::TestArchiveV2::test_archived_ticket_attachment_still_resolves_for_cov004
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Root cause investigation for T-2893 (post-land sweep regression, COV004
findings on 10 attachment paths under archived tickets T-2195/T-2197/
T-2244/T-2328/T-2350/T-2543).

`_cov004` (src/frob/gates/__init__.py) resolves every attachment path as
a fixed `Path("tickets") / attachment.path`. `frob ticket archive`
(chore(tickets): archive 886 ticket(s), commit 8d131b53a, landed
2026-08-22 09:43:31 -0400) moves a done ticket's whole directory from
`tickets/<id>/` to `tickets/archive/<id>/` but does NOT rewrite the
`attachments[].path` field recorded in that ticket's own frontmatter --
the field still reads `T-2195/attachments/...` (relative to `tickets/`),
so after archival COV004 looks for the file at
`tickets/T-2195/attachments/...`, which no longer exists (it is now at
`tickets/archive/T-2195/attachments/...`), and fires "sha mismatch or
missing" on every archived ticket that ever had an attachment.

This is repo-wide and systemic, not specific to any one land: every
already-archived ticket with an attachment is affected today (confirmed
for T-2195, T-2197, T-2244, T-2328, T-2350, T-2543 while investigating
T-2893), and every future archive of a ticket with an attachment will
reproduce it again.

Fix belongs in one of:
  - `frob ticket archive` (src/frob/tickets, the archive command): rewrite
    each moved ticket's `attachments[].path` field to be relative to
    `tickets/` post-move (i.e. prefix with `archive/`), OR
  - `_cov004` / `_cov004_one` (src/frob/gates/__init__.py): resolve a
    missing `tickets/<path>` by also trying `tickets/archive/<path>`
    before concluding "missing".

Either fix should include a regression test that archives a done ticket
with an attachment and asserts COV004 stays clean afterward.

Measured while triaging T-2893 (2026-08-26): the blamed commit for
T-2893 (cab0f9fb, 2026-08-22 06:37:42) PREDATES the archive commit
(8d131b53a, 2026-08-22 09:43:31) that actually broke these attachment
paths -- the sweep's attribution to "an unattributed source (sweep
spawned by T-2875)" at cab0f9fb is not the real cause; the archive
command run afterward is.