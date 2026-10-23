+++
id = "01M1QDTV1WHKSQHWQY5KASC9GH"
title = "R6-A: [jsx]/[tailwind]/org.model schema + JSX and tailwind-config ingestion (CR-17, CR-21 schema)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0060"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/spec/__init__.py", "src/crunk/ingest/**", "tests/unit/test_spec.py", "tests/unit/test_ingest.py", "tests/integration/test_int_11_jsx.py", "docs/design/subsystems/ingest.md", "docs/design/subsystems/spec.md", "frob.lock"]

[[acceptance]]
text = "given a TSX fixture with literal style props, classNames with arbitrary values, and a tailwind config mapping, when ingest_tree runs with the r6 sections configured, then jsx sheets carry the documented declarations/utilities and tw_theme is populated (INT-11)"
bound = false
+++

Per r6 spec.md (UT-SPEC-09) and ingest.md (JSX sources + Tailwind config sections, UT-ING-09/10): JsxConfig/TailwindConfig sub-models + org.model field; Bucket.JSX; Stylesheet.utilities + LocatedUtility model; ProjectStyles.tw_theme; ingest/jsx.py (brace-balanced style extraction, React px/unitless semantics with exact-source spans preserving INV-ING-01, className utility tokens with variant stripping, computed/interpolated skipped silently); ingest/tailwind.py heuristic literal theme parse; walk wiring behind the config (off = zero behavior change).
