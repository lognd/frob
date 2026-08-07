---
id: T-1152
title: 'arch: extract tickets/__init__.py evidence/transition + done-report/review/drop/attach
  families + split _land.py -- T-1151 residue'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
- tests/test_tickets_cmd_evidence.py
- tests/test_tickets_tiers.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_cmd_evidence.py
  reason: T-1152's own plan requires re-pointing frob:tests directives in any tests/*.py
    file referencing a moved evidence-family symbol, plus fixing the design/frob.strata
    SELFAUDIT001 interface= gap the split surfaced
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_tiers.py
  reason: T-1152's own plan requires re-pointing frob:tests directives in any tests/*.py
    file referencing a moved evidence-family symbol, plus fixing the design/frob.strata
    SELFAUDIT001 interface= gap the split surfaced
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: T-1152's own plan requires re-pointing frob:tests directives in any tests/*.py
    file referencing a moved evidence-family symbol, plus fixing the design/frob.strata
    SELFAUDIT001 interface= gap the split surfaced
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify::test_reverify_true_when_command_still_reproduces
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_permissive_when_evidence_reverified_none
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_rejects_when_evidence_reverified_false
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_allows_when_mutation_evidence_true
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_permissive_when_mutation_evidence_none
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_rejects_when_mutation_evidence_false
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_fails_loudly_on_now_failing_evidence
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_refuses_non_done_ticket
- tests/test_tickets.py::TestEvidence::test_resolvable_ids_appended
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
- tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_appends_and_round_trips
- tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_normalizes_dot_form_before_resolving_and_storing
- tests/test_tickets.py::TestStateMachine::test_legal_transitions
- tests/test_tickets.py::TestStateMachine::test_transition_queued_to_planned_unit
- tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_ticket_not_found_propagates_load_error
- tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_write_failure_propagates
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_rejected
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_docs_kind_closes
- tests/test_tickets_cmd_evidence.py::TestRunCmdEvidenceLaunchFailure::test_oserror_on_launch_is_evidence_cmd_failed
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_allowed_once_descendant_done
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_refused_with_open_descendant
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_plain_ticket_close_unaffected_by_guard
designated_repro_test: null
threat: null
component: null
---
T-1151 extracted ONE family (field setters/sprint: set_priority/set_kind/
set_tier/set_sprint/set_component, sprint_view/sprint_velocity,
ticket_flow) into src/frob/tickets/_setters.py, following T-1103/T-1123's
per-family extraction pattern. tickets/__init__.py: 2740 -> ~2065 lines
(carved further, still likely above the <2000 acceptance target from
T-1108's own scope note -- verify exact line count at pickup).

Remaining families (per T-1151's own body, none touched by this pass):
- evidence/transition (transition, add_evidence, the _done_transition_*
  guard family) -- BEWARE the load-time circular import T-1103's Done
  report flagged for this exact family (new_ticket/finalize_draft already
  late-import from the package to work around it)
- done-report/review/drop/attach (brief_ticket, mutate_labels,
  record_review, attach, drop helpers, compose_done_report/
  set_done_report)

_land.py (4762 lines) still untouched across T-1108/T-1123/T-1151 --
still needs its own split (preflight/splice/verify/sweep families per
T-1108's original plan) before LARGE001 stops flagging it.

Follow the same pattern each time: one cohesive family per dispatch,
private module re-exported from __init__ via explicit imports (never
`import *`), zero caller-visible behavior change, existing tests as the
safety net, carry frob:ticket/frob:doc/frob:tests directives verbatim,
repoint docs/modules/tickets.md's frob:describes anchors and any
tests/*.py frob:tests directives at the new module path, add frob:ticket
edges to any test class/method a directive-repoint touches (COV002),
carry an INV006 split-module waiver per 0abc4e3a's precedent if the
moved prose trips it, watch for tests that monkeypatch a moved function
via the PACKAGE attribute (tickets_mod.<name>) -- those need a late
`from frob.tickets import <name>` inside the moved function body instead
of a module-top-level binding.