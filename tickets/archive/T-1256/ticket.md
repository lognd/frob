---
id: T-1256
title: 'ledger v2: archive via git mv, no content rewrite'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-1254
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_archive.py
- src/frob/tickets/_store.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: archive_v2/v2_archive_dir frob:doc edges point into these design/module
    docs; SCOPE002 requires them in the declared scope alongside the code they annotate
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/ledger-v2.md
  reason: archive_v2/v2_archive_dir frob:doc edges point into these design/module
    docs; SCOPE002 requires them in the declared scope alongside the code they annotate
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: archive_v2/v2_archive_dir frob:doc edges point into these design/module
    docs; SCOPE002 requires them in the declared scope alongside the code they annotate
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/ledger-v2.md
  reason: archive_v2/v2_archive_dir frob:doc edges point into these design/module
    docs; SCOPE002 requires them in the declared scope alongside the code they annotate
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_land.py::TestArchiveV2::test_archive_moves_directory_via_git_mv_no_content_rewrite
- tests/test_ticket_land.py::TestArchiveV2::test_archive_v2_regression_two_sided_divergence_no_clobber
- tests/test_ticket_land.py::TestArchiveV2::test_archived_v2_ticket_still_resolves_as_blocker
- tests/test_ticket_land.py::TestArchiveV2::test_first_ever_archive_uses_real_git_mv_not_rename_fallback
designated_repro_test: null
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 4.3) needs archive to

    become a plain `git mv tickets/T-#### tickets/archive/T-####` per ticket,

    with zero content rewrite -- eliminating the T-0959 archive-clobber

    failure mode structurally rather than guarding it. Blocked by the

    store-backend ticket.'
  evidence:
  - tests/test_ticket_land.py::TestArchiveV2::test_archive_moves_directory_via_git_mv_no_content_rewrite
  - tests/test_ticket_land.py::TestArchiveV2::test_first_ever_archive_uses_real_git_mv_not_rename_fallback
  - tests/test_ticket_land.py::TestArchiveV2::test_archive_v2_regression_two_sided_divergence_no_clobber
- text: 'GIVEN a v2-mode ticket reaching state done or dropped

    WHEN `frob ticket archive` runs

    THEN its directory is `git mv`-ed to `tickets/archive/T-####/` with no

    byte of `ticket.md`/`done-report.md` content rewritten (diff shows a pure

    rename, verified via `git diff --stat` showing 0 insertions/deletions for

    the moved files).'
  evidence:
  - tests/test_ticket_land.py::TestArchiveV2::test_archive_moves_directory_via_git_mv_no_content_rewrite
- text: 'GIVEN a v2-mode repo where one worktree''s archive tree predates another

    branch''s newer archive sweep (the T-0959 shape)

    WHEN both are merged

    THEN there is no clobber possible -- each archived ticket is a disjoint

    git path, so git''s own merge/rename detection handles the union with no

    custom splice code, verified by a regression test reproducing the T-0959

    incident''s two-sided-divergence shape against the v2 archive path and

    asserting no block is lost.'
  evidence:
  - tests/test_ticket_land.py::TestArchiveV2::test_archive_v2_regression_two_sided_divergence_no_clobber
- text: 'GIVEN `blocked_by`/`parent` references into an archived v2 ticket from an

    active ticket

    WHEN the referencing ticket is loaded

    THEN the archived ticket still resolves (load path checks both

    `tickets/*/ticket.md` and `tickets/archive/*/ticket.md`, mirroring

    today''s `load_all` reading both tickets.md and tickets-archive.md).'
  evidence:
  - tests/test_ticket_land.py::TestArchiveV2::test_archived_v2_ticket_still_resolves_as_blocker
threat: null
component: null
---
Ledger v2 design (docs/design/ledger-v2.md section 4.3) needs archive to
become a plain `git mv tickets/T-#### tickets/archive/T-####` per ticket,
with zero content rewrite -- eliminating the T-0959 archive-clobber
failure mode structurally rather than guarding it. Blocked by the
store-backend ticket.

GIVEN a v2-mode ticket reaching state done or dropped
WHEN `frob ticket archive` runs
THEN its directory is `git mv`-ed to `tickets/archive/T-####/` with no
byte of `ticket.md`/`done-report.md` content rewritten (diff shows a pure
rename, verified via `git diff --stat` showing 0 insertions/deletions for
the moved files).

GIVEN a v2-mode repo where one worktree's archive tree predates another
branch's newer archive sweep (the T-0959 shape)
WHEN both are merged
THEN there is no clobber possible -- each archived ticket is a disjoint
git path, so git's own merge/rename detection handles the union with no
custom splice code, verified by a regression test reproducing the T-0959
incident's two-sided-divergence shape against the v2 archive path and
asserting no block is lost.

GIVEN `blocked_by`/`parent` references into an archived v2 ticket from an
active ticket
WHEN the referencing ticket is loaded
THEN the archived ticket still resolves (load path checks both
`tickets/*/ticket.md` and `tickets/archive/*/ticket.md`, mirroring
today's `load_all` reading both tickets.md and tickets-archive.md).