---
id: T-5240
title: extending guide failure-injection-acceptance-criteria.md missing registry_of_registries.json
  row
state: done
kind: docs
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/extending/registry_of_registries.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_no_orphan_guides
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_probe_table_and_inventory_agree
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5240
branch: t-5240
---
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_no_orphan_guides fails: guide file docs/extending/failure-injection-acceptance-criteria.md exists on disk but has no row in registry_of_registries.json. Fix: add the missing inventory row (title/description per the existing rows' shape).