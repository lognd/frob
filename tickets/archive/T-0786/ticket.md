---
id: T-0786
title: 'AUDIT: gate-by-gate vacuous-satisfaction sweep + lang parser trust-boundary
  pass (blindspot audit boundary)'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/gates-vacuous.md
- docs/index.md
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/index.md
  reason: 'DOC001 requires docs/audits/gates-vacuous.md be linked from docs/index.md
    (the standard audits-index pattern every other docs/audits/*.md entry follows);
    adding the one-line index entry, not expanding the audit''s own content scope.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: docs-only audit ticket; CLI-dispatch integration test is the bound evidence
    (T-0167 precedent), scope-added for covers_scope (D-02 route 2)
  actor: logan
  at: '2026-07-23'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN the audit doc WHEN complete THEN every gate in gates/__init__.py has
    a recorded verdict for empty-diff/empty-scope/cached-stale satisfaction (can it
    go green without doing its work) and the lang/** tree-sitter ingestion of untrusted
    files has a recorded DoS/traversal verdict; every defect found is filed as its
    own ticket
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
The 2026-07-23 blindspot audit explicitly skipped: (a) a full vacuous-satisfaction sweep of gates/__init__.py (8568 lines -- can any gate be satisfied by an empty diff, empty scope, or stale cache?), and (b) lang/** parser trust boundary (tree-sitter on untrusted repo files). These are the largest unaudited surfaces. Run per the audit-until-empty discipline (docs/audits/, pessimistic auditor told to find 10+, repeat until 0).