---
id: T-1574
title: tests/unit/test_ticket_store.py has 10 tests broken by T-1553's v1-to-v2 fresh-repo
  default flip (file not in T-1553's audited scope)
state: dropped
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
found while working T-1561: tests/unit/test_ticket_store.py was NOT in
T-1553's declared scope (test_tickets.py, test_ticket_land.py,
test_tickets_migration.py, test_tickets_collision.py,
test_tickets_velocity.py only) and was missed by that audit. 10 tests
fail against current main (confirmed via `pytest tests/unit/test_ticket_store.py
-q`, reproducible, unrelated to T-1541/T-1561's own changes):

TestStoreMode::test_fresh_repo_defaults_to_single (asserts the OLD
default directly -- needs updating to assert v2, or moving to a
dedicated "pinned v1" fixture if the v1 case still needs its own
coverage)
TestWriteTicket::test_marker_lookalike_body_line_refuses_write
TestArchiveLedger::test_write_then_load_archive_round_trips
TestLoadArchiveCache::test_reparses_when_archive_content_changes
TestLoadArchiveCache::test_skips_reparse_when_content_hash_unchanged
TestSetDoneReport::test_caller_never_touches_markdown
TestSetDoneReport::test_second_call_replaces_first_report
TestSetDoneReport::test_composes_and_writes_atomically
TestReplayEvidenceFromDoneReport::test_recovers_ids_when_structured_evidence_empty
TestReplayEvidenceFromDoneReport::test_transition_to_done_auto_replays_lost_evidence

Most fail because a bare tmp_path now defaults to v2 mode, and v2 mode
splits Done reports into their own done-report.md (never embedded in
ticket.body) -- the same root cause as T-1573 (filed
separately for tests/test_tickets_evidence_cli.py, a different file).
Fix: audit each test, pin v1/'single' mode explicitly (seed an empty
tickets.md, matching T-1553's own fix pattern) where the test is
genuinely about v1-specific behavior, or update the assertion to the
v2-appropriate location/expectation where it is not.

## Drop reason
- 2026-08-05: moot: coordinator fixed the 11 v1-assuming tests in this worktree before landing