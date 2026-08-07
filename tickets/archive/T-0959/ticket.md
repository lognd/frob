---
id: T-0959
title: land clobbers tickets-archive.md with the worktree's stale copy (62 archived
  blocks wiped by T-0703's land)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
designated_repro_test: null
acceptance:
- text: given a worktree whose tickets-archive.md predates an archive sweep on main,
    when its ticket lands, then every block in main's pre-land archive survives in
    the post-land archive
  evidence:
  - tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
threat: null
component: null
---
T-0703's land (a9486381) replaced main's tickets-archive.md wholesale with the worktree's pre-archive-sweep copy, deleting the 62 blocks a TICK003 sweep had archived -- every Done report citing them then fired TICK006 phantom-filing (19 errors), plus COV003 regressions. Recovery was git checkout of the pre-land archive (2ab3c386, verified strict superset). Root cause to find: the land path stages tickets-archive.md from the worktree without the merge/splice discipline tickets.md gets; T-0740's _check_ledger_id_integrity guards _splice_only_ticket for tickets.md but the archive file appears to ride along unguarded (T-0703's worktree archive was stale because the sweep happened on main after the worktree's warmup merge). Fix: land must treat tickets-archive.md like tickets.md -- merge/splice not overwrite -- plus an id-integrity assertion that no archived id present on main's archive disappears in the staged result. Regression test: worktree with stale archive + main with newer archived blocks -> land must preserve main's blocks.