---
id: T-0213
title: COV001 short message says 'undocumented' for symbols that have docstrings
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
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov001_message_wording_for_docstring_without_doc_edge
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 lograder: COV001 flags DeveloperException/StaffException which HAVE docstrings -- rule means 'no frob:doc edge'; long-form message is correct, short line is wrong and misleads adopters into thinking docstrings satisfy it. Align the short message with the long form.