---
id: T-0402
title: 'AUDIT: graph foundation -- complete-snapshot loads + fail-closed parsing (docs/audits/graph.md)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/graph/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestLoadGraph::test_cache_stale_after_new_file_added
designated_repro_test: null
threat: null
component: null
---
See docs/audits/graph.md. HIGH: load_graph only re-hashes files already cached, so a newly-added file returns Ok on an INCOMPLETE snapshot (gates check a graph missing that files obligations); a non-UTF-8 .md throws UnicodeDecodeError and hard-crashes frob check. RIGHT-WAY fix: detect new/removed files as staleness (not just changed cached ones); catch decode errors per-file and surface loudly not crash-or-drop. Then re-audit until empty. MED/LOW G3-G12 in the doc.