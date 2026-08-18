---
id: T-2353
title: priority/kind/component/tier mutations have no --reason audit trail
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- docs/modules/tickets.md
- docs/modules/tickets-data-storage.md
- tests/test_tickets_priority.py
- tests/test_ticket_evidence.py
- tests/test_tickets_organization.py
- tests/test_tickets_tiers.py
- src/frob/tickets/__init__.py
- tests/test_tickets_scope_mutation.py
- tests/test_tickets_work_and_land_finish.py
- tests/test_ticket_work_and_land_finish.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_setters.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets.md
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_tickets_priority.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_ticket_evidence.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_tickets_organization.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_tickets_tiers.py
  reason: T-2353 requires --reason on priority/kind/component/tier setters (lib+CLI+parsers),
    a shared audit-trail model, doc updates, and existing test call-site updates for
    the new required parameter
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: TriageChangeEntry needs the same package-level re-export ScopeChangeEntry
    already gets, for tests/callers to import it without reaching into _models
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: set_tier's new required reason kwarg (T-2353) breaks this pre-existing unrelated
    call site; fixing the call, not touching its own feature under test
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_tickets_work_and_land_finish.py
  reason: set_tier's new required reason kwarg (T-2353) breaks this pre-existing unrelated
    call site; fixing the call, not touching its own feature under test
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: correct filename typo from prior scope add (tests_tickets_ vs test_ticket_)
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/config.py
  reason: priority/kind/component/tier's new --reason/--reason-file CLI flags need
    AppConfig fields (ticket_triage_reason/ticket_triage_reason_file), forgotten from
    the initial scope grant
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'WIRE001: new CLI dests ticket_triage_reason/ticket_triage_reason_file must
    also be copied here (AppConfig.from_external''s allow-list) or argparse silently
    drops them before AppConfig(**d), T-1422 precedent'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field
- tests/test_tickets_priority.py::TestSetPriority::test_reason_missing_refuses
- tests/test_tickets_priority.py::TestSetPriority::test_reasoned_change_records_triage_entry
- tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field
- tests/test_ticket_evidence.py::TestSetKind::test_reason_missing_refuses
- tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field
- tests/test_tickets_organization.py::TestSetComponent::test_reason_missing_refuses
- tests/test_tickets_tiers.py::TestSetTier::test_updates_tier_field
- tests/test_tickets_tiers.py::TestSetTier::test_reason_missing_refuses
designated_repro_test: tests/test_tickets_priority.py::TestSetPriority::test_reason_missing_refuses
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: 2a18d603b5a84c6022575310ecc413fbd1333a13
---
frob ticket priority <id> <level> accepts NO --reason flag, so a priority
change leaves no audit trail of why it happened. Meanwhile frob ticket
scope and frob ticket accept --amend BOTH require a --reason (recorded in
scope_changes / acceptance_amendments audit trails) and refuse without
one. That is an inconsistency in the ledger's own accountability model:
in a repo whose premise is that unaccounted work is a build failure,
silently re-triaging a ticket's priority is exactly the kind of
unrecorded decision the ledger exists to prevent. Hit this raising
T-2351 from medium to critical -- the change is now in the ledger with
no recorded justification.

Survey ALL the frob ticket mutation verbs before designing the fix
(priority, kind, component, label, tier, sprint, runs-last, block,
...) and report which do and do not require a reason. Then make the
ones that change triage-relevant state consistent, following the
existing --reason/--reason-file pattern (T-0737 precedent) and
recording into a per-ticket audit trail like the existing ones
(scope_changes, acceptance_amendments). Do not invent a new audit
mechanism if one already fits.

POSITIVE CONTROLS: a reason-less invocation of a newly-guarded verb is
REFUSED; a reasoned one records into the audit trail; and verbs that
legitimately need no reason (pure queries) are untouched.