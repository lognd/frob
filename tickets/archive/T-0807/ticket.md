---
id: T-0807
title: 'check: auto-suppress land-owned REL001 bump-half in worktree/ticket context
  (reviews keep tripping on it)'
state: done
kind: ux
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/check_runner.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'Verification tests for T-0807''s context-derived REL001 suppression live
    in

    tests/test_gates.py (TestDebtGate, alongside the existing T-0731 bump tests

    they extend) -- adding this test home to scope so COV002 accounts for the

    new/changed test methods.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestDebtGate::test_release_gate_bump_fires_without_frob_agent
- tests/test_gates.py::TestDebtGate::test_release_gate_bump_suppressed_under_frob_agent
- tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket
- tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket
- tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease
- tests/test_gates.py::TestDebtGate::test_rel001_linked_worktree_detected
designated_repro_test: null
acceptance:
- text: GIVEN frob check --ticket T-X running in a worktree (or against a ticket with
    a live worktree lease) WHEN the public API changed THEN REL001's version-bump
    demand is reported as an informational note (land owns the bump) not an error;
    GIVEN a plain root-checkout check with no ticket context THEN REL001 errors as
    today
  evidence:
  - tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket
  - tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease
  - tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket
threat: null
component: null
---
Recurring friction (4+ review cycles this drive): REL001's bump-half fires as an error in worktree reviews/implementations because suppression is keyed on the FROB_AGENT env var, which reviewers and some dispatch shells never set -- every reviewer then REJECTs or hand-waives a violation that frob ticket land auto-clears seconds later (auto-bumps landed 0.97.0 through 0.105.0 this week). Derive the suppression from CONTEXT instead of env: if the check runs with --ticket and that ticket holds a worktree lease (or cwd is a linked worktree), the bump is land-owned by definition. Keep the API-diff REPORTING (reviewers should still see 'public API changed (minor)'), demote only the bump demand.