---
id: T-0492
title: 'frob ticket evidence: dot-form Class.method ids never verify as passing (raw
  ids passed to _verify_ids_passing before normalization)'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- tests/test_tickets_evidence_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: T-0492 regression test for dot-form evidence-id normalization mirrors src/frob/app/ticket_runner.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_tickets_evidence_cli.py::TestDotFormEvidenceNormalizesBeforePassingCheck::test_dot_form_id_passes_exactly_like_its_colon_form
designated_repro_test: null
threat: null
component: null
---
Found while working T-0400. `frob ticket evidence <id> "path::Class.method"` (the dot form the playbook/docs document as the canonical evidence-id spelling) ALWAYS fails with EvidenceNotPassing, even when the test genuinely passes. Root cause: _apply_evidence (src/frob/app/ticket_runner.py) passes the raw, un-normalized node_ids straight into _verify_ids_passing, which buckets ids via matches_collected(n, python_collected) -- but python_collected (from _collect_python_and_rust_ids) stores pytest's native '::' form only. A dot-form id never matches_collected() against that set, so its bucket is empty, run_selected has nothing to run, and the id silently ends up absent from the returned passing frozenset -- rejected downstream as EvidenceNotPassing with a misleading message (the test did pass, it was just never actually invoked for this check). add_evidence's OWN normalization (_validate_evidence_list, T-0293) already converts dot-form to :: form before resolution/persistence; _apply_evidence needs to pass that SAME normalized list into _verify_ids_passing instead of the raw CLI args, or the two normalization paths silently diverge. Repro: 'frob ticket evidence T-XXXX "tests/test_foo.py::TestBar.test_baz"' rejects; 'frob ticket evidence T-XXXX "tests/test_foo.py::TestBar::test_baz"' (:: form) for the identical test succeeds. Workaround used in T-0400: recorded evidence in :: form.