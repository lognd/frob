---
id: T-0094
title: 'frob ticket evidence subcommand: append structured evidence ids from the CLI'
state: done
kind: ux
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
- src/frob/__main__.py
- docs/modules/tickets.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestEvidence::test_resolvable_ids_appended
- tests/test_tickets.py::TestEvidence::test_parametrized_bare_name_matches
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_rejected
- tests/test_tickets.py::TestEvidence::test_mixed_batch_rejected_wholesale
- tests/test_tickets.py::TestEvidence::test_dedupes_against_existing_evidence
- tests/test_tickets.py::TestEvidence::test_unknown_ticket_not_found
designated_repro_test: null
threat: null
component: null
---
Three implementer agents in a row (T-0062, T-0063, T-0064) wrote Done-report prose evidence but left the structured evidence: YAML empty or wrong (cargo ids), because the only way to record evidence is hand-editing tickets.md YAML. Add 'frob ticket evidence T-XXXX <pytest-node-id>...' that validates ids against collected tests (rejecting unresolvable ids up front, closing the COV003 gap at write time) and appends to the structured list. Orchestration keeps catching this by hand; the tool should make the right thing the easy thing.