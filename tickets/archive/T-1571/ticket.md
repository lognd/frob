---
id: T-1571
title: 'cli regrouping: help-surface rework -- group verbs in frob --help output'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1725
- T-1764
- T-1765
- T-1766
parent: T-1238
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__main__.py
- docs/design/cli-regrouping.md
- tests/unit/test_main_entry.py
- tickets/T-1571/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: narrow mega-glob to the exact files T-1571 (help-surface rework) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: narrow mega-glob to the exact files T-1571 (help-surface rework) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: narrow mega-glob to the exact files T-1571 (help-surface rework) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1571/**
  reason: narrow mega-glob to the exact files T-1571 (help-surface rework) touches
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_verb_groups_listed_before_also_available_directly_section
- tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_non_group_verb_listed_after_also_available_directly
- tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_nested_subparser_help_is_unaffected
designated_repro_test: null
threat: null
component: null
---
Refiled from T-1571 (T-1238 slice, draft-loss class; also cited by T-1238's Done report). Rework the top-level frob --help output to present the T-1238 verb groups instead of the flat 30+ subcommand list.