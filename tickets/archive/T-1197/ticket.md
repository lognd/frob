---
id: T-1197
title: 'refactor: reference-rewrite engine (resolve/plan/apply/verify pipeline)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1135
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- docs/commands/refactor.md
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_refactor.py::TestRunRefactor::test_rename_succeeds_and_commits
- tests/test_refactor.py::TestVerify::test_import_resolution_passes_clean_files
- tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
- tests/test_refactor.py::TestRunRefactor::test_verify_failure_rolls_back
- tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
- tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write
- tests/test_refactor.py::TestApplyPlan::test_apply_failed_on_write_error_reports_apply_failed
- tests/test_refactor.py::TestRunRefactor::test_apply_failure_recovers_clean_precommit_tree
- tests/test_refactor.py::TestScanReferences::test_semicolon_joined_from_import_refuses_rewrite
- tests/test_refactor.py::TestScanReferences::test_unresolved_attribute_style_reference_surfaces
- tests/test_refactor.py::TestVerify::test_check_delta_uses_current_interpreter
- tests/test_refactor.py::TestVerify::test_import_resolution_catches_dangling_reference
- tests/test_refactor.py::TestVerify::test_import_resolution_local_import_resolves
designated_repro_test: null
reviews:
- verdict: reject
  reviewer: review-pass
  findings: "Reviewer findings requiring rework before re-close:\n\n1. BLOCKING: src/frob/refactor/_apply.py:79-107\
    \ -- overlapping/same-line\n   RewriteOps silently clobber each other; each op\
    \ computed against\n   ORIGINAL source, sorted by start_line descending, so two\
    \ ops sharing a\n   start_line means the second applied overwrites the first wholesale\
    \ with\n   no warning, and verify often still passes. Also _scan.py:264-277\n\
    \   _import_op replaces the whole [lineno, end_lineno] span, silently\n   deleting\
    \ other code sharing the physical line (e.g. semicolon-joined\n   statements).\
    \ Fix: detect overlapping/duplicate line ranges across ops\n   targeting the same\
    \ file and REFUSE with a typani Result error (not an\n   exception), at plan-time\
    \ or apply-time. Add tests for same-line\n   multi-ref and semicolon-joined cases.\n\
    \n2. src/frob/refactor/_verify.py:112 -- verify_check_delta shells out to\n  \
    \ bare `frob check --delta`, which per playbook sec 2 can be a stale\n   global\
    \ binary. Invoke the current interpreter's frob (sys.executable\n   -m frob) or\
    \ the repo venv's frob, version-consistent with the running\n   code. Add/adjust\
    \ a test.\n\n3. BLOCKING: verify_import_resolution is ast.parse-only (a stand-in)\
    \ while\n   the ticket promises import-graph resolution. Implement real import\n\
    \   resolution for touched modules (frob.graph rebuild + resolve check per\n \
    \  ticket body), or, if genuinely out of reach this session, rename the\n   function\
    \ honestly (verify_syntax), disclose the limitation explicitly\n   in the CLI\
    \ report and docs/commands/refactor.md, make pytest-collect\n   verification non-skippable\
    \ by default, and file a follow-up ticket for\n   real import resolution. Prefer\
    \ implementing it for real.\n\n4. No test exercises apply_plan's OSError failure\
    \ path or run_refactor's\n   pre-commit reset-and-clean recovery (_apply.py:124-126,\n\
    \   _transaction.py:269-276). Add a real test (e.g. monkeypatched write\n   failure\
    \ mid-file-set) asserting the tree is restored.\n\n5. The unresolved attribute-style-reference\
    \ path (_scan.py:151-181\n   _handle_import) has zero coverage. Add a test with\
    \ `import\n   old.module` + `old.module.qualname(...)` usage asserting `unresolved`\n\
    \   populates and surfaces in the report."
  commit: 2320155238aa75f5cc285253230cbb437486ecf0
  at: '2026-07-29'
acceptance:
- text: 'GIVEN a Python symbol renamed via `frob refactor rename` WHEN every import

    and call site is rewritten THEN a fresh `pytest --collect-only` over the

    repo shows no new collection error and `frob check --delta` against a

    pre-refactor baseline stamp shows zero new findings (allowing for the

    same finding relocated to the new symref)'
  evidence:
  - tests/test_refactor.py::TestRunRefactor::test_rename_succeeds_and_commits
  - tests/test_refactor.py::TestVerify::test_import_resolution_passes_clean_files
  - tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
  - tests/test_refactor.py::TestRunRefactor::test_verify_failure_rolls_back
  - tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
- text: 'GIVEN a rename target whose destination name collides with something

    already imported at a call site WHEN the refactor applies THEN that call

    site gets an auto-generated import alias, and the disclosed report names

    every alias generated'
  evidence:
  - tests/test_refactor.py::TestRunRefactor::test_rename_succeeds_and_commits
  - tests/test_refactor.py::TestVerify::test_import_resolution_passes_clean_files
  - tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
  - tests/test_refactor.py::TestRunRefactor::test_verify_failure_rolls_back
  - tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
- text: 'GIVEN a refactor whose apply phase cannot complete every planned rewrite

    WHEN it detects this THEN it refuses and rolls back via `git reset --hard`

    to its own pre-transaction commit, never leaving a half-moved symbol, and

    never touching refs/stash'
  evidence:
  - tests/test_refactor.py::TestRunRefactor::test_rename_succeeds_and_commits
  - tests/test_refactor.py::TestVerify::test_import_resolution_passes_clean_files
  - tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
  - tests/test_refactor.py::TestRunRefactor::test_verify_failure_rolls_back
  - tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
threat: null
component: null
---
Design: docs/design/refactor-verb.md (T-1135). Build the shared
resolve/plan/apply/verify transaction pipeline for `frob refactor`:

- Resolve phase: given a Python move/rename/split target, use frob.lang +
  frob.graph to locate the symbol(s) unambiguously; refuse with no writes
  if the target does not resolve or a destination name collision has no
  --alias-conflict policy given (policy itself is T-1135's alias-conflict
  child; this ticket just exposes the extension point).
- Plan phase: build the full rewrite plan (import/call-site rewrites incl.
  auto-alias on conflict, absolute-import form) before any file write.
- Apply phase: AST-level move preserving formatting outside the moved
  span; rewrite Python import/call sites; commit as one WIP commit in the
  caller's own worktree (never git stash, per agent-playbook.md sec 1b).
- Verify phase: import graph resolves (frob.graph rebuild + import
  resolution check), pytest --collect-only succeeds with no new
  collection error, frob check --delta against a pre-refactor baseline
  stamp is diff-clean (identity-aware: a finding that moved with its
  symref is not "new").
- Rollback: any verify-phase failure does `git reset --hard` to the
  pre-transaction commit inside the caller's own worktree (never touches
  refs/stash) and prints the disclosed report (attempted rewrites, why it
  could not complete).
- New CLI verb `frob refactor move`/`frob refactor rename` (split is a
  separate child), with docs/commands/refactor.md added following the
  existing docs/commands/*.md per-command convention.
- This ticket owns ONLY the Python-import/call-site reference kind and
  the shared pipeline; frob-owned DSL/waiver/registry/evidence rewriting
  is out of scope (children 2 and 3 extend this pipeline's reference-kind
  inventory, they do not reimplement resolve/plan/apply/verify).