+++
id = "01M7EXV9RKV8M86RDJ51YXAD9A"
title = "Per-rule effort_minutes metadata and frob stats --debt"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:20:53Z"
updated = "2026-11-15T06:20:53Z"
idempotency_key = "static-research-k12"
labels = ["no-story"]

[[acceptance]]
text = "Rule metadata accepts effort_minutes and rules without one use a documented default"
bound = false

[[acceptance]]
text = "frob stats --debt reports total, per-kLOC and delta vs base on a fixture repo"
bound = false

[[acceptance]]
text = "Output labels debt as an estimate"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 11, section 1.6. Rationale: Sonar's remediation effort per rule yields debt, debt ratio and trend; frob stats has cost per point and PM objectives but no per-finding effort (grep for effort in frob-obligations found nothing). Sonar details are [F], the SQALE criticism is [M]. Remedy: optional effort_minutes in rule metadata with a documented default, and frob stats --debt reporting total debt, debt per kLOC and trend vs base. Rule-level constants are a heuristic: label output as an estimate. Crates/files: rule metadata in crates/frob-obligations and gob-rules, the stats verb in crates/frob.
