---
id: T-1135
title: 'EPIC frob refactor: transactional move/rename/split with full reference, directive,
  and obligation rewrite'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-1135/**
evidence_scope:
- tests/test_refactor.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'T-2446: epic per its own body (''children to file at design time''); NEEDS
    DECOMPOSITION per fleet_status.py at 20+ days old -- narrowing the parent to its
    own ledger shard is correct, the real file scopes belong to the not-yet-filed
    children'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/**
  reason: 'T-2446: epic per its own body (''children to file at design time''); NEEDS
    DECOMPOSITION per fleet_status.py at 20+ days old -- narrowing the parent to its
    own ledger shard is correct, the real file scopes belong to the not-yet-filed
    children'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/**
  reason: 'T-2446: epic per its own body (''children to file at design time''); NEEDS
    DECOMPOSITION per fleet_status.py at 20+ days old -- narrowing the parent to its
    own ledger shard is correct, the real file scopes belong to the not-yet-filed
    children'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-1135/**
  reason: 'T-2446: epic per its own body (''children to file at design time''); NEEDS
    DECOMPOSITION per fleet_status.py at 20+ days old -- narrowing the parent to its
    own ledger shard is correct, the real file scopes belong to the not-yet-filed
    children'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): epic-rollup close: T-1135''s only child T-1197
    is shipped and archived done; re-verification confirmed the code (refactor/_repointer.py,
    _directives.py, _prose.py, _alias_policy.py, _transaction.py) satisfies the epic''s
    own wider acceptance wording, no amendment or code change needed'
  actor: logan
  at: '2026-08-18'
  old_length: 9774
  new_length: 10092
evidence:
- tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
- tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten
- tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move
- tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten
- tests/test_refactor.py::TestRepointer::test_archived_per_ticket_ledger_file_evidence_rewritten
- tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
- tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write
- tests/test_refactor.py::TestProseCarrier::test_docs_prose_and_code_block_rewritten
- tests/test_refactor.py::TestRunRefactor::test_run_refactor_does_not_roll_back_on_ticket_md_evidence_carrier
designated_repro_test: null
acceptance:
- text: 'GIVEN frob refactor move/rename/split on a symbol or module family WHEN it
    completes THEN all imports and call sites are rewritten (absolute imports, auto-aliasing
    on destination or import-site name conflicts, with a disclosed alias report),
    and every frob-owned reference moves with the symbol: frob:tests/frob:doc/frob:enforces
    target forms, waiver symrefs including path:: prefixes, PII012 (file,token) allowlist
    entries, check-coverage registry citations, and archived-ticket evidence node
    ids'
  evidence:
  - tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
  - tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten
  - tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move
  - tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten
  - tests/test_refactor.py::TestRepointer::test_archived_per_ticket_ledger_file_evidence_rewritten
- text: GIVEN a refactor that cannot complete every rewrite THEN it refuses and rolls
    back rather than leaving a half-move; post-conditions verified in-command (import
    graph resolves, tests collect, gate findings diff-clean vs pre-refactor)
  evidence:
  - tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
  - tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write
- text: 'GIVEN a moved or renamed symbol WHEN the refactor completes THEN every mention
    of it in prose is rewritten too: docstrings and comments naming the dotted path
    (including all frob: comment-DSL directive targets anywhere in the repo, not just
    those attached to the moved symbol), docs/** prose and code refs, and doc anchors
    whose heading slugs embed the symbol or module name -- auto-documentation updating
    is part of the transaction, with unresolvable prose mentions listed in the disclosed
    report rather than silently skipped'
  evidence:
  - tests/test_refactor.py::TestProseCarrier::test_docs_prose_and_code_block_rewritten
  - tests/test_refactor.py::TestRunRefactor::test_run_refactor_does_not_roll_back_on_ticket_md_evidence_carrier
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: bbdcc97bd8c3f2ad469ade1dd179a5959bec4db8
---
User directive 2026-07-28: refactors today mean an agent hand-editing every import and callsite, and -- the expensive part -- hand-carrying frob's symbol-attached bookkeeping. Second user directive same day: the rewrite must ALSO cover frob symbols and symbols in comments -- auto-documentation updating -- because a rename that fixes code but strands docs/docstring/comment mentions just converts silent breakage into doc drift (the DRIFT001/DOC006 class this repo keeps paying down). Evidence from this drive: 3 coordinator INV006 waiver carries in one wave (0abc4e3a), PII012 allowlist re-keying on every move (T-1076), the ARCH101/103 waiver-symref path:: bug where moved waivers never matched again, archived evidence repoints after litmus renames (8dae48c5), DRIFT002 edge repoints. frob owns the graph/binding/exports substrate to do this transactionally. Python first; the multi-language binding tables (TS/Rust/C-C++/Kotlin) extend it later. Children to file at design time: reference-rewrite engine, directive/waiver carrier (absorbs T-1134), registry/evidence repointer, split verb built on the T-1072/T-1077 family-extraction pattern, alias-conflict policy. Relationship: makes T-1108/T-1115-class split tickets mechanical.