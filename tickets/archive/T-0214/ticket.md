---
id: T-0214
title: COV002 close-before-commit catch-22 turns covered changes into hard errors
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_covers_own_closing_diff
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_without_grace_still_fires
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-public: closing the covering ticket while its strata file is still uncommitted turned every symbol in the file into 'changed with no open ticket' (30 hard errors) which vanish after commit. Either honor recently-done tickets' frob:ticket references for working-tree changes (grace window until commit) or make frob ticket close warn when the covering scope still has uncommitted changes, and document commit-then-close ordering in the playbook. Relates to T-0176 land (which enforces the safe order mechanically).