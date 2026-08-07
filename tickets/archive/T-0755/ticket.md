---
id: T-0755
title: 'adversarial evidence obligation: ticket tests must fail on a diff-scoped mutant
  (confirmatory-only tests flagged)'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: T-0417
tier: ticket
sprint: null
scope:
- src/frob/mutate/**
- src/frob/tickets/**
- src/frob/gates/**
- docs/modules/tickets.md
- tests/test_mutate.py
- tests/test_tickets_mutation_evidence.py
- tests/test_gates_mutation_evidence.py
- tests/test_ticket_land.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner.py
- docs/modules/mutate.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_mutate.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Test files for the T-0755 mutation-evidence obligation (new tests/test_tickets_mutation_evidence.py,
    tests/test_gates_mutation_evidence.py; edits to tests/test_mutate.py for the new
    max_mutants cap and tests/test_ticket_land.py for the land precheck) live under
    tests/, outside the src/**-only scope declared at filing time.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/__main__.py
  reason: 'Reviewer round-2 finding 4 requires a documented --skip-mutation-evidence
    escape hatch on `frob ticket land`. Wiring a new CLI flag structurally touches
    the three CLI-wiring files (dispatch table, AppConfig flag plumbing, runner),
    matching the existing CLI_WIRING_FILES precedent for feature-shaped work even
    though this ticket is kind=security.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/config.py
  reason: 'Reviewer round-2 finding 4 requires a documented --skip-mutation-evidence
    escape hatch on `frob ticket land`. Wiring a new CLI flag structurally touches
    the three CLI-wiring files (dispatch table, AppConfig flag plumbing, runner),
    matching the existing CLI_WIRING_FILES precedent for feature-shaped work even
    though this ticket is kind=security.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/ticket_runner.py
  reason: 'Reviewer round-2 finding 4 requires a documented --skip-mutation-evidence
    escape hatch on `frob ticket land`. Wiring a new CLI flag structurally touches
    the three CLI-wiring files (dispatch table, AppConfig flag plumbing, runner),
    matching the existing CLI_WIRING_FILES precedent for feature-shaped work even
    though this ticket is kind=security.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/mutate.md
  reason: Round-2 changes altered run_mutations' public signature (max_mutants, line_ranges)
    and added the MUTATION_RUN_ENV recursion-guard sentinel; docs/modules/mutate.md
    is that surface's doc home and updating it in the same change is the repo's document-as-you-go
    rule, same precedent as docs/modules/tickets.md already being in scope for the
    TEST016 section.
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_mutate.py::test_run_mutations_max_mutants_caps_points_explored
- tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds::test_filters_non_node_id_entries
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_filters_to_scope_and_python
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_empty_when_nothing_touched
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_no_test_evidence_is_ok_empty
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_exec_disabled_is_err
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_security_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_error_for_bug_kind
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_findings_no_violations
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_security_kind_error_finding_blocks
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_feature_kind_warn_finding_does_not_block
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_no_findings_is_ok
- tests/test_mutate.py::test_generate_mutants_line_ranges_filters_to_changed_lines
- tests/test_mutate.py::test_generate_mutants_line_ranges_no_match_is_empty
- tests/test_mutate.py::test_run_mutations_line_ranges_scopes_to_changed_lines
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_large_file_unmutable_changed_lines_is_skipped_not_flagged
- tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_skip_flag_bypasses_error_finding_but_still_logs
- tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_parses_to_true
- tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_omitted_defaults_false
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings
- tests/test_mutate.py::test_run_mutations_sets_mutation_run_sentinel_in_child_env
- tests/test_ticket_land.py::TestCloseSkipMutationEvidenceCliWiring::test_flag_parses_to_true
- tests/test_ticket_land.py::TestCloseSkipMutationEvidenceCliWiring::test_flag_omitted_defaults_false
- tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket::test_error_severity_finding_returns_false
- tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket::test_warn_only_severity_returns_true
- tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket::test_no_findings_returns_none
- tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket::test_unresolvable_branch_returns_none
- tests/test_ticket_land.py::TestCloseFailureHintMutationEvidence::test_confirmatory_only_hint_names_skip_flag_remedy
- tests/test_ticket_land.py::TestCloseFailureHintMutationEvidence::test_other_error_does_not_name_skip_flag_remedy
- tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass::test_skip_flag_bypasses_error_verdict
- tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass::test_no_skip_flag_refuses_on_error_verdict
designated_repro_test: null
acceptance:
- text: GIVEN a ticket whose recorded evidence tests all pass against a mutant of
    the changed logic WHEN close/land verifies THEN a confirmatory-only-test finding
    fires naming the tests; GIVEN at least one evidence test fails on the mutant THEN
    it passes
  evidence:
  - tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
  - tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged
  - tests/test_ticket_land.py::TestMutationEvidencePrecheck::test_security_kind_error_finding_blocks
threat: null
component: null
---
Root-cause analysis 2026-07-22: several rejects were correctness bugs whose own tests PASSED because they were confirmatory, not adversarial -- written to pass for the reason the implementer built the thing (T-0611, T-0571, T-0682, T-0574, T-0710). A confirmatory test that would pass on BOTH the pre-change and post-change code proves nothing. frob already has `frob mutate`. Add a diff-scoped obligation: for a ticket touching code with new/changed tests, run those tests against the PRE-change version of the changed symbols (or a targeted mutant of the new logic) and require at least ONE recorded evidence test to FAIL on the mutant -- proving the test actually distinguishes the change. A test that passes on the mutant is a confirmatory-only test = a TEST-family warning (ratchet to error via T-0569 pool for security/bug-kind tickets). This is mutation testing scoped to the ticket diff, wired into close/land as evidence-quality verification, reusing frob.mutate.