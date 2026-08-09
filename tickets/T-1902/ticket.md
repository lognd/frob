---
id: T-1902
title: T-1892's EvidenceCmdSilent refusal broke two existing tests whose fixtures
  use 'true' as the evidence command
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, on main after landing T-1892 (c8e50a3d878d). Two tests now FAIL:

  tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_applied_for_docs_ticket
  tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_archives_done_ticket

Both fail for the same reason, visible in the captured log:

  WARNING frob.tickets._evidence: evidence command 'true' exited 0 but captured stdout+stderr empty -- refused (T-1892)
  ERROR   frob.app.ticket_runner: EvidenceCmdSilent: evidence command exited 0 with empty stdout+stderr -- proves nothing

THE NEW BEHAVIOR IS CORRECT AND MUST NOT BE REVERTED. T-1892 deliberately refuses a silent zero-exit evidence command because its digest is the SHA-256 of the empty string and proves nothing. These two test fixtures happen to pass the literal command 'true' -- precisely the case T-1892 exists to reject. The tests are asserting the OLD, unsound contract.

FIX: update both fixtures to use a chatty zero-exit command (e.g. 'echo verified' or 'grep -c ...') so they exercise the accepted path, and -- more valuable -- add an assertion to at least one of them that a SILENT command is refused, so the two behaviors are locked together in the test that owns this fixture. Do not add an escape hatch or a bypass flag to make the old fixtures pass.

PROCESS LESSON worth recording alongside the fix. T-1892's implementer ran only its own new test file (tests/test_tickets_cmd_evidence.py, 28 passing) and a scoped 'frob check --ticket T-1892'. Neither reaches a caller in a DIFFERENT test file that depends on the changed contract. This is the same shape as the invalid-argument-type wave (T-1894/T-1896): agents verify their own diff and land green, and the breakage surfaces on main afterwards. A contract-tightening change specifically needs a reverse-dependency search for existing callers of the tightened API -- consider whether frob can compute and demand that automatically for a diff that makes a validation STRICTER.