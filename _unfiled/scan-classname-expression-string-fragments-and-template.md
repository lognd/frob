+++
id = "01M1T07J3P7GR84V0N5RD3WGMT"
title = "Scan className-expression string fragments and template static segments (A-060)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:40Z"
aliases = ["crunk:T-0118"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/ingest/jsx.py", "tests/unit/test_ingest.py", "tests/system/test_e2e_45_selfmap.py", "tests/integration/test_int_11_jsx.py"]

[[acceptance]]
text = "given a TSX file with className={backtick a z-footer dollar-brace cond end-brace backtick}, when ingested, then z-footer is a LocatedUtility and z- half-tokens never appear"
bound = false

[[acceptance]]
text = "given a .ts template constant with class-list static segments, when scanned, then per-segment tokens are extracted under the existing heuristic"
bound = false
+++

unused_tokens reports a live layer token dead when its only consumer is a template-literal className with interpolation. Implement the r12 rule from ingest.md and 02-specification.md: inside a className expression, scan every string literal and every template-literal static segment as a class list, dropping tokens that touch an interpolation boundary; apply the same static-segment scan to .ts template constants. Covers clsx/cn calls and ternaries by construction.
