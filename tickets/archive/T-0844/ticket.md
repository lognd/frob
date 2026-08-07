---
id: T-0844
title: wire TEST016 mutation-evidence obligation into frob ticket close (not just
  land)
state: done
kind: security
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/tickets/_models.py
- docs/modules/tickets.md
- src/frob/gates/_mutation_evidence.py
- tests/test_evidence_integrity.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: T-0844 needs to add the --skip-mutation-evidence escape hatch to the close
    CLI path (mirroring land), which requires wiring the flag through the argparse
    parser (src/frob/__main__.py) and AppConfig (src/frob/app/config.py), not just
    ticket_runner.py and tickets/__init__.py.
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/config.py
  reason: T-0844 needs to add the --skip-mutation-evidence escape hatch to the close
    CLI path (mirroring land), which requires wiring the flag through the argparse
    parser (src/frob/__main__.py) and AppConfig (src/frob/app/config.py), not just
    ticket_runner.py and tickets/__init__.py.
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/tickets/_models.py
  reason: Need a new TicketError variant (mirroring LandError.EvidenceConfirmatoryOnly)
    for the direct-close mutation-evidence refusal path; TicketError lives in src/frob/tickets/_models.py.
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/tickets.md
  reason: New public transition()/mutation_evidence parameter needs docs/modules/tickets.md
    updated in the same change per playbook mandate.
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: The module docstring of frob.gates._mutation_evidence asserts mutation_evidence_violations
    has exactly one caller (land only) and that wiring close is tracked follow-up
    work; T-0844 makes that false, so the docstring prose needs a one-line update
    to stay accurate.
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_evidence_integrity.py
  reason: New tests are needed to cover the transition()/_done_transition_guard mutation_evidence
    parameter and the ticket_runner close-path wiring; adding to tests/test_evidence_integrity.py
    (the T-0398 D-0x precedent file) rather than inventing a new file.
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Reviewer REJECT: T-0844s own new lines in config.py/ticket_runner.py are
    confirmatory-only under T-0755s self-check. Adding real adversarial coverage requires
    a CLI-wiring test file; tests/test_ticket_land.py already carries the TestSkipMutationEvidenceCliWiring
    precedent for lands identical flag shape, so the close-path twin belongs there
    too.'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_rejects_when_mutation_evidence_false
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_allows_when_mutation_evidence_true
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_permissive_when_mutation_evidence_none
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
threat: null
component: null
---
T-0755 wired the diff-scoped adversarial evidence obligation (TEST016,
frob.gates.mutation_evidence_violations) into `frob ticket land`
(frob.tickets._land._check_mutation_evidence), because frob.tickets/**
and frob.gates/** were in scope but frob.app/** was not.

`frob ticket close` (the direct, non-land close path) goes through
frob.app.ticket_runner and frob.tickets.transition, and does NOT run the
mutation-evidence check today -- a security/bug-kind ticket closed
directly (never landed) can still close on confirmatory-only evidence.

Plan: inject mutation_evidence_violations (or an equivalent
Callable[[Ticket], tuple[Violation, ...]]) into the close-path CLI
runner, mirroring the covers_scope/reviewed injection pattern
transition()/_done_transition_guard() already use, and block DONE on an
ERROR-severity finding the same way land does.