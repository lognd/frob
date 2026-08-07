---
id: T-1537
title: 'frob ticket evidence --replace: rebind evidence ids when tests are renamed/parametrized'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/ticket_runner/_verify.py
- tests/test_tickets_evidence_cli.py
- src/frob/tickets/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'T-1537 frob ticket evidence --replace: rebind evidence ids atomically through
    the single-writer path'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1537 frob ticket evidence --replace: rebind evidence ids atomically through
    the single-writer path'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'T-1537 frob ticket evidence --replace: rebind evidence ids atomically through
    the single-writer path'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'T-1537 frob ticket evidence --replace: rebind evidence ids atomically through
    the single-writer path'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: 'T-1537 frob ticket evidence --replace: rebind evidence ids atomically through
    the single-writer path'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: T-1537 needs replace_evidence re-exported from the tickets package
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_replaces_flat_evidence_and_acceptance_binding_atomically
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_old_node_absent_is_a_hard_refusal
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_unresolvable_new_node_is_rejected
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_same_old_and_new_is_a_no_op_success
- tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replaces_and_commits
- tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_requires_at_least_one_of_the_three_modes
- tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_not_found_exits_nonzero
designated_repro_test: null
threat: null
component: null
---
Renaming or parametrizing a test that is bound as ticket evidence currently orphans the binding: land fails 'evidence no longer resolves post-merge' and there is no CLI to fix it -- the coordinator had to hand-edit via store APIs (write_ticket) twice on 2026-08-04 (T-1520 parametrization). Deliver: frob ticket evidence <id> --replace <old-node> <new-node> [--path .], updating both the evidence list and every acceptance criterion binding atomically through the single-writer path; follow-up (draft if needed): frob refactor rename detecting bound-evidence references and offering the rebind automatically.