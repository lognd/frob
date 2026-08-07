---
id: T-0713
title: Audit COV007 dedup passes (T-0524) for over-pruned extending-guide anchors
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/unit/test_extending_guides_complete.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_extending_guides_complete.py
  reason: audit-only ticket concluded honest-no-findings (T-0706 already fixed the
    one real over-prune); this canary test is the audit's own evidence/instrument,
    scope-bind it per the T-0398 source+test convention
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_has_a_guide_file
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_anchor_file_exists_and_mentions_guide
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_no_orphan_guides
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_probe_table_and_inventory_agree
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_probe_still_matches_source
designated_repro_test: null
threat: null
component: null
---
found while working T-0706: 2642c5f3 (T-0524) removed the docs/guides/extending/capability-registry.md#capability-registry frob:doc anchor above DANGEROUS_OPERATIONS in src/frob/vet/_capability_registry.py as a supposed COV007 duplicate, but no other anchor in the file carried the extending-guide fragment -- broke tests/unit/test_extending_guides_complete.py silently until T-0706 caught and restored it (waived SCOPE001 there). Audit other T-0524 COV007 dedup commits for the same over-pruning pattern against docs/guides/extending/registry_of_registries.json rows.