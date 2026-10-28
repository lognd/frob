+++
id = "01M4MD9FEH1F337CTWPZ03B67Y"
title = "crunk check: --report and --contrast renderers, cache ls|prune, Python-corpus violation parity"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-11T02:39:53Z"
updated = "2026-10-28T12:57:45Z"
labels = ["no-story"]
scope = ["crates/crunk-check/**", "crates/crunk/src/**"]
+++

Split from ~1ZF0G9C, which landed the exit-code and warm-cache criteria over the existing gob-check pipeline. Remaining: --report (Markdown or v2 JSON) and --contrast renderers through gob-diagnostics, versioned --json with {version:1}, crunk cache ls|prune over gob-cache, and the corpus parity of violations against Python output (the harness is ~Q4J906S). Port test_report.py, test_app.py, test_cache.py and e2e 07, 15, 17, INT-06, 07, 09, 12.

no-story: internal engineering task in crunk-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
