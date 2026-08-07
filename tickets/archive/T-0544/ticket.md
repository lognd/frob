---
id: T-0544
title: 'graph: frob:describes anchor discovery only scans docs/, missing README/top-level
  notes (T-0404 finding 8)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0404
tier: ticket
sprint: null
scope:
- src/frob/graph/
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_graph.py
  reason: T-0544's README-doc-discovery fix needs a regression test in tests/test_graph.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_graph.py::TestExclude::test_walk_repo_files_classifies_top_level_readme_as_doc
designated_repro_test: null
threat: null
component: null
---
docs/audits/lang-check-docs.md finding 8. _walk_doc_files (graph/__init__.py) only walks docs/**/*.md; a frob:describes anchor placed in README.md or a top-level design note is never parsed, so its DESCRIBES edge (and the facet it selects for DRIFT001) never exists -- even though DOC001's orphan-doc root set does include README.md. Fix direction: scan the same include/exclude glob set doclink uses, not a hardcoded docs/ dir. Out of T-0404's declared scope (graph/, not lang/check/gates/) -- needs a scope-widened or standalone follow-up ticket.