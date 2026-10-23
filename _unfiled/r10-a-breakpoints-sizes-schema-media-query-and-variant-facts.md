+++
id = "01M1QDTV322Y6MS3KDRTTCYT3G"
title = "R10-A: breakpoints/sizes schema + media-query and variant facts (CR-22/23 data)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0098"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/spec/naming.py", "src/crunk/spec/__init__.py", "src/crunk/ingest/**", "tests/unit/test_spec.py", "tests/unit/test_ingest.py"]

[[acceptance]]
text = "given the r10 schema, when a spec with sizes and breakpoints loads and a tree with media queries and variant utilities ingests, then the documented facts land (UT-SPEC-10, UT-ING-11)"
bound = false
+++

Per r10 spec.md and ingest.md: ScalesConfig.sizes (empty default, ascending); BreakpointsConfig (mapping + base_required, precedence declared > tailwind-implied v3 defaults > off/empty); catalog rows SIZE001/BP001/BP002/BP003; size_token in naming; Stylesheet.media_queries (LocatedMediaQuery: prelude text, parsed min/max px incl. the -0.02 idiom, line) recorded where _walk_rules recurses; LocatedUtility.variants preserved in order (name unchanged for existing consumers) across tsx className, ts constants, and variant stripping.
