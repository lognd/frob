---
id: T-1200
title: 'refactor: registry/evidence repointer (PII012 allowlist, registry citations,
  ticket evidence)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- tests/test_refactor.py
- docs/commands/refactor.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: docs move with code per playbook sec 4/6; the repointer functions get anchors
    in the same change that adds them
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move
- tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten
- tests/test_refactor.py::TestRepointer::test_ticket_evidence_symref_rewritten
designated_repro_test: null
acceptance:
- text: 'GIVEN a PII012 allowlist entry keyed on (old_file_path, token) WHEN the

    file is moved via `frob refactor move` THEN the entry is re-keyed to

    (new_file_path, token) and no new PII012 finding fires at the new

    location for that token'
  evidence:
  - tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move
- text: 'GIVEN a registry entry in docs/design/registry/*.yaml whose handled_by/

    caught_by citation embeds a literal path::qualname string for a moving

    symbol, not reachable via a frob:enforces DSL edge WHEN the move

    completes THEN that citation string is rewritten and

    frob.gates._registry_exhaustiveness reports no new REG008/REG009 finding'
  evidence:
  - tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten
- text: 'GIVEN a closed ticket in tickets.md or tickets-archive.md whose Evidence

    section cites a path::Class.method or pytest node id for a moving symbol

    WHEN the move completes THEN the cited evidence string is rewritten to

    the new symref and remains resolvable'
  evidence:
  - tests/test_refactor.py::TestRepointer::test_ticket_evidence_symref_rewritten
threat: null
component: null
---
Design: docs/design/refactor-verb.md (T-1135). Extends T-1197's plan/apply
pipeline with the three remaining non-DSL reference kinds named in the
epic:

- PII012 (file, token) allowlist entries: locate the exact storage first
  (src/frob/gates/_pii_structural/ is the closest hit found during design
  survey -- confirm the exact file/data shape before writing the repoint
  logic), then re-key any entry whose file half matches a moving path to
  the new path, token half unchanged (T-1076 precedent for why this keeps
  breaking by hand today).
- check-coverage registry citations (docs/design/registry/*.yaml,
  handled_by/caught_by, read by frob.gates._registry_exhaustiveness
  REG004-011): survey whether any registry entry embeds a literal
  path::qualname string outside a frob:enforces edge (the directive
  carrier, T-1199, already keeps frob:enforces targets correct via the
  DSL rewrite -- this ticket only needs to cover a citation that is NOT
  reachable that way, if one exists).
- Archived-ticket evidence node ids: pytest node ids and path::Class.method
  forms recorded in tickets.md Done-report/Evidence sections and in
  tickets-archive.md, for any ticket (open or archived) whose evidence
  cites a symref that is moving. Both files, not just the live ledger.

This ticket owns the "everything the directive carrier's DSL rewrite
cannot reach" residue -- coordinate with T-1199 to avoid double-rewriting
a citation that IS reachable via frob:enforces.