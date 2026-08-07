## Done report

Changed: docs/index.md (one bullet under Getting started, matching the
install/quickstart/agentic-workflow/editors entry style).

Evidence: tests/unit/test_research_assets.py::test_docs_index_links_the_guide
(drift-lock: the link's absence fails the suite). Gate proof: DOC001 for
docs/guides/exhaustive-research.md present before this change, absent
after; repo violation count dropped by exactly one.

Filed: none. Gates: no other rule references docs/index.md in this diff.
