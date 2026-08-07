---
id: T-0088
title: reorganize flat docs/ into guides/ modules/ commands/ hierarchy
state: done
kind: docs
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- src/**
- tests/**
- frob-core/**
- README.md
- frob.toml
- tickets.md
- agents/**
- skills/**
- scripts/**
- invariants/**
- TODO.md
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
designated_repro_test: null
acceptance:
- text: GIVEN the moved docs WHEN frob check runs THEN doclink/drift/coverage gates
    pass with zero dangling frob:doc or describes edges
  evidence: []
threat: null
component: null
---
Flat docs/ (31 files) becomes: index.md + rework.md at root; guides/ (quickstart, agentic-workflow); modules/ (19 module design docs); commands/ (9 per-command refs); strata/ unchanged. Every frob:doc directive, describes anchor consumer, markdown/backtick link, and config path updated in the same change.