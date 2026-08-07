---
id: T-0444
title: 'evidence_covers_scope rejects docs-kind tickets: covering-test requirement
  unsatisfiable for doc-only scope (contradicts T-0215 cmd-evidence)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_evidence_integrity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_evidence_covers_scope_true_for_docs_kind_with_cmd_evidence
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_evidence_covers_scope_false_for_code_kind_with_cmd_shaped_evidence
designated_repro_test: null
threat: null
component: null
---
Found while landing T-0267 (a docs-only correction). The evidence-integrity
D-02 check `evidence_covers_scope` requires at least one non-cmd (pytest)
evidence id that binds to a code symbol under the ticket's scope. A docs-kind
ticket is scoped to documentation files, which have no coverable code symbol,
so the check can NEVER be satisfied -- yet T-0215 explicitly sanctions
docs-kind tickets closing on a `--evidence-cmd` exit status
(`CMD_EVIDENCE_ALLOWED_KINDS = {docs}`). The two mechanisms contradicted:
docs tickets were unclosable (EvidenceScopeUnbound) despite following the
sanctioned evidence path. This is over-reach in the recently-strengthened
evidence-integrity gate, not a property of the ticket.