+++
id = "01M43ATCF5GGK59S96K1ZF0G9C"
title = "crunk check end to end: pipeline, reports, cache, exit codes"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:36Z"
updated = "2026-10-11T03:45:24Z"
idempotency_key = "crunk-plan-chk"
labels = ["area:crunk"]
scope = ["crates/crunk-check/**", "crates/crunk/src/check.rs", "crates/crunk/tests/check*.rs", "crates/crunk-check/tests/**"]

[[links]]
kind = "blocked-by"
target = "01M43ARY91XZ35DN9SCHRHS033"

[[links]]
kind = "blocked-by"
target = "01M43ARYFVG86PAGGM78JGRZY3"

[[links]]
kind = "blocked-by"
target = "01M43ATASM383KB9130JY79XVV"

[[links]]
kind = "blocked-by"
target = "01M43ATB4X0B56W8T0G8MQFYVM"

[[acceptance]]
text = "Given a warm cache, when check runs twice, then the second run reuses cached ingest and reports the same findings"
bound = true

[[acceptance]]
text = "Given an error-severity violation, when crunk check --json runs, then the exit is 1; given a clean project, then 0"
bound = true

[[acceptance]]
text = "Given an unreadable crunk.toml, when check runs, then it is refused with E-CONFIG (exit 3, the shared refusal code), and a bad flag exits 2"
bound = true
+++

Wire ingest, rules and fixes into the gob-check pipeline: PATH arguments, --config/--root, --json (versioned, `{version:1}` kept for the parity run plus gob.sibling/1), --contrast and --report (Markdown or v2 JSON) renderers via gob-diagnostics, content-addressed cache in gob-cache (replaces cache/store.py; `crunk cache ls|prune` over it), exit 0/1/2. report/ (1009 LOC) terminal, json, markdown, preview. Port tests/unit/test_report.py, test_app.py, test_cache.py, e2e 07, 15, 17, INT-06, 07, 09, 12.
