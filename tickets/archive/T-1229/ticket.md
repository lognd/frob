---
id: T-1229
title: negative-existence claims -- bind absence-claims to a ticket via frob:until,
  flag unbound ones
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- docs/design/registry/check-coverage.yaml
- docs/modules/gates.md
- docs/modules/graph.md
- tests/unit/gates/test_negexist.py
- tests/test_graph.py
- docs/guides/extending/comment-dsl-directives.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'Coordinator brief for T-1229 explicitly requires registering the new

    NEGEXIST001 gate rule id in docs/design/registry/check-coverage.yaml

    (one documented entry, gate_rule_total bumped by exactly one) alongside

    _KNOWN_GATE_RULES -- this is the WIRE001/T-1428 registry-completeness

    requirement for any new gate rule literal, not an unrelated expansion.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/gates.md
  reason: 'Docs move with code (playbook rule): NEGEXIST001''s frob:doc anchor

    (gates.md) and the frob:until/frob:enumerates comment-DSL prose

    (graph.md) must exist for DOC002 to resolve the new gate''s own

    frob:doc pointer and to document the new directive for humans/agents.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/graph.md
  reason: 'Docs move with code (playbook rule): NEGEXIST001''s frob:doc anchor

    (gates.md) and the frob:until/frob:enumerates comment-DSL prose

    (graph.md) must exist for DOC002 to resolve the new gate''s own

    frob:doc pointer and to document the new directive for humans/agents.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/gates/test_negexist.py
  reason: 'Evidence recording requires a real test file covering the new

    NEGEXIST001 gate and frob:until/CLAIMS_ABSENCE markdown-anchor parsing.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_graph.py
  reason: 'Evidence recording requires a real test file covering the new

    NEGEXIST001 gate and frob:until/CLAIMS_ABSENCE markdown-anchor parsing.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/guides/extending/comment-dsl-directives.md
  reason: 'Adding "until" to _VERB_TABLE (T-1229''s code-side frob:until form)

    made this doc''s DOCENUM001-checked member list stale immediately --

    a real DOCENUM001 gate error, not optional cleanup.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_until_directive_emits_until_edge
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_negative_existence_phrase_emits_claims_absence_edge
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_not_yet_wired_phrase_is_also_detected
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_directive_comment_line_itself_never_matches_the_heuristic
- tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_plain_prose_with_no_matching_phrase_emits_nothing
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_unbound_claim_is_flagged
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_open_ticket_is_clean
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_closed_ticket_is_stale
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_missing_ticket_is_stale
- tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_no_claims_at_all_is_clean
designated_repro_test: null
threat: null
component: null
---
A directive (e.g. frob:until T-####) binds not-yet-built prose to a ticket; when the ticket closes/archives the claim goes stale. Unbound absence-claims ('does not exist yet' heuristics) get flagged for binding. The sweep found ~20 shipped-but-documented-as-absent instances (docs/audits/docs-staleness-2026-07-29.md, 'Negative-existence claims' section). Ref: gate-gap class 3.