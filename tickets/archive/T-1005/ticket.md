---
id: T-1005
title: 'frob ticket reverify: re-run close verification on a done ticket without state
  transition'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: T-0999
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- tests/**
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: reverify's docs live in docs/modules/tickets.md (new reverify section +
    public-api anchors); the file was hand-edited as part of this ticket's own scope,
    not silently forgotten
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_recovers_narrative_before_changed_marker
- tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_none_when_no_done_report_section
- tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_none_when_no_changed_marker_to_anchor_against
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_fails_loudly_on_now_failing_evidence
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_refuses_non_done_ticket
- tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged
- tests/test_ticket_reverify.py::TestReverifyCli::test_surfaces_now_failing_evidence_loudly
- tests/test_ticket_reverify.py::TestReverifyCli::test_refuses_non_done_ticket
designated_repro_test: null
acceptance:
- text: given a done ticket with newly-bound evidence, when frob ticket reverify runs,
    then the full close verification executes and the refreshed recap reflects the
    new evidence, with ticket state unchanged
  evidence:
  - tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_recovers_narrative_before_changed_marker
  - tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_none_when_no_done_report_section
  - tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_none_when_no_changed_marker_to_anchor_against
  - tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket
  - tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_fails_loudly_on_now_failing_evidence
  - tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_refuses_non_done_ticket
  - tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged
  - tests/test_ticket_reverify.py::TestReverifyCli::test_surfaces_now_failing_evidence_loudly
  - tests/test_ticket_reverify.py::TestReverifyCli::test_refuses_non_done_ticket
threat: null
component: null
---
Churn item 6 (~5 occurrences): after a post-close send-back (TEST016 strengthening), scope/evidence/done-report apply to a done ticket but nothing can re-run close verification (close refuses done->done; start/sweep refuse on done), so lands proceed on recap trust. Add frob ticket reverify <id>: runs the full close-time verification suite (evidence re-run, mutation evidence, covers-scope, claims capture) against a done ticket, updating the recap, with no state transition.