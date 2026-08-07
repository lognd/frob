---
id: T-1422
title: 'frob ticket accept can only append: add amend and remove for acceptance criteria,
  with a recorded reason'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
- tests/test_tickets_acceptance.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_accept.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_reporting.py
- docs/modules/tickets.md
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_metadata.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_accept.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/tickets.md
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/config.py
  reason: 'declared scope named a nonexistent src/frob/app/ticket_runner/_metadata.py

    (no such path in the tree). The real CLI-flag registration for accept

    lives at src/frob/_cli_parsers/_ticket/_metadata.py; the command

    implementation lives in src/frob/app/ticket_runner/_mutate.py alongside

    _scope/_accept; a new src/frob/tickets/_accept.py module holds the

    amend/remove logic (T-0455''s _scope.py split pattern) wired through

    frob/tickets/__init__.py; surfacing the amendment requires touching

    show''s renderer (_query.py) and Done report composition (_reporting.py);

    docs/modules/tickets.md documents the new verbs in the same change.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_replaces_text_and_records_reason
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_reason_containing_hash_colon_and_quotes_round_trips
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_replaces_text
- tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_show_renders_amendment_and_reason
- tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_done_report_renders_amendment_section
- tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_done_report_omits_section_when_no_amendments
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_on_terminal_ticket
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_refuses_on_terminal_ticket
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_preserves_existing_evidence_binding
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_empty_reason
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_out_of_range_index
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_drops_criterion_and_records_reason
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_remove_drops_criterion
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_without_reason_exits_nonzero
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_and_remove_together_is_rejected
designated_repro_test: null
acceptance:
- text: GIVEN a ticket with a mis-specified acceptance criterion WHEN it is amended
    via the CLI with a reason THEN the new text replaces the old and the reason is
    recorded in the ledger, the way scope changes already record theirs
  evidence:
  - tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_replaces_text_and_records_reason
  - tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_reason_containing_hash_colon_and_quotes_round_trips
  - tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_replaces_text
- text: GIVEN an amended criterion WHEN the ticket is shown or its Done report rendered
    THEN the amendment and its reason are surfaced, never buried
  evidence:
  - tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_show_renders_amendment_and_reason
  - tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_done_report_renders_amendment_section
  - tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_done_report_omits_section_when_no_amendments
- text: GIVEN a ticket in a terminal state WHEN an amendment is attempted THEN it
    is refused
  evidence:
  - tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_on_terminal_ticket
  - tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_refuses_on_terminal_ticket
threat: null
component: null
---
frob ticket accept can only APPEND acceptance criteria. There is no supported way to correct, replace, or remove one. That gap forces the two worst available workarounds, and both were exercised on 2026-08-01/02.

WORKAROUND 1, hand-editing the ledger. Used twice. The second attempt embedded a space followed by a hash inside a plain YAML scalar, which starts a comment, truncating the mapping. tickets.md stopped parsing and frob reported "ticket queue failed to load: all gates were skipped. This is a hard failure" -- the ENTIRE gate layer down, not just the tickets gate. frob's own pre-commit hook had warned "the ledger should only be written via the frob ticket CLI" on three separate commits that day. The hook was right every time.

WORKAROUND 2, filing a successor ticket. Used for T-1414, carrying T-1296's delivered strata work. This one is honest and is the right answer when the ORIGINAL goal genuinely remains open. But it is roughly fifteen minutes of ledger surgery per instance -- new ticket, scope, start, evidence rebind, done report, land -- and it leaves two ledger entries where the work was one.

WHY IT MATTERS NOW, beyond convenience. A criterion can be WRONG in two distinct ways, and both occurred:

  Mis-specified. T-1411's criterion [0] asked that a comment naming no in-scope identifier must not fire PII012. A trailing comment reading "stores the user ssn" names no matching identifier either, so satisfying the criterion as written would have SILENCED the poorly-named-variable case the rule exists for. An agent implemented it faithfully and produced a capability regression that passed review, because the criterion is what review checks against. Caught only because the agent surfaced two now-failing tests honestly instead of updating them.

  Unsatisfiable by construction. Ten burn-down tickets assert "0 TEST005 findings under package X" across packages holding 100-400 findings. No single dispatch can satisfy that. Since T-1410 wired the gate-claim guard, frob correctly REFUSES to close them -- which is right, and which also means genuine completed work strands behind a criterion that was written as an aspiration rather than a deliverable.

Neither is fixable today without one of the two workarounds above.

WHAT TO BUILD. A supported way to amend acceptance, with the same discipline the rest of the ledger has. At minimum a verb to replace a criterion's text by index and a verb to remove one, both requiring a --reason recorded in the ledger exactly as frob ticket scope already records scope changes. The reason field is the point: an amended criterion must carry WHY it changed, so that weakening a criterion to force a close is visible in the record rather than silent.

Guard against the obvious abuse. Amending a criterion is a legitimate correction when the criterion was wrong; it is goalpost-moving when the criterion was right and the work fell short. The distinction cannot be fully automated, but the reason string makes it reviewable, and amendments should be surfaced -- in frob ticket show, and in the Done report -- rather than buried. Consider refusing an amendment on a ticket already in a terminal state.

Then re-scope the ten burn-down tickets to triage-shaped acceptance, the shape already used on T-1400: every remaining finding is triaged as either a genuine gap closed with a behavioral test, or an artifact recorded with the covering test named. That is satisfiable, honest, and still forbids filler -- and it is what T-1418's classification is producing the input for.