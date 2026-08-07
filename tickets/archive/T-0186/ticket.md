---
id: T-0186
title: link docs/guides/exhaustive-research.md from docs/index.md
state: done
kind: docs
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/index.md
- tickets.md
- tests/unit/test_research_assets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_research_assets.py::test_docs_index_links_the_guide
designated_repro_test: null
threat: null
component: null
---
T-0185 shipped docs/guides/exhaustive-research.md but docs/index.md is outside T-0185's declared scope, so DOC001 (doclink) cannot be satisfied without touching it. Add one bullet under 'Getting started' pointing at the new guide, matching the existing entries for install/quickstart/agentic-workflow/editors.