---
id: T-1348
title: Land auto-fix phase must be transactional and leave a safe recovery path
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: high
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_fix_engine.py
- docs/modules/tickets.md
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: apply_tier_a_fixes' affects()-closure doc anchor lives here; the T-1348
    crash-safety/manifest change must update it
  actor: logan
  at: '2026-07-31'
- op: add
  glob: tests/test_gates.py
  reason: the T-1348 crash-safety/manifest tests live here
  actor: logan
  at: '2026-07-31'
evidence:
- tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip
- tests/test_gates.py::TestAutofixManifest::test_apply_tier_a_fixes_clears_manifest_on_clean_finish
- tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes
- tests/test_gates.py::TestTierAAutofixCrashSafety::test_kill_between_write_and_rename_leaves_original_file_intact
designated_repro_test: null
acceptance:
- text: given a land killed mid-auto-fix, when the worktree is inspected, then no
    source file is left half-rewritten
  evidence:
  - tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip
  - tests/test_gates.py::TestAutofixManifest::test_apply_tier_a_fixes_clears_manifest_on_clean_finish
  - tests/test_gates.py::TestTierAAutofixCrashSafety::test_kill_between_write_and_rename_leaves_original_file_intact
- text: given a land killed mid-auto-fix, when an agent recovers, then it can identify
    exactly which paths land rewrote without discarding its own uncommitted work
  evidence:
  - tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip
  - tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes
threat: null
component: tickets
---
Leaf of T-1344. Observed on T-1338 (2026-07-31): a "frob ticket land" run was killed by a timeout DURING its Tier-A auto-fix phase. That left a source file (src/frob/gates/_debt_deprecated.py) GARBLED -- a half-applied rewrite. The agent did the obvious thing, "git checkout -- <file>", which cleaned the garble but SILENTLY DESTROYED an uncommitted new test method in a different file it also reverted. It was caught only because a pytest count in a later run did not match expectations.

Two distinct defects, both worth fixing:

1. NON-ATOMIC AUTO-FIX. Land absorbs frob fmt, sync-interface, and the Tier-A fix handlers before its own merge. If it dies mid-phase the tree is left in a state that is neither before nor after. Make the auto-fix phase transactional: stage rewrites and commit them as one unit, or write through a temp-and-rename so a kill leaves the ORIGINAL intact. T-1262 covers a Tier-B apply-verify-rollback engine; this is the land-side gap and is not the same ticket.

2. NO SAFE RECOVERY. After an interrupted land, an agent cannot distinguish "this file is garbled by the dead autofix" from "this file has my uncommitted work in it". Land should leave a recovery breadcrumb naming exactly which paths it rewrote (under .frob/), so recovery is targeted instead of a blanket checkout. Consider also auto-committing a wip snapshot BEFORE the auto-fix phase begins -- land already makes a pre-merge wip commit, so moving that earlier may fix this almost for free.

Interim mitigation now in dispatch prompts: agents are told to commit new tests BEFORE running land. That is a workaround, not a fix -- it depends on every agent remembering.