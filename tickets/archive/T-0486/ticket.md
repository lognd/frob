---
id: T-0486
title: 'dup/_legacy_py._harvest_with: with-item alias lookup uses nonexistent ''alias''
  field, as-pattern binding names never join the alpha-rename set'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_legacy_py.py
- tests/unit/test_dup.py
- tests/unit/test_dup_legacy_py.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/dup/_legacy_py.py
  reason: T-0486's frontmatter scope was empty (recovered ticket only stated scope
    in free-text body); backfilling it so SCOPE001's cross-ticket exemption recognizes
    tests/unit/test_dup.py as T-0486's own scope, not T-0487's
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_dup.py
  reason: T-0486's frontmatter scope was empty (recovered ticket only stated scope
    in free-text body); backfilling it so SCOPE001's cross-ticket exemption recognizes
    tests/unit/test_dup.py as T-0486's own scope, not T-0487's
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_dup_legacy_py.py
  reason: T-0486's frontmatter scope was empty (recovered ticket only stated scope
    in free-text body); backfilling it so SCOPE001's cross-ticket exemption recognizes
    tests/unit/test_dup.py as T-0486's own scope, not T-0487's
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_dup.py::TestFindDuplicates::test_with_target_alpha_rename_matches_at_renamed_rung
designated_repro_test: null
threat: null
component: null
---
Recovered filing: T-0486 (ex-draft, id lost at land) was filed in T-0160 batch work but its ledger block was lost in a merge (only the Done-report prose survived). _harvest_with looks up child_by_field_name('alias') on with_item nodes, but the tree-sitter-python grammar nests with_item under with_clause and represents the bound name via an as_pattern/as_pattern_target child, not an 'alias' field -- so 'with X as name:' binding names are never collected into the alpha-rename local set for Python dup-fingerprinting. Scope: src/frob/dup/_legacy_py.py plus its unit tests.