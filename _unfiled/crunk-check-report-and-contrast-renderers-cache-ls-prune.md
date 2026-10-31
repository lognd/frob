+++
id = "01M4MD9FEH1F337CTWPZ03B67Y"
title = "crunk check: --report and --contrast renderers, cache ls|prune, Python-corpus violation parity"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-11T02:39:53Z"
updated = "2026-10-31T12:56:12Z"
labels = ["no-story"]
scope = ["crates/crunk-check/**", "crates/crunk/src/**", "crates/gob-cache/src/lib.rs", "crates/crunk/tests/**", "docs/crunk/**", "crates/gob-check/src/lib.rs", "crates/gob-check/src/pipeline.rs"]

[[acceptance]]
text = "crunk check --json carries version 1"
bound = false

[[acceptance]]
text = "crunk check --report markdown and --report json render through the report module"
bound = false

[[acceptance]]
text = "crunk check --contrast lists every role pair in every mode"
bound = false

[[acceptance]]
text = "crunk cache ls and crunk cache prune operate on the shared cache"
bound = false
+++

Split from ~1ZF0G9C, which landed the exit-code and warm-cache criteria over the existing gob-check pipeline. Remaining: --report (Markdown or v2 JSON) and --contrast renderers through gob-diagnostics, versioned --json with {version:1}, crunk cache ls|prune over gob-cache, and the corpus parity of violations against Python output (the harness is ~Q4J906S). Port test_report.py, test_app.py, test_cache.py and e2e 07, 15, 17, INT-06, 07, 09, 12.

no-story: internal engineering task in crunk-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
