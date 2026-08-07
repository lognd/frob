---
id: T-0165
title: 'DOC002 anchor errors: report the computed slug and suggest nearest valid anchor'
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
- src/frob/docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDocanchorGate::test_unresolvable_anchor_reports_slug_and_nearest_match
- tests/test_gates.py::TestDocanchorGate::test_unresolvable_anchor_fires
- tests/test_gates.py::TestDocanchorGate::test_missing_file_fires
- tests/test_gates.py::TestDocanchorGate::test_malformed_target_missing_fragment_fires
- tests/test_gates.py::TestDocanchorGate::test_resolvable_heading_and_explicit_anchor_pass
designated_repro_test: null
threat: null
component: null
---
Typani pilot: DOC002 anchor-resolution failures forced manual guessing of GitHub-style slugs. The error must print the slug it computed, the anchors it found in the target file, and the nearest match (edit distance). Small change, large DX payoff for every frob:doc user.