+++
id = "01M7EXV8HQ1ENKAD4NP5ZTFEZX"
title = "Coverage ingest: Cobertura XML and JaCoCo XML alongside the existing lcov normaliser"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:52Z"
updated = "2026-11-15T06:20:52Z"
idempotency_key = "static-research-k9"
labels = ["no-story"]

[[acceptance]]
text = "A Cobertura XML fixture and a JaCoCo XML fixture normalise to the same model as an equivalent lcov fixture"
bound = false

[[acceptance]]
text = "[coverage] accepts a report path of either format with format auto-detected"
bound = false

[[acceptance]]
text = "Docs list the supported coverage formats"
bound = false
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 9, section 3. Rationale: frob has a shared lcov normaliser and [coverage] thresholds (frob-evidence crate coverage module, CoverageConfig; ticket 9Q1N24Q done). Report claims Cobertura/JaCoCo ingest is missing: verify first by grepping crates/frob-evidence/src/coverage; a grep for cobertura|jacoco over crates and docs found no hits at HEAD. Remedy: add Cobertura and JaCoCo readers that normalise to the same line/branch model, selected by report file shape or config. Crates/files: crates/frob-evidence/src/coverage/.
