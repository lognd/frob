---
id: T-1556
title: 'cli hygiene remainder: warning collapse, read-only check --ticket, close porcelain,
  cli-hygiene principles doc (T-1271 split)'
state: done
kind: ux
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/gates/_waive_lease.py
- docs/design/cli-hygiene.md
- src/frob/_cli_parsers/_ticket/_progress.py
- tests/unit/test_cli_hygiene_checklist_t1556.py
- tests/unit/test_close_failure_hint_t1556.py
- tests/unit/test_scope_closure_warning_collapse_t1556.py
- tests/test_tickets_leases.py
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive_lease.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-hygiene.md
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: renumber --help text warning is Principle 1's concrete anchor, cited by
    cli-hygiene.md's checklist
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_cli_hygiene_checklist_t1556.py
  reason: T-1556 own test files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_close_failure_hint_t1556.py
  reason: T-1556 own test files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_scope_closure_warning_collapse_t1556.py
  reason: T-1556 own test files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_tickets_leases.py
  reason: T-1556 own test files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/check_runner.py
  reason: criterion 2 (read-only check --ticket never requires a lease) needs the
    actual CLI wiring; ticket_lease_pin's mutating kwarg exists but nothing invoked
    it with mutating=False yet
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_no_warnings_logs_nothing
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_few_warnings_logged_individually
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_many_warnings_collapse_to_counted_summary
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_verbose_env_var_disables_collapse
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_read_only_invocation_skips_the_lease_check
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
- tests/unit/test_close_failure_hint_t1556.py::test_evidence_scope_unbound_names_evidence_and_scope_commands
- tests/unit/test_close_failure_hint_t1556.py::test_evidence_not_passing_names_evidence_command
- tests/unit/test_close_failure_hint_t1556.py::test_own_obligations_unclean_names_check_delta_command
- tests/unit/test_close_failure_hint_t1556.py::test_gate_claim_unverified_names_close_retry
- tests/unit/test_close_failure_hint_t1556.py::test_live_tracker_cited_names_successor_ticket_remedy
- tests/unit/test_close_failure_hint_t1556.py::test_new_gate_rule_unaccepted_names_accept_and_evidence_commands
- tests/unit/test_close_failure_hint_t1556.py::test_reverify_verb_is_threaded_through_new_cases
- tests/unit/test_close_failure_hint_t1556.py::test_unhandled_error_still_falls_back_to_generic_message
- tests/unit/test_cli_hygiene_checklist_t1556.py::TestRenumberPositionalContractDocumented::test_old_positional_help_names_the_whole_ledger_fallback
- tests/unit/test_cli_hygiene_checklist_t1556.py::TestRenumberPositionalContractDocumented::test_dry_run_help_states_its_default
designated_repro_test: null
acceptance:
- text: GIVEN a command emits repeated advisory warnings (scope-closure on ticket
    new can flood thousands of lines) THEN they collapse to a counted summary with
    a --verbose escape hatch -- signal is never drowned
  evidence:
  - tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_no_warnings_logs_nothing
  - tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_few_warnings_logged_individually
  - tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_many_warnings_collapse_to_counted_summary
  - tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_verbose_env_var_disables_collapse
- text: GIVEN a read-only invocation (check --ticket for review, show, brief) THEN
    it never requires a lease or mutates state -- reviewers repeatedly could not re-verify
    gate claims because check --ticket demands a lease
  evidence:
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_read_only_invocation_skips_the_lease_check
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
- text: GIVEN a multi-step workflow (close needs start, done-report, evidence, accepts)
    THEN each refusal names the exact next command AND a single porcelain verb exists
    that sequences the happy path; hidden optional arguments that change behavior
    (e.g. renumber's positional-only contract) are documented in --help with examples
  evidence:
  - tests/unit/test_close_failure_hint_t1556.py::test_evidence_scope_unbound_names_evidence_and_scope_commands
  - tests/unit/test_close_failure_hint_t1556.py::test_evidence_not_passing_names_evidence_command
  - tests/unit/test_close_failure_hint_t1556.py::test_own_obligations_unclean_names_check_delta_command
  - tests/unit/test_close_failure_hint_t1556.py::test_gate_claim_unverified_names_close_retry
  - tests/unit/test_close_failure_hint_t1556.py::test_live_tracker_cited_names_successor_ticket_remedy
  - tests/unit/test_close_failure_hint_t1556.py::test_new_gate_rule_unaccepted_names_accept_and_evidence_commands
  - tests/unit/test_close_failure_hint_t1556.py::test_reverify_verb_is_threaded_through_new_cases
  - tests/unit/test_close_failure_hint_t1556.py::test_unhandled_error_still_falls_back_to_generic_message
- text: GIVEN the audit lands THEN a short cli-hygiene principles doc exists in docs/design/
    and a checklist test (or gate rule) verifies new parsers against it (every flag
    help string states its default; no flag silently changes another flag's meaning)
  evidence:
  - tests/unit/test_cli_hygiene_checklist_t1556.py::TestRenumberPositionalContractDocumented::test_old_positional_help_names_the_whole_ledger_fallback
  - tests/unit/test_cli_hygiene_checklist_t1556.py::TestRenumberPositionalContractDocumented::test_dry_run_help_states_its_default
threat: null
component: null
anchor: false
anchor_reason: null
---
Split from T-1271: its dispatch delivered criterion 0 (enum-valued flag errors list every valid value inline) with bound evidence; these four criteria were not implemented in that worktree and were drafted there as T-1557, which cannot survive a land preview (land-splice draft-loss class). Filed as a real main-side ticket so T-1271 can land its delivered portion with an honest acceptance trail.