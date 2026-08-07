---
id: T-0854
title: 'close/land preflight: block closing a ticket that registry dispositions or
  waivers still cite as their live tracker'
state: done
kind: feature
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- tests/test_tickets_live_tracker.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: New tests are needed for live_tracker_citations (git-grep-shaped scan) and
    its close/land preflight wiring; adding a new tests/test_tickets_live_tracker.py
    file and a TestLiveTrackerPrecheck class to tests/test_ticket_land.py (the existing
    TestMutationEvidencePrecheck precedent file for land-time preflight unit tests).
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_land.py
  reason: New tests are needed for live_tracker_citations (git-grep-shaped scan) and
    its close/land preflight wiring; adding a new tests/test_tickets_live_tracker.py
    file and a TestLiveTrackerPrecheck class to tests/test_ticket_land.py (the existing
    TestMutationEvidencePrecheck precedent file for land-time preflight unit tests).
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_deferred_disposition
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_tracked_by_disposition
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_ignores_duplicate_of_disposition
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_comment_waiver_ticket_attribute
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_strata_waiver_ticket_clause
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_unrelated_ticket_id_not_matched
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_own_scope_citation_excluded
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_citation_outside_own_scope_still_flagged
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_draft_id_always_clear
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_bare_cli_invocation_not_matched
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_non_git_root_degrades_to_no_citations
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_empty_repo_has_no_citations
- tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation::test_close_refused_when_registry_cites_this_ticket
- tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation::test_close_allowed_when_no_citation
- tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck::test_citations_found_blocks
- tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck::test_no_citations_is_ok
- tests/test_ticket_land.py::TestDraftFinalizeRewritesRegistryYamlRefs::test_registry_yaml_deferred_ref_rewritten_to_final_id
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_repointed_citation_no_longer_matches
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_unresolvable_base_ref_fails_closed
designated_repro_test: null
threat: null
component: null
---
The T-0605 incident class: landing/closing T-0605 instantly turned 41 patterns.yaml rows with disposition deferred:T-0605 into main-wide REG003 errors -- discovered only on the NEXT check, after the close was final. WAIVE006 already models the same hazard for waiver ticket= attributes but nothing checks it AT CLOSE TIME, and registry deferred:/tracked-by dispositions are not checked at all. Add a close/land preflight (same family as the T-0763 acceptance preflight): grep registry yamls for deferred:<id> and waiver bindings for ticket=<id>; a nonzero hit refuses the close with the row list and the remedy (file successor, re-point rows in the same change). Coordinator recipe exists in memory; this makes it mechanical.