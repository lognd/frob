---
id: T-3533
title: Update TestAutofixManifest.test_killed_mid_handler_leaves_manifest_naming_completed_fixes
  for T-3526's pre-first-mutation journal
state: in-progress
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3526: apply_tier_a_fixes now writes the T-1348 autofix manifest ONCE before the loop starts (empty applied list), not only after each handler completes -- this is the T-3526 fix itself (journal-before-first-mutation, so a kill during the FIRST handler is also detectable as an abandoned state, not just kills after handler N>=1). This makes tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes's final assertion 'assert not _autofix_manifest_path(root).is_file()' fail: the file now legitimately exists (empty rewritten_paths, fix_count=0, pid=<this process>) even though the first handler raised before completing -- this is the CORRECT new behavior, not a regression. Fix: change the assertion to expect the manifest file TO exist with rewritten_paths=[] and fix_count=0 (parse the JSON and assert those fields), and update the test's own docstring/comment (currently says 'no manifest existing yet here is itself correct') to describe the new pre-first-mutation journal contract instead. tests/test_gates.py is out of T-3526's own scope (held by T-3492 at filing time) so this fix could not be made in the same ticket.